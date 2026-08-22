"""Simulation orchestration.

Deterministic control flow around AI decisions. The engine decides *what to ask
and in what order*; it never decides what the answer is.

    content DNA  ->  personas per segment  ->  one viewer agent per persona
                 ->  aggregate per segment ->  propagation cascade
                 ->  bottleneck reflection ->  SimulationResult

## Two entry points

`run_simulation_for_personas(personas, content)` is the core: you bring the
personas, it simulates them. Use this when you already have a persona set, and
in tests.

`run_simulation(request, ...)` is the orchestrator behind `POST
/ai/simulation/run`: it resolves the audience graph, generates personas per
segment, then calls the core. **Its signature is frozen** — Developer 2's
`counterfactual/experiments/experiment.py` calls it with a `SimulationRequest`
and unpacks `(result, mock)`.

## Failure policy

A persona whose call fails is recorded with `error` set, excluded from every
average, and the run finishes with `status='partial'`. Losing one synthetic
viewer is not a reason to throw away the other nineteen.

OWNER: Developer 1.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from audience.segmentation.segmentation import targetable_segments
from audience.discovery.discovery import discover_audience
from config import settings
from logging_utils import get_logger, log_event
from personas.generation.generator import generate_personas
from personas.profiles.profiles import select_within_budget
from propagation.engine.propagation import simulate_propagation
from schemas import (
    AudienceGraph,
    AudienceRequest,
    AudienceSegment,
    ContentDNA,
    Persona,
    PersonaSimulationResult,
    RunMetadata,
    SimulationRequest,
    SimulationResult,
    Warning,
)
from simulation.agents.viewer_agent import failed_result, simulate_persona
from simulation.behavior.aggregation import (
    aggregate_segment,
    analyse_audience,
    compute_confidence,
    disagreement,
    overall_score,
    usable,
)
from simulation.behavior.reflection import analyze_bottlenecks

import fixtures

logger = get_logger("simulation.engine")



#: Cap on concurrent model calls. Personas are embarrassingly parallel, but
#: firing forty at once is a good way to meet a rate limit mid-demo.
DEFAULT_CONCURRENCY = int(os.getenv("AI_SIM_CONCURRENCY", "8"))


@dataclass
class SimulationOptions:
    """Cost and behaviour levers for one run."""

    max_personas: int | None = None
    concurrency: int = DEFAULT_CONCURRENCY
    seed: int | None = None
    #: Skip the AI reflection pass. Useful for a cheap re-simulation of a
    #: counterfactual variant, where only the score delta is wanted.
    explain_bottlenecks: bool = True

    def ceiling(self) -> int:
        return max(1, self.max_personas or settings.max_personas)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Core: personas in, result out
# ---------------------------------------------------------------------------

async def _simulate_one(
    persona: Persona, content: ContentDNA, semaphore: asyncio.Semaphore
) -> tuple[PersonaSimulationResult, bool]:
    """Simulate one persona, converting any failure into a flagged result."""
    async with semaphore:
        print(f"[PERSONA] id: {persona.id}")
        print(f"[PERSONA] model request started for {persona.id}")
        try:
            res = await simulate_persona(persona, content)
            print(f"[PERSONA] model response received for {persona.id}")
            print(f"[PERSONA] validation passed for {persona.id}")
            print(f"[PERSONA] simulation completed for {persona.id}")
            return res
        except Exception as exc:  # noqa: BLE001 — one persona must not kill the run
            print(f"[PERSONA ERROR]")
            print(f"persona_id: {persona.id}")
            print(f"error: {str(exc)[:300]}")
            print(f"raw response type: {type(exc)}")
            print(f"validation error: True")
            log_event(
                logger,
                "persona_simulation_failed",
                persona_id=persona.id,
                error=str(exc)[:300],
            )
            return failed_result(persona, str(exc)), False


async def run_simulation_for_personas(
    personas: list[Persona],
    content: ContentDNA | None,
    *,
    graph: AudienceGraph | None = None,
    options: SimulationOptions | None = None,
    simulation_id: str | None = None,
    reel_id: str | None = None,
    variant_id: str | None = None,
) -> tuple[SimulationResult, bool]:
    """Simulate a persona set against one piece of content. Returns `(result, mock)`.

    Degrades rather than raises: an empty persona set comes back as a `failed`
    result carrying a warning, because a caller that asked for a simulation
    deserves to be told why it is empty rather than handed an exception.
    """
    options = options or SimulationOptions()
    started = _now()
    simulation_id = simulation_id or f"sim_{uuid.uuid4().hex[:8]}"
    warnings: list[Warning] = []
    any_mock = False

    # --- content ----------------------------------------------------------
    if content is None:
        content = fixtures.content_dna()
        any_mock = True
        warnings.append(
            Warning(
                code="MOCK_CONTENT_DNA",
                message="No Content DNA supplied; simulated against the development fixture.",
                severity="info",
            )
        )

    # --- empty persona set ------------------------------------------------
    if not personas:
        warnings.append(
            Warning(
                code="EMPTY_PERSONA_SET",
                message="No personas were available to simulate. Nothing was measured.",
                severity="error",
            )
        )
        return (
            _empty_result(simulation_id, started, reel_id, variant_id, graph, warnings, any_mock),
            any_mock,
        )

    # --- budget -----------------------------------------------------------
    requested = len(personas)
    ceiling = options.ceiling()
    if requested > ceiling:
        personas = select_within_budget(personas, ceiling)
        warnings.append(
            Warning(
                code="PERSONA_CAP_APPLIED",
                message=(
                    f"Capped at {ceiling} personas (wanted {requested}). Segment "
                    "coverage is reduced; confidence is discounted accordingly."
                ),
                severity="warning",
            )
        )
        requested = len(personas)

    # --- viewer agents ----------------------------------------------------
    semaphore = asyncio.Semaphore(max(1, options.concurrency))
    outcomes = await asyncio.gather(
        *(_simulate_one(persona, content, semaphore) for persona in personas)
    )
    persona_results = [result for result, _ in outcomes]
    any_mock = any_mock or any(mock for _, mock in outcomes)

    failures = [result for result in persona_results if result.error is not None]
    if failures:
        warnings.append(
            Warning(
                code="PARTIAL_SIMULATION",
                message=(
                    f"{len(persona_results) - len(failures)}/{len(persona_results)} personas "
                    "completed successfully. The rest were excluded from the averages."
                ),
                severity="warning",
            )
        )

    # --- aggregate --------------------------------------------------------
    segments = _segments_for(personas, graph)
    segment_results = [
        aggregate_segment(
            segment,
            [p for p in personas if p.segment_id == segment.id],
            persona_results,
        )
        for segment in segments
    ]

    # --- propagation ------------------------------------------------------
    waves = simulate_propagation(
        persona_results,
        graph=graph,
        segment_results=segment_results,
        personas=personas,
        seed=options.seed,
    )

    # --- confidence -------------------------------------------------------
    confidence = compute_confidence(persona_results, requested=requested, content=content)
    warnings.extend(
        Warning(code="CONFIDENCE_FACTOR", message=note, severity="info")
        for note in confidence.notes
    )

    # --- reflection -------------------------------------------------------
    bottlenecks = []
    if options.explain_bottlenecks:
        try:
            bottlenecks, reflection_mock = await analyze_bottlenecks(
                content, persona_results, segment_results, waves
            )
            any_mock = any_mock or reflection_mock
        except Exception as exc:  # noqa: BLE001 — a run without a diagnosis is still a run
            log_event(logger, "bottleneck_analysis_failed", error=str(exc)[:300])
            warnings.append(
                Warning(
                    code="BOTTLENECK_ANALYSIS_FAILED",
                    message=f"Could not explain the results: {exc}",
                    severity="warning",
                )
            )

    # --- audience analysis ------------------------------------------------
    analysis = analyse_audience(segment_results, graph)
    warnings.extend(_analysis_warnings(analysis, segment_results))

    if any_mock:
        warnings.append(
            Warning(
                code="MOCK_DATA",
                message="Some or all of this result came from fixtures, not a model.",
                severity="info",
            )
        )

    finished = _now()
    duration_ms = (finished - started).total_seconds() * 1000

    result = SimulationResult(
        simulation_id=simulation_id,
        status="partial" if failures else "completed",
        reel_id=reel_id,
        variant_id=variant_id,
        graph_id=graph.graph_id if graph else None,
        overall_score=overall_score(segment_results),
        confidence=confidence.value,
        audience_results=persona_results,
        propagation_waves=waves,
        audience_segment_results=segment_results,
        bottlenecks=bottlenecks,
        warnings=warnings,
        created_at=started.isoformat(),
        completed_at=finished.isoformat(),
        metadata=RunMetadata(
            model="fixture" if any_mock else settings.reasoning_model,
            prompt_version="viewer-agent-v1",
            persona_count=len(persona_results),
            simulation_duration_ms=round(duration_ms, 2),
            mock=any_mock,
        ),
    )

    log_event(
        logger,
        "simulation_completed",
        simulation_id=simulation_id,
        status=result.status,
        persona_count=len(persona_results),
        failures=len(failures),
        overall_score=result.overall_score,
        confidence=result.confidence,
        disagreement=disagreement(usable(persona_results)),
        strongest=analysis.strongest_segment_id,
        weakest=analysis.weakest_segment_id,
        simulation_duration_ms=round(duration_ms, 2),
        mock=any_mock,
        **confidence.as_fields(),
    )

    return result, any_mock


def _empty_result(
    simulation_id: str,
    started: datetime,
    reel_id: str | None,
    variant_id: str | None,
    graph: AudienceGraph | None,
    warnings: list[Warning],
    mock: bool,
) -> SimulationResult:
    return SimulationResult(
        simulation_id=simulation_id,
        status="failed",
        reel_id=reel_id,
        variant_id=variant_id,
        graph_id=graph.graph_id if graph else None,
        overall_score=0.0,
        confidence=0.0,
        audience_results=[],
        propagation_waves=[],
        audience_segment_results=[],
        bottlenecks=[],
        warnings=warnings,
        created_at=started.isoformat(),
        completed_at=_now().isoformat(),
        metadata=RunMetadata(model="none", persona_count=0, mock=mock),
    )


def _segments_for(personas: list[Persona], graph: AudienceGraph | None) -> list[AudienceSegment]:
    """The segments actually represented in this persona set.

    Synthesises a placeholder segment for any persona whose segment is not in
    the graph, so a hand-assembled persona list still aggregates instead of
    silently producing zero segment results.
    """
    known = {segment.id: segment for segment in graph.segments} if graph else {}
    ordered: list[AudienceSegment] = []
    seen: set[str] = set()

    for persona in personas:
        if persona.segment_id in seen:
            continue
        seen.add(persona.segment_id)
        ordered.append(
            known.get(persona.segment_id)
            or AudienceSegment(
                id=persona.segment_id,
                name=persona.segment_id.replace("_", " ").strip().title() or "Unnamed segment",
                description="Segment not present in the audience graph.",
                parent_segment=None,
                characteristics=[],
                relevance_score=0.5,
            )
        )

    return ordered


def _analysis_warnings(analysis, segment_results) -> list[Warning]:
    """Surface the audience-level findings as warnings the frontend can render."""
    by_id = {result.segment_id: result for result in segment_results}
    notes: list[Warning] = []

    if analysis.strongest_segment_id and analysis.weakest_segment_id:
        strongest = by_id.get(analysis.strongest_segment_id)
        weakest = by_id.get(analysis.weakest_segment_id)
        if strongest and weakest and strongest.segment_id != weakest.segment_id:
            notes.append(
                Warning(
                    code="SEGMENT_SPREAD",
                    message=(
                        f"Strongest: {strongest.segment_name} ({strongest.score:.2f}). "
                        f"Weakest: {weakest.segment_name} ({weakest.score:.2f})."
                    ),
                    severity="info",
                )
            )

    if analysis.cross_niche_segment_ids:
        names = [
            by_id[segment_id].segment_name
            for segment_id in analysis.cross_niche_segment_ids
            if segment_id in by_id
        ]
        if names:
            notes.append(
                Warning(
                    code="CROSS_NICHE_OPPORTUNITY",
                    message=(
                        f"{', '.join(names)} performed well despite not being a primary "
                        "target — an audience you are reaching without aiming at."
                    ),
                    severity="info",
                )
            )

    if analysis.largest_dropoff_segment_id and analysis.largest_dropoff_delta > 0.2:
        segment = by_id.get(analysis.largest_dropoff_segment_id)
        if segment:
            notes.append(
                Warning(
                    code="LARGEST_DROPOFF",
                    message=(
                        f"{segment.segment_name} has the widest gap between starting and "
                        f"finishing ({analysis.largest_dropoff_delta:.0%})."
                    ),
                    severity="info",
                )
            )

    return notes


# ---------------------------------------------------------------------------
# Orchestrator: request in, result out
# ---------------------------------------------------------------------------

async def run_simulation(
    request: SimulationRequest,
    content: ContentDNA | None = None,
    graph: AudienceGraph | None = None,
) -> tuple[SimulationResult, bool]:
    """Resolve an audience, generate personas, and simulate. Returns `(result, mock)`."""
    options = SimulationOptions(seed=None)

    content_dna = content or request.content_dna
    any_mock = False

    audience_graph = graph
    if not audience_graph:
        if content_dna or request.custom_audience:
            audience_req = AudienceRequest(
                niche=request.custom_audience or (content_dna.topic if content_dna else "Video Content"),
                target_audience=request.custom_audience or "General Audience",
                location="Global",
                language="English",
                creator_goal="Maximize engagement and reach"
            )
            audience_graph, amock = await discover_audience(audience_req)
            any_mock = any_mock or amock
        else:
            audience_graph = fixtures.audience_graph()
            any_mock = True

    segments = targetable_segments(audience_graph) or audience_graph.segments
    
    # We want exactly 10 personas total.
    total_personas = 10
    if not segments:
        raise RuntimeError("No targetable segments found in audience graph.")
        
    base_count = total_personas // len(segments)
    remainder = total_personas % len(segments)

    personas: list[Persona] = []
    generation_warnings: list[Warning] = []

    async def _generate_for_segment(segment: AudienceSegment, count: int):
        if count <= 0:
            return [], False, None
        try:
            generated, mock = await generate_personas(
                segment, count, audience_graph.request.creator_goal
            )
            return generated, mock, None
        except Exception as exc:  # noqa: BLE001
            log_event(
                logger,
                "persona_generation_failed",
                segment_id=segment.id,
                error=str(exc)[:300],
            )
            return [], False, Warning(
                code="PERSONA_GENERATION_FAILED",
                message=f"Could not generate personas for '{segment.name}': {exc}",
                severity="warning",
            )

    tasks = []
    for i, s in enumerate(segments):
        count = base_count + (1 if i < remainder else 0)
        tasks.append(_generate_for_segment(s, count))

    results = await asyncio.gather(*tasks)
    for gen, mock, warn in results:
        personas.extend(gen)
        any_mock = any_mock or mock
        if warn:
            generation_warnings.append(warn)

    result, mock = await run_simulation_for_personas(
        personas,
        content_dna,
        graph=audience_graph,
        options=options,
        simulation_id=request.simulation_id,
        reel_id=request.reel_id,
        variant_id=request.variant_id,
    )

    if generation_warnings:
        result = result.model_copy(
            update={"warnings": [*generation_warnings, *result.warnings]}
        )

    return result, any_mock or mock


def segments_by_id(graph: AudienceGraph) -> dict[str, AudienceSegment]:
    return {segment.id: segment for segment in graph.segments}
