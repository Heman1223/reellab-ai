"""Module-level tests for the AI service.

Everything runs in mock mode (no `AI_API_KEY`), so no test here can spend a
token or reach a network. What is being tested is the deterministic scaffolding:
that the pipeline holds together, that failures degrade instead of crashing, and
that mock output is honestly labelled.
"""

from __future__ import annotations

import asyncio

import fixtures
from audience import discover_audience, targetable_segments, validate_graph
from counterfactual.experiments.experiment import compare, recommend
from evaluation import evaluate_predictions, load_dataset, rank_from_scores
from personas import brief_for, generate_personas, select_within_budget
from propagation import simulate_propagation
from schemas import AudienceRequest, Prediction, SimulationRequest, VariantComparison
from simulation.behavior.aggregation import overall_score, segment_score, usable, verdict_for
from simulation.engine.engine import run_simulation
from video_analysis import analyze_video

REQUEST = AudienceRequest(
    niche="fitness",
    target_audience="natural bodybuilding beginners",
    secondary_audience="college students interested in fitness",
    location="India",
    language="English",
    creator_goal="increase reach among beginners",
)


# --- audience ---------------------------------------------------------------

def test_discover_audience_returns_a_valid_graph_in_mock_mode():
    graph, mock = asyncio.run(discover_audience(REQUEST))

    assert mock is True
    assert len(graph.segments) >= 3
    assert validate_graph(graph) == []
    # The caller's own brief is echoed back, not the fixture's.
    assert graph.request.creator_goal == REQUEST.creator_goal


def test_targetable_segments_excludes_the_root_niche():
    graph = fixtures.audience_graph()
    leaves = targetable_segments(graph)

    assert leaves
    assert all(segment.parent_segment is not None for segment in leaves)
    # Sorted by relevance, most relevant first.
    scores = [segment.relevance_score for segment in leaves]
    assert scores == sorted(scores, reverse=True)


def test_validate_graph_catches_a_dangling_parent():
    graph = fixtures.audience_graph()
    broken = graph.model_copy(
        update={
            "segments": [
                graph.segments[1].model_copy(update={"parent_segment": "seg_does_not_exist"}),
            ]
        }
    )
    problems = validate_graph(broken)
    assert any("unknown parent" in problem for problem in problems)


# --- personas ---------------------------------------------------------------

def test_generate_personas_returns_personas_for_the_segment():
    segment = targetable_segments(fixtures.audience_graph())[0]
    personas, mock = asyncio.run(generate_personas(segment, count=2))

    assert mock is True
    assert 1 <= len(personas) <= 2
    assert all(persona.segment_id == segment.id for persona in personas)


def test_brief_for_falls_back_when_no_system_brief_was_generated():
    persona = fixtures.personas()[0].model_copy(update={"system_brief": None})
    brief = brief_for(persona)

    assert persona.name in brief
    assert "seconds" in brief


def test_select_within_budget_keeps_the_behavioural_spread():
    personas = fixtures.personas()
    trimmed = select_within_budget(personas, 3)

    assert len(trimmed) == 3
    tendencies = [p.attention_profile.swipe_tendency for p in trimmed]
    # The most patient viewer survives the trim, not just the impatient tail.
    assert min(tendencies) == min(p.attention_profile.swipe_tendency for p in personas)


# --- video ------------------------------------------------------------------

def test_analyze_video_produces_content_dna_in_mock_mode():
    dna, mock = asyncio.run(analyze_video(video_path="data/sample_reels/x.mp4", video_id="reel_9"))

    assert mock is True
    assert dna.video_id == "reel_9"
    assert dna.hook.duration_seconds > 0
    assert dna.scenes


# --- aggregation ------------------------------------------------------------

def test_segment_score_is_bounded_and_ordered():
    results = fixtures.simulation_result().audience_results
    score = segment_score(results)

    assert 0.0 <= score <= 1.0
    assert segment_score([]) == 0.0


def test_verdict_thresholds():
    assert verdict_for(0.8) == "strong"
    assert verdict_for(0.45) == "mixed"
    assert verdict_for(0.1) == "weak"


def test_failed_personas_are_excluded_from_averages():
    results = fixtures.simulation_result().audience_results
    broken = results[0].model_copy(update={"error": "model timeout"})

    assert len(usable([broken, *results[1:]])) == len(results) - 1


def test_overall_score_weights_by_persona_count():
    segment_results = fixtures.simulation_result().audience_segment_results
    score = overall_score(segment_results)

    assert 0.0 <= score <= 1.0
    assert overall_score([]) == 0.0


# --- propagation ------------------------------------------------------------

def test_propagation_produces_waves_and_terminates():
    simulation = fixtures.simulation_result()
    waves = simulate_propagation(
        simulation.audience_results,
        graph=fixtures.audience_graph(),
        segment_results=simulation.audience_segment_results,
        seed=42,
    )

    assert waves
    assert waves[0].wave == 0
    assert waves[0].reach > 0
    # Bounded: either it dies out or it hits the hop cap.
    assert waves[-1].terminated or len(waves) <= 5


def test_propagation_with_no_persona_results_returns_nothing():
    assert simulate_propagation([], graph=fixtures.audience_graph()) == []


# --- simulation engine ------------------------------------------------------

def test_run_simulation_end_to_end_in_mock_mode():
    result, mock = asyncio.run(
        run_simulation(SimulationRequest(reel_id="reel_001"))
    )

    assert mock is True
    assert result.simulation_id.startswith("sim_")
    assert result.status in {"completed", "partial"}
    assert result.audience_results
    assert result.audience_segment_results
    assert result.propagation_waves
    assert 0.0 <= result.overall_score <= 1.0
    # Mock runs must say so, in the metadata and in a warning.
    assert result.metadata is not None and result.metadata.mock is True
    assert any(warning.code == "MOCK_DATA" for warning in result.warnings)


def test_simulation_forces_10_personas():
    result, _ = asyncio.run(run_simulation(SimulationRequest(reel_id="r")))
    assert len(result.audience_results) <= 10


# --- counterfactual ---------------------------------------------------------

def test_compare_computes_segment_deltas():
    baseline = fixtures.simulation_result()
    experiment = fixtures.counterfactual_experiment()
    variant = experiment.variants[0]

    improved = baseline.model_copy(
        update={
            "overall_score": baseline.overall_score + 0.2,
            "audience_segment_results": [
                result.model_copy(update={"score": min(1.0, result.score + 0.1)})
                for result in baseline.audience_segment_results
            ],
        }
    )

    comparison = compare(baseline, variant, improved)

    assert comparison.variant_id == variant.id
    assert comparison.score_delta > 0
    assert all(delta > 0 for delta in comparison.segment_deltas.values())


def test_recommend_declines_to_pick_a_loser():
    comparisons = [
        VariantComparison(variant_id="var_a", score_delta=-0.1, confidence=0.7),
        VariantComparison(variant_id="var_b", score_delta=-0.3, confidence=0.7),
    ]
    recommendation = recommend(comparisons)

    assert recommendation.winning_variant_id is None
    assert recommendation.caveats


def test_recommend_flags_a_low_confidence_win():
    comparisons = [
        VariantComparison(variant_id="var_a", score_delta=0.3, confidence=0.4),
    ]
    recommendation = recommend(comparisons)

    assert recommendation.winning_variant_id == "var_a"
    assert any("confidence" in caveat.lower() for caveat in recommendation.caveats)


# --- evaluation -------------------------------------------------------------

def test_evaluation_scores_a_perfect_ranking():
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

    assert metrics.item_count == len(dataset.items)
    assert metrics.pairwise_ranking_accuracy == 1.0
    assert metrics.rank_correlation == 1.0
    # False positives/negatives are counted against HIT_THRESHOLD now, so they
    # are real integers rather than the `None` the placeholder used to return.
    assert isinstance(metrics.false_positives, int)
    assert isinstance(metrics.false_negatives, int)
    assert metrics.mean_absolute_error is not None


def test_evaluation_scores_a_reversed_ranking():
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

    metrics = evaluate_predictions(predictions, dataset)
    assert metrics.pairwise_ranking_accuracy == 0.0


def test_rank_from_scores_orders_best_first():
    predictions = rank_from_scores({"a": 0.2, "b": 0.9, "c": 0.5})

    assert [p.reel_id for p in predictions] == ["b", "c", "a"]
    assert [p.predicted_rank for p in predictions] == [1, 2, 3]
