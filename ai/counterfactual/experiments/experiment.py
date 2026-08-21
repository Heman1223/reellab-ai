"""Running a counterfactual experiment end to end.

    run_experiment(request) -> CounterfactualExperiment

    generate a hypothesis  →  generate variants  →  re-simulate each variant
                           →  compare against the baseline  →  recommend

The comparison arithmetic is deterministic; the hypothesis and the
recommendation are AI. That split is deliberate — we want the deltas to be
reproducible, and we want the reasoning about what they *mean* to be inspectable
prose rather than a threshold nobody remembers choosing.

OWNER: Developer 2 (with Developer 1 owning the re-simulation it calls).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from logging_utils import get_logger, log_event
from schemas import (
    ContentDNA,
    CounterfactualExperiment,
    ExperimentRequest,
    Recommendation,
    RunMetadata,
    SimulationRequest,
    SimulationResult,
    Variant,
    VariantComparison,
)
from simulation.engine.engine import run_simulation

import fixtures

from ..generation.variants import generate_variants

logger = get_logger("counterfactual.experiments")


def compare(
    baseline: SimulationResult, variant: Variant, variant_result: SimulationResult
) -> VariantComparison:
    """Deterministic head-to-head between a variant run and the baseline."""
    baseline_by_segment = {
        result.segment_id: result.score for result in baseline.audience_segment_results
    }

    segment_deltas: dict[str, float] = {}
    for result in variant_result.audience_segment_results:
        before = baseline_by_segment.get(result.segment_id)
        if before is not None:
            segment_deltas[result.segment_id] = round(result.score - before, 4)

    gain = max(segment_deltas.items(), key=lambda item: item[1], default=None)
    loss = min(segment_deltas.items(), key=lambda item: item[1], default=None)

    return VariantComparison(
        variant_id=variant.id,
        score_delta=round(variant_result.overall_score - baseline.overall_score, 4),
        segment_deltas=segment_deltas,
        biggest_gain_segment_id=gain[0] if gain and gain[1] > 0 else None,
        biggest_loss_segment_id=loss[0] if loss and loss[1] < 0 else None,
        confidence=round(min(baseline.confidence, variant_result.confidence), 4),
    )


def recommend(comparisons: list[VariantComparison]) -> Recommendation:
    """Pick a winner, and be explicit about how much to trust the pick.

    A win inside the noise of a small persona sample is not a win, and saying so
    is more useful to the creator than a confident-sounding number.
    """
    if not comparisons:
        return Recommendation(
            winning_variant_id=None,
            reasoning="No variants were simulated, so there is nothing to compare.",
            confidence=0.0,
            caveats=["No comparison data."],
        )

    best = max(comparisons, key=lambda comparison: comparison.score_delta)
    caveats: list[str] = []

    if best.score_delta <= 0:
        return Recommendation(
            winning_variant_id=None,
            reasoning=(
                "No variant beat the original. The bottleneck is probably not the "
                "one this experiment targeted — try a different modification type."
            ),
            confidence=best.confidence,
            caveats=["All variants scored at or below the baseline."],
        )

    if best.confidence < 0.6:
        caveats.append(
            "Confidence is below 0.6; re-run at a higher depth before acting on this."
        )

    runner_up = sorted(comparisons, key=lambda c: c.score_delta, reverse=True)[1:2]
    if runner_up and abs(best.score_delta - runner_up[0].score_delta) < 0.05:
        caveats.append(
            "The top two variants are within 0.05 of each other — that gap is inside "
            "the noise of a small persona sample."
        )

    if best.biggest_loss_segment_id:
        caveats.append(
            f"This variant costs reach in segment '{best.biggest_loss_segment_id}'."
        )

    return Recommendation(
        winning_variant_id=best.variant_id,
        reasoning=(
            f"Variant {best.variant_id} improves the overall score by "
            f"{best.score_delta:+.2f}, with its largest gain in segment "
            f"'{best.biggest_gain_segment_id or 'n/a'}'."
        ),
        confidence=best.confidence,
        caveats=caveats,
    )


async def run_experiment(
    request: ExperimentRequest,
    baseline: SimulationResult | None = None,
    content: ContentDNA | None = None,
) -> tuple[CounterfactualExperiment, bool]:
    """Generate variants, re-simulate them, and compare. Returns `(experiment, mock)`."""
    started = datetime.now(timezone.utc)
    experiment_id = request.experiment_id or f"exp_{uuid.uuid4().hex[:8]}"

    any_mock = False
    if baseline is None:
        baseline = fixtures.simulation_result()
        any_mock = True
    if content is None:
        content = fixtures.content_dna()
        any_mock = True

    variants, mock = await generate_variants(
        content,
        baseline,
        request.modification_type,
        request.variant_count,
        request.instruction,
    )
    any_mock = any_mock or mock

    comparisons: list[VariantComparison] = []
    simulated: list[Variant] = []

    for variant in variants:
        try:
            variant_result, variant_mock = await run_simulation(
                SimulationRequest(
                    reel_id=baseline.reel_id,
                    content_dna=variant.predicted_content_dna or content,
                    graph_id=baseline.graph_id,
                    variant_id=variant.id,
                )
            )
            any_mock = any_mock or variant_mock

            comparisons.append(compare(baseline, variant, variant_result))
            simulated.append(
                variant.model_copy(
                    update={
                        "simulation_id": variant_result.simulation_id,
                        "score": variant_result.overall_score,
                    }
                )
            )
        except Exception as exc:  # noqa: BLE001 — one bad variant must not sink the experiment
            log_event(logger, "variant_simulation_failed", variant_id=variant.id, error=str(exc))
            simulated.append(variant)

    finished = datetime.now(timezone.utc)

    experiment = CounterfactualExperiment(
        experiment_id=experiment_id,
        original_simulation_id=request.original_simulation_id,
        hypothesis=_hypothesis_for(baseline, request.modification_type),
        modification_type=request.modification_type,
        variants=simulated,
        comparison=comparisons,
        recommendation=recommend(comparisons),
        status="completed" if comparisons else "failed",
        created_at=started.isoformat(),
        completed_at=finished.isoformat(),
        metadata=RunMetadata(
            model="fixture" if any_mock else "mixed",
            prompt_version="variant-generation-v0",
            simulation_duration_ms=(finished - started).total_seconds() * 1000,
            mock=any_mock,
        ),
    )

    log_event(
        logger,
        "experiment_completed",
        experiment_id=experiment_id,
        variant_count=len(simulated),
        compared=len(comparisons),
        winner=experiment.recommendation.winning_variant_id,
        mock=any_mock,
    )

    return experiment, any_mock


def _hypothesis_for(baseline: SimulationResult, modification_type: str) -> str:
    """State the claim the experiment tests, grounded in the worst bottleneck.

    TODO(Developer 2): have the model write this. A hypothesis assembled from a
    template is a label, not a claim — and the claim is what makes the result
    falsifiable.
    """
    if not baseline.bottlenecks:
        return f"Changing the {modification_type} will improve overall performance."

    worst = max(baseline.bottlenecks, key=lambda bottleneck: bottleneck.severity)
    return (
        f"The reel is limited by its {worst.stage}: {worst.likely_cause} "
        f"Changing the {modification_type} should address this."
    )
