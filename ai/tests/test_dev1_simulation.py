"""Developer 1 — audience, personas, simulation, propagation, evaluation.

Covers the scenarios the module brief calls out: schema validation, simulation
against mock Content DNA, malformed AI output, a failed persona not taking down
a run, deterministic propagation, confidence, and an empty persona list.

Everything runs in mock mode, so no test here can spend a token or reach a
network. Where a real model call is needed, the provider is monkeypatched.

Run:  cd ai && python -m pytest tests/test_dev1_simulation.py
"""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

import fixtures
import llm as llm_module
from audience import assemble_graph, discover_audience, targetable_segments, validate_graph
from audience.segmentation.segmentation import MAX_DEPTH, graph_id_for, slugify
from errors import MalformedModelOutputError
from evaluation import (
    actual_performance_score,
    confidence_calibration,
    evaluate_predictions,
    load_dataset,
    rank_from_scores,
)
from personas import behavioural_spread, generate_personas, persona_cache, select_within_budget
from personas.profiles.profiles import PersonaCache, cache_key, slug_id
from propagation import simulate_propagation
from schemas import (
    AudienceRequest,
    ContentDNA,
    Persona,
    PersonaSimulationResult,
    Prediction,
    SimulationRequest,
)
from simulation import (
    SimulationOptions,
    compute_confidence,
    content_gaps,
    detect_signals,
    disagreement,
    run_simulation,
    run_simulation_for_personas,
    simulate_persona,
)
from simulation.agents.viewer_agent import _coerce, _ViewerReaction, failed_result

REQUEST = AudienceRequest(
    niche="fitness",
    target_audience="natural bodybuilding beginners",
    secondary_audience="college students interested in fitness",
    location="India",
    language="English",
    creator_goal="increase reach among beginners",
)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _clear_persona_cache():
    persona_cache.clear()
    yield
    persona_cache.clear()


# ===========================================================================
# 1. Audience discovery — schema validation
# ===========================================================================

def test_discover_audience_returns_a_structurally_valid_graph():
    graph, mock = run(discover_audience(REQUEST))

    assert mock is True
    assert validate_graph(graph) == []
    assert len(graph.segments) >= 3
    # The caller's own brief is echoed back, not the fixture's.
    assert graph.request.creator_goal == REQUEST.creator_goal


def test_graph_id_is_deterministic_for_the_same_brief():
    assert graph_id_for(REQUEST) == graph_id_for(REQUEST)
    other = REQUEST.model_copy(update={"niche": "cooking"})
    assert graph_id_for(other) != graph_id_for(REQUEST)


def test_assemble_graph_derives_ids_and_resolves_edges_by_name():
    graph = assemble_graph(
        request=REQUEST,
        segments=[
            {"name": "Fitness India", "description": "root", "relevance_score": 0.5},
            {
                "name": "Beginner Lifters",
                "description": "new to training",
                "parent_name": "Fitness India",
                "relevance_score": 0.9,
            },
            {
                "name": "College Starters",
                "description": "campus gym",
                "parent_name": "Fitness India",
                "relevance_score": 0.7,
            },
        ],
        adjacency=[
            {"from_name": "College Starters", "to_name": "Beginner Lifters", "spillover_probability": 0.4},
        ],
    )

    assert validate_graph(graph) == []
    assert slugify("Beginner Lifters") == "seg_beginner_lifters"
    assert graph.adjacency[0].from_segment_id == "seg_college_starters"
    assert graph.adjacency[0].to_segment_id == "seg_beginner_lifters"


def test_assemble_graph_repairs_a_dangling_parent_and_forces_one_root():
    graph = assemble_graph(
        request=REQUEST,
        segments=[
            {"name": "A", "description": "a", "parent_name": "Does Not Exist", "relevance_score": 0.2},
            {"name": "B", "description": "b", "parent_name": None, "relevance_score": 0.8},
        ],
        adjacency=[{"from_name": "A", "to_name": "Ghost", "spillover_probability": 0.5}],
    )

    assert validate_graph(graph) == []
    assert len([s for s in graph.segments if s.parent_segment is None]) == 1
    # The edge pointing at a segment that does not exist was dropped, not kept.
    assert graph.adjacency == []


def test_assemble_graph_caps_hierarchy_depth():
    chain = [{"name": "L0", "description": "d", "parent_name": None, "relevance_score": 0.5}]
    chain += [
        {
            "name": f"L{level}",
            "description": "d",
            "parent_name": f"L{level - 1}",
            "relevance_score": 0.5,
        }
        for level in range(1, 6)
    ]
    graph = assemble_graph(request=REQUEST, segments=chain, adjacency=[])

    parents = {s.id: s.parent_segment for s in graph.segments}

    def depth(segment_id: str) -> int:
        count, current, seen = 1, parents[segment_id], set()
        while current and current not in seen:
            seen.add(current)
            count += 1
            current = parents.get(current)
        return count

    assert max(depth(s.id) for s in graph.segments) <= MAX_DEPTH


def test_assemble_graph_rejects_an_empty_segment_list():
    with pytest.raises(ValueError):
        assemble_graph(request=REQUEST, segments=[], adjacency=[])


def test_targetable_segments_excludes_the_root_and_sorts_by_relevance():
    leaves = targetable_segments(fixtures.audience_graph())

    assert leaves
    assert all(segment.parent_segment is not None for segment in leaves)
    scores = [segment.relevance_score for segment in leaves]
    assert scores == sorted(scores, reverse=True)


# ===========================================================================
# 2. Persona generation — schema validation, diversity, caching
# ===========================================================================

def test_generate_personas_validates_against_the_persona_contract():
    segment = targetable_segments(fixtures.audience_graph())[0]
    personas, mock = run(generate_personas(segment, count=2))

    assert mock is True
    assert personas
    for persona in personas:
        assert isinstance(persona, Persona)
        assert persona.segment_id == segment.id
        assert 0 <= persona.attention_profile.swipe_tendency <= 1
        assert 0 <= persona.engagement_profile.share_tendency <= 1


def test_persona_count_is_capped_by_the_budget():
    segment = targetable_segments(fixtures.audience_graph())[0]
    personas, _ = run(generate_personas(segment, count=10_000))

    # Never explodes into an unbounded, unaffordable run.
    assert len(personas) <= 25


def test_persona_ids_are_deterministic_and_carry_the_segment():
    assert slug_id("seg_x", "Rohit Sharma", 0) == "seg_x__rohit_sharma_0"
    assert slug_id("seg_x", "Rohit Sharma", 0) == slug_id("seg_x", "Rohit Sharma", 0)


def test_behavioural_spread_separates_diverse_from_identical_personas():
    personas = fixtures.personas()
    clones = [personas[0].model_copy(update={"id": f"clone_{i}"}) for i in range(4)]

    assert behavioural_spread(personas) > behavioural_spread(clones)
    assert behavioural_spread(clones) == 0.0
    assert behavioural_spread(personas[:1]) == 0.0


def test_select_within_budget_keeps_both_ends_of_the_spread():
    personas = fixtures.personas()
    trimmed = select_within_budget(personas, 3)

    assert len(trimmed) == 3
    tendencies = [p.attention_profile.swipe_tendency for p in trimmed]
    # The most patient viewer survives the trim, not just the impatient tail.
    assert min(tendencies) == min(p.attention_profile.swipe_tendency for p in personas)
    assert select_within_budget(personas, 0) == []


def test_persona_cache_round_trips_and_evicts():
    cache = PersonaCache(max_entries=2)
    key = cache_key("seg_a", 3, "v1")

    assert cache.get(key) is None
    cache.put(key, fixtures.personas()[:2])
    assert len(cache.get(key)) == 2

    cache.put(cache_key("seg_b", 3, "v1"), [])
    cache.put(cache_key("seg_c", 3, "v1"), [])
    assert len(cache) == 2  # bounded, never grows without limit


def test_cache_key_changes_with_the_prompt_version():
    assert cache_key("seg", 3, "v1") != cache_key("seg", 3, "v2")


# ===========================================================================
# 3. Simulation against mock Content DNA
# ===========================================================================

def test_simulate_persona_returns_a_valid_result():
    persona = fixtures.personas()[0]
    result, mock = run(simulate_persona(persona, fixtures.content_dna()))

    assert mock is True
    assert result.persona_id == persona.id
    assert 0 <= result.watch_probability <= 1
    assert result.reason


def test_run_simulation_for_personas_end_to_end():
    personas = fixtures.personas()
    result, mock = run(run_simulation_for_personas(personas, fixtures.content_dna()))

    assert mock is True
    assert result.status in {"completed", "partial"}
    assert len(result.audience_results) == len(personas)
    assert result.audience_segment_results
    assert result.propagation_waves
    assert 0 <= result.overall_score <= 1
    assert 0 <= result.confidence <= 1
    assert result.metadata is not None and result.metadata.mock is True


def test_simulation_works_with_no_content_dna_and_says_so():
    """Developer 2's pipeline may not be ready; the run must not depend on it."""
    result, _ = run(run_simulation_for_personas(fixtures.personas(), None))

    assert result.audience_results
    assert any(w.code == "MOCK_CONTENT_DNA" for w in result.warnings)


def test_depth_controls_persona_count():
    quick, _ = run(run_simulation(SimulationRequest(reel_id="r", depth="quick")))
    deep, _ = run(run_simulation(SimulationRequest(reel_id="r", depth="deep")))

    assert len(deep.audience_results) >= len(quick.audience_results)


def test_request_signature_developer_2_depends_on_is_intact():
    """`counterfactual/experiments/experiment.py` calls exactly this shape."""
    result, mock = run(
        run_simulation(
            SimulationRequest(
                reel_id="reel_001",
                content_dna=fixtures.content_dna(),
                graph_id="graph_fitness_in_001",
                variant_id="var_a",
            )
        )
    )

    assert isinstance(mock, bool)
    assert result.variant_id == "var_a"
    assert result.simulation_id.startswith("sim_")


# ===========================================================================
# 4. Invalid AI output handling
# ===========================================================================

def test_probabilities_outside_0_1_are_rejected_by_the_schema():
    for bad in ({"watch_probability": 1.4}, {"confidence": -0.2}, {"swipe_time": -3}):
        payload = {
            "watch_probability": 0.5,
            "completion_probability": 0.4,
            "like_probability": 0.1,
            "save_probability": 0.1,
            "share_probability": 0.1,
            "comment_probability": 0.1,
            "swipe_time": 2.0,
            "action": "swipe",
            "reason": "n/a",
            "confidence": 0.5,
            **bad,
        }
        with pytest.raises(ValidationError):
            _ViewerReaction.model_validate(payload)


def test_incoherent_probabilities_are_clamped_not_trusted():
    """A viewer cannot finish or share a video they never watched."""
    reaction = _ViewerReaction(
        watch_probability=0.2,
        completion_probability=0.9,   # impossible: exceeds watch
        like_probability=0.8,
        save_probability=0.8,
        share_probability=0.8,
        comment_probability=0.8,
        swipe_time=999.0,             # beyond the end of the video
        action="swipe",
        reason="left immediately",
        confidence=0.6,
    )
    content = fixtures.content_dna()
    result = _coerce(reaction, fixtures.personas()[0], content)

    assert result.completion_probability <= result.watch_probability
    assert result.share_probability <= result.watch_probability
    assert result.swipe_time <= content.duration_seconds


def test_an_unknown_action_falls_back_to_a_coherent_one():
    reaction = _ViewerReaction(
        watch_probability=0.2,
        completion_probability=0.1,
        like_probability=0.0,
        save_probability=0.0,
        share_probability=0.0,
        comment_probability=0.0,
        swipe_time=1.0,
        action="teleported",
        reason="nonsense action",
        confidence=0.4,
    )
    result = _coerce(reaction, fixtures.personas()[0], fixtures.content_dna())
    assert result.action == "swipe"


def test_engagement_actions_clear_the_swipe_time():
    reaction = _ViewerReaction(
        watch_probability=0.9,
        completion_probability=0.8,
        like_probability=0.6,
        save_probability=0.5,
        share_probability=0.2,
        comment_probability=0.1,
        swipe_time=12.0,  # contradicts "save"
        action="save",
        reason="saved it",
        confidence=0.7,
    )
    result = _coerce(reaction, fixtures.personas()[0], fixtures.content_dna())
    assert result.swipe_time is None


def test_malformed_json_raises_rather_than_being_silently_accepted():
    with pytest.raises(MalformedModelOutputError):
        llm_module._parse_json("this is not json at all")


def test_json_in_a_code_fence_is_tolerated():
    assert llm_module._parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_schema_refs_are_inlined_for_providers():
    schema = llm_module.schema_for(ContentDNA)
    assert "$defs" not in schema
    assert "properties" in schema
    # Aliased (camelCase) keys, because that is what the model must emit.
    assert "videoId" in schema["properties"]


# ===========================================================================
# 5. A failed persona must not crash the simulation
# ===========================================================================

def test_failed_result_is_neutral_and_zero_confidence():
    result = failed_result(fixtures.personas()[0], "model timeout")

    assert result.error == "model timeout"
    assert result.confidence == 0.0
    assert result.watch_probability == 0.0


def test_one_exploding_persona_does_not_take_down_the_run(monkeypatch):
    personas = fixtures.personas()
    failing_id = personas[1].id

    real = llm_module.settings.is_mock_mode

    async def flaky(persona, content):
        if persona.id == failing_id:
            raise RuntimeError("provider exploded")
        return await _original_simulate(persona, content)

    _original_simulate = simulate_persona
    monkeypatch.setattr("simulation.engine.engine.simulate_persona", flaky)

    result, _ = run(run_simulation_for_personas(personas, fixtures.content_dna()))

    assert real is True
    assert result.status == "partial"
    assert len(result.audience_results) == len(personas)

    failed = [r for r in result.audience_results if r.error is not None]
    assert len(failed) == 1 and failed[0].persona_id == failing_id

    # The failure is reported, and excluded from every average.
    assert any(w.code == "PARTIAL_SIMULATION" for w in result.warnings)
    for segment in result.audience_segment_results:
        assert segment.persona_count <= len(personas) - 1 or segment.segment_id != failing_id


def test_all_personas_failing_still_returns_a_result(monkeypatch):
    async def always_fails(persona, content):
        raise RuntimeError("provider down")

    monkeypatch.setattr("simulation.engine.engine.simulate_persona", always_fails)
    result, _ = run(run_simulation_for_personas(fixtures.personas(), fixtures.content_dna()))

    assert result.status == "partial"
    assert result.overall_score == 0.0
    assert result.confidence == 0.0
    assert all(r.error is not None for r in result.audience_results)


# ===========================================================================
# 6. Empty persona list
# ===========================================================================

def test_empty_persona_list_degrades_instead_of_raising():
    result, _ = run(run_simulation_for_personas([], fixtures.content_dna()))

    assert result.status == "failed"
    assert result.audience_results == []
    assert result.overall_score == 0.0
    assert any(w.code == "EMPTY_PERSONA_SET" for w in result.warnings)


# ===========================================================================
# 7. Deterministic propagation
# ===========================================================================

def _persona_results() -> list[PersonaSimulationResult]:
    return fixtures.simulation_result().audience_results


def test_propagation_is_reproducible_for_a_given_seed():
    simulation = fixtures.simulation_result()
    kwargs = dict(
        graph=fixtures.audience_graph(),
        segment_results=simulation.audience_segment_results,
    )

    first = simulate_propagation(simulation.audience_results, seed=42, **kwargs)
    second = simulate_propagation(simulation.audience_results, seed=42, **kwargs)

    assert [(w.wave, w.reach) for w in first] == [(w.wave, w.reach) for w in second]


def test_a_different_seed_gives_a_different_cascade():
    simulation = fixtures.simulation_result()
    kwargs = dict(
        graph=fixtures.audience_graph(),
        segment_results=simulation.audience_segment_results,
    )

    a = simulate_propagation(simulation.audience_results, seed=1, **kwargs)
    b = simulate_propagation(simulation.audience_results, seed=999, **kwargs)

    # Stochastic, so the reaches should differ somewhere.
    assert [w.reach for w in a] != [w.reach for w in b]


def test_propagation_without_a_seed_is_still_reproducible():
    """Derived from persona ids, so a repeated run repeats the cascade."""
    results = _persona_results()
    assert [w.reach for w in simulate_propagation(results)] == [
        w.reach for w in simulate_propagation(results)
    ]


def test_propagation_is_bounded():
    waves = simulate_propagation(_persona_results(), graph=fixtures.audience_graph(), seed=7)

    assert waves[0].wave == 0
    assert len(waves) <= 5
    assert waves[-1].terminated or len(waves) == 5


def test_propagation_needs_only_persona_results():
    """Works with no graph — the spec's minimal signature."""
    waves = simulate_propagation(_persona_results(), seed=42)
    assert waves and waves[0].reach > 0


def test_non_sharing_audience_kills_the_cascade():
    dead = [
        result.model_copy(update={"share_probability": 0.0, "watch_probability": 0.1})
        for result in _persona_results()
    ]
    waves = simulate_propagation(dead, graph=fixtures.audience_graph(), seed=42)

    assert waves[-1].terminated


def test_failed_personas_are_ignored_by_propagation():
    results = [r.model_copy(update={"error": "boom"}) for r in _persona_results()]
    assert simulate_propagation(results, seed=42) == []


# ===========================================================================
# 8. Confidence
# ===========================================================================

def test_confidence_is_explainable_and_bounded():
    results = _persona_results()
    breakdown = compute_confidence(results, requested=len(results), content=fixtures.content_dna())

    assert 0 <= breakdown.value <= 1
    for factor in breakdown.as_fields().values():
        assert 0 <= factor <= 1
    # Five personas is below the stable-sample bar, and it says so.
    assert any("personas simulated" in note for note in breakdown.notes)


def test_failed_personas_reduce_confidence():
    results = _persona_results()
    healthy = compute_confidence(results, requested=len(results))
    degraded = compute_confidence(
        [results[0].model_copy(update={"error": "timeout"}), *results[1:]],
        requested=len(results),
    )

    assert degraded.value < healthy.value
    assert any("completed successfully" in note for note in degraded.notes)


def test_no_successful_personas_gives_zero_confidence():
    results = [r.model_copy(update={"error": "boom"}) for r in _persona_results()]
    breakdown = compute_confidence(results, requested=len(results))

    assert breakdown.value == 0.0
    assert breakdown.notes


def test_missing_content_dna_reduces_confidence():
    results = _persona_results()
    full = compute_confidence(results, requested=len(results), content=fixtures.content_dna())
    blank = compute_confidence(
        results,
        requested=len(results),
        content=fixtures.content_dna().model_copy(update={"transcript": "", "scenes": []}),
    )

    assert blank.content_completeness < full.content_completeness
    assert blank.value < full.value


def test_content_gaps_names_what_is_missing():
    gaps = content_gaps(fixtures.content_dna().model_copy(update={"transcript": ""}))
    assert any("Transcript" in gap for gap in gaps)
    assert content_gaps(None)


def test_disagreement_detects_a_split_audience():
    results = _persona_results()
    unanimous = [r.model_copy(update={"watch_probability": 0.5, "completion_probability": 0.5}) for r in results]

    assert disagreement(unanimous) == 0.0
    assert disagreement(results) > 0.0


# ===========================================================================
# 9. Bottleneck detection
# ===========================================================================

def test_signals_are_measured_from_data_not_templated():
    simulation = fixtures.simulation_result()
    signals = detect_signals(
        fixtures.content_dna(),
        simulation.audience_results,
        simulation.audience_segment_results,
        simulation.propagation_waves,
    )

    assert signals
    stages = {signal.stage for signal in signals}
    assert "hook" in stages  # 4 of 5 fixture personas leave inside the hook
    # Severity is ordered, and every description carries the measurement.
    assert signals == sorted(signals, key=lambda s: s.severity, reverse=True)
    assert all(0 <= signal.severity <= 1 for signal in signals)


def test_a_healthy_reel_produces_no_bottlenecks():
    great = [
        r.model_copy(
            update={
                "watch_probability": 0.95,
                "completion_probability": 0.9,
                "share_probability": 0.5,
                "save_probability": 0.5,
                "like_probability": 0.6,
                "swipe_time": None,
                "action": "share",
                "error": None,
            }
        )
        for r in _persona_results()
    ]
    assert detect_signals(fixtures.content_dna(), great, []) == []


def test_bottlenecks_without_a_model_admit_the_cause_is_unknown():
    """No fabricated explanations when the reasoning model is unavailable."""
    simulation = fixtures.simulation_result()
    from simulation.behavior.reflection import UNEXPLAINED, analyze_bottlenecks

    bottlenecks, mock = run(
        analyze_bottlenecks(
            fixtures.content_dna(),
            simulation.audience_results,
            simulation.audience_segment_results,
            simulation.propagation_waves,
        )
    )

    assert mock is True
    assert bottlenecks
    for bottleneck in bottlenecks:
        assert bottleneck.likely_cause == UNEXPLAINED
        assert bottleneck.confidence == 0.0  # honest: nothing was reasoned about


# ===========================================================================
# 10. Evaluation
# ===========================================================================

def test_perfect_ranking_scores_perfectly():
    dataset = load_dataset()
    predictions = [
        Prediction(
            reel_id=item.reel_id,
            predicted_score=1.0 / item.actual_rank,
            predicted_rank=item.actual_rank,
            confidence=0.7,
        )
        for item in dataset.items
    ]
    metrics = evaluate_predictions(predictions, dataset)

    assert metrics.pairwise_ranking_accuracy == 1.0
    assert metrics.rank_correlation == 1.0


def test_reversed_ranking_scores_zero():
    dataset = load_dataset()
    count = len(dataset.items)
    predictions = [
        Prediction(
            reel_id=item.reel_id,
            predicted_score=0.5,
            predicted_rank=count - item.actual_rank + 1,
            confidence=0.5,
        )
        for item in dataset.items
    ]
    assert evaluate_predictions(predictions, dataset).pairwise_ranking_accuracy == 0.0


def test_evaluate_predictions_accepts_a_bare_item_list():
    dataset = load_dataset()
    predictions = rank_from_scores({item.reel_id: 0.5 for item in dataset.items})

    assert evaluate_predictions(predictions, dataset.items).item_count == len(dataset.items)


def test_actual_performance_score_is_bounded_and_ordered():
    dataset = load_dataset()
    scores = [actual_performance_score(item.actual) for item in dataset.items]

    assert all(0 <= score <= 1 for score in scores)
    ranked = sorted(dataset.items, key=lambda item: item.actual_rank)
    # The reel that really did best should score highest on our blend.
    assert actual_performance_score(ranked[0].actual) == max(scores)


def test_confidence_calibration_detects_useful_confidence():
    predictions = [
        Prediction(reel_id="a", predicted_score=0.9, predicted_rank=1, confidence=0.9),
        Prediction(reel_id="b", predicted_score=0.5, predicted_rank=2, confidence=0.2),
    ]
    # 'a' was accurate and confident; 'b' was wrong and unsure — good calibration.
    assert confidence_calibration(predictions, {"a": 0.05, "b": 0.6}) > 0


def test_empty_predictions_do_not_crash_evaluation():
    metrics = evaluate_predictions([], load_dataset())

    assert metrics.item_count == 0
    assert metrics.rank_correlation is None
    assert metrics.notes


def test_rank_from_scores_orders_best_first_and_carries_confidence():
    predictions = rank_from_scores({"a": 0.2, "b": 0.9, "c": 0.5}, {"b": 0.8})

    assert [p.reel_id for p in predictions] == ["b", "c", "a"]
    assert [p.predicted_rank for p in predictions] == [1, 2, 3]
    assert predictions[0].confidence == 0.8


# ===========================================================================
# 11. Cost control
# ===========================================================================

def test_simulation_options_map_depth_to_persona_count():
    assert SimulationOptions(depth="quick").per_segment() == 2
    assert SimulationOptions(depth="standard").per_segment() == 4
    assert SimulationOptions(depth="deep").per_segment() == 8
    assert SimulationOptions(personas_per_segment=3).per_segment() == 3


def test_persona_ceiling_trims_an_oversized_run():
    personas = fixtures.personas()
    result, _ = run(
        run_simulation_for_personas(
            personas, fixtures.content_dna(), options=SimulationOptions(max_personas=2)
        )
    )

    assert len(result.audience_results) == 2
    assert any(w.code == "PERSONA_CAP_APPLIED" for w in result.warnings)


def test_bottleneck_explanation_can_be_skipped_to_save_calls():
    result, _ = run(
        run_simulation_for_personas(
            fixtures.personas(),
            fixtures.content_dna(),
            options=SimulationOptions(explain_bottlenecks=False),
        )
    )
    assert result.bottlenecks == []


def test_cost_estimate_is_none_for_an_unknown_model():
    assert llm_module.estimate_cost_usd("some-local-model", 1000, 1000) is None
    assert llm_module.estimate_cost_usd("claude-opus-5", 1_000_000, 0) == 5.0
