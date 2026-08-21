"""Simulation orchestration.

    run_simulation(request) -> SimulationResult

Deterministic control flow around AI decisions. The engine decides *what to ask
and in what order*; it never decides what the answer is.

Pipeline:

    content DNA  →  personas per segment  →  one viewer agent per persona
                 →  aggregate per segment →  propagation cascade
                 →  bottleneck reflection →  SimulationResult

Failure policy: a persona whose call fails is recorded with `error` set and
excluded from the averages, and the run finishes with `status='partial'`. Losing
one synthetic viewer is not a reason to throw away the other twenty.

OWNER: Developer 1.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from audience.segmentation.segmentation import targetable_segments
from config import settings
from logging_utils import get_logger, log_event
from personas.generation.generator import generate_personas
from propagation.engine.propagation import simulate_propagation
from schemas import (
    AudienceGraph,
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
    aggregate_confidence,
    aggregate_segment,
    overall_score,
    usable,
)
from simulation.behavior.reflection import analyze_bottlenecks

import fixtures

logger = get_logger("simulation.engine")

#: How many personas each depth simulates per segment. Depth is the main lever
#: between a five-second demo run and a run worth trusting.
DEPTH_PERSONAS_PER_SEGMENT = {"quick": 2, "standard": 4, "deep": 8}

#: Cap on concurrent model calls. Personas are embarrassingly parallel, but
#: firing forty at once is a good way to meet a rate limit mid-demo.
MAX_CONCURRENCY = 8


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _simulate_one(
    persona: Persona, content: ContentDNA, semaphore: asyncio.Semaphore
) -> tuple[PersonaSimulationResult, bool]:
    async with semaphore:
        try:
            return await simulate_persona(persona, content)
        except Exception as exc:  # noqa: BLE001 — one persona must not kill the run
            log_event(logger, "persona_simulation_failed", persona_id=persona.id, error=str(exc))
            return failed_result(persona, str(exc)), False


async def run_simulation(
    request: SimulationRequest,
    content: ContentDNA | None = None,
    graph: AudienceGraph | None = None,
) -> tuple[SimulationResult, bool]:
    """Run a full simulation. Returns `(result, mock)`."""
    started = datetime.now(timezone.utc)
    simulation_id = request.simulation_id or f"sim_{uuid.uuid4().hex[:8]}"
    warnings: list[Warning] = []
    any_mock = False

    # ---- 1. Content ------------------------------------------------------
    content_dna = content or request.content_dna
    if content_dna is None:
        content_dna = fixtures.content_dna()
        any_mock = True
        warnings.append(
            Warning(
                code="MOCK_CONTENT_DNA",
                message="No Content DNA supplied; simulated against the development fixture.",
                severity="info",
            )
        )

    # ---- 2. Audience -----------------------------------------------------
    audience_graph = graph or fixtures.audience_graph()
    segments = targetable_segments(audience_graph)
    if not segments:
        segments = audience_graph.segments

    per_segment = DEPTH_PERSONAS_PER_SEGMENT.get(request.depth, 4)

    # ---- 3. Personas -----------------------------------------------------
    personas_by_segment: dict[str, list[Persona]] = {}
    for segment in segments:
        try:
            personas, mock = await generate_personas(
                segment, per_segment, audience_graph.request.creator_goal
            )
            any_mock = any_mock or mock
            personas_by_segment[segment.id] = personas
        except Exception as exc:  # noqa: BLE001
            log_event(logger, "persona_generation_failed", segment_id=segment.id, error=str(exc))
            personas_by_segment[segment.id] = []
            warnings.append(
                Warning(
                    code="PERSONA_GENERATION_FAILED",
                    message=f"Could not generate personas for '{segment.name}': {exc}",
                    severity="warning",
                )
            )

    all_personas = [p for group in personas_by_segment.values() for p in group]
    if not all_personas:
        raise RuntimeError("No personas available; cannot simulate.")

    if len(all_personas) > settings.max_personas:
        warnings.append(
            Warning(
                code="PERSONA_CAP_APPLIED",
                message=(
                    f"Capped at AI_MAX_PERSONAS={settings.max_personas} "
                    f"(wanted {len(all_personas)}). Segment coverage is reduced."
                ),
                severity="warning",
            )
        )
        all_personas = all_personas[: settings.max_personas]
        kept = {persona.id for persona in all_personas}
        personas_by_segment = {
            segment_id: [p for p in group if p.id in kept]
            for segment_id, group in personas_by_segment.items()
        }

    # ---- 4. Viewer agents ------------------------------------------------
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    outcomes = await asyncio.gather(
        *(_simulate_one(persona, content_dna, semaphore) for persona in all_personas)
    )
    persona_results = [result for result, _ in outcomes]
    any_mock = any_mock or any(mock for _, mock in outcomes)

    failures = [result for result in persona_results if result.error is not None]
    if failures:
        warnings.append(
            Warning(
                code="PARTIAL_SIMULATION",
                message=(
                    f"{len(failures)} of {len(persona_results)} personas failed and were "
                    "excluded from the averages."
                ),
                severity="warning",
            )
        )

    # ---- 5. Aggregate ----------------------------------------------------
    segment_results = [
        aggregate_segment(segment, personas_by_segment.get(segment.id, []), persona_results)
        for segment in segments
    ]

    # ---- 6. Propagation --------------------------------------------------
    waves = simulate_propagation(audience_graph, segment_results, persona_results)

    # ---- 7. Reflection ---------------------------------------------------
    try:
        bottlenecks, mock = await analyze_bottlenecks(
            content_dna, persona_results, segment_results, waves
        )
        any_mock = any_mock or mock
    except Exception as exc:  # noqa: BLE001 — a run without a diagnosis is still a run
        log_event(logger, "bottleneck_analysis_failed", error=str(exc))
        bottlenecks = []
        warnings.append(
            Warning(
                code="BOTTLENECK_ANALYSIS_FAILED",
                message=f"Could not explain the results: {exc}",
                severity="warning",
            )
        )

    if any_mock:
        warnings.append(
            Warning(
                code="MOCK_DATA",
                message="Some or all of this result came from fixtures, not a model.",
                severity="info",
            )
        )

    finished = datetime.now(timezone.utc)
    duration_ms = (finished - started).total_seconds() * 1000

    result = SimulationResult(
        simulation_id=simulation_id,
        status="partial" if failures else "completed",
        reel_id=request.reel_id,
        variant_id=request.variant_id,
        graph_id=audience_graph.graph_id,
        overall_score=overall_score(segment_results),
        confidence=aggregate_confidence(usable(persona_results)),
        audience_results=persona_results,
        propagation_waves=waves,
        audience_segment_results=segment_results,
        bottlenecks=bottlenecks,
        warnings=warnings,
        created_at=started.isoformat(),
        completed_at=finished.isoformat(),
        metadata=RunMetadata(
            model="fixture" if any_mock else settings.reasoning_model,
            prompt_version="viewer-agent-v0",
            persona_count=len(persona_results),
            simulation_duration_ms=duration_ms,
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
        simulation_duration_ms=duration_ms,
        mock=any_mock,
    )

    return result, any_mock


def segments_by_id(graph: AudienceGraph) -> dict[str, AudienceSegment]:
    return {segment.id: segment for segment in graph.segments}
