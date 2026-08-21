"""Evaluation harness.

The loop we are trying to close:

    historical reel -> our simulation -> predicted ranking
                                              |  compare
                                actual performance (data/evaluation/)

`run_evaluation` scores predictions someone hands it. `simulate_dataset` closes
the loop end to end, but needs Content DNA per historical reel — the
`contentDnaRef` field in the dataset — which is Developer 2's pipeline. Until
that exists it raises rather than pretending.

OWNER: Developer 1.
"""

from __future__ import annotations

from schemas import (
    ContentDNA,
    EvaluationDataset,
    EvaluationItem,
    EvaluationMetrics,
    Persona,
    Prediction,
)
from logging_utils import get_logger, log_event

from ..datasets.loader import load_dataset
from ..metrics.metrics import evaluate_predictions

logger = get_logger("evaluation.harness")


def run_evaluation(
    predictions: list[Prediction],
    dataset_id: str | None = None,
    actuals: EvaluationDataset | list[EvaluationItem] | None = None,
) -> EvaluationMetrics:
    """Score a set of predictions against ground truth."""
    dataset = actuals if actuals is not None else load_dataset(dataset_id)
    metrics = evaluate_predictions(predictions, dataset)

    log_event(
        logger,
        "evaluation_completed",
        dataset_id=dataset_id,
        item_count=metrics.item_count,
        rank_correlation=metrics.rank_correlation,
        pairwise_ranking_accuracy=metrics.pairwise_ranking_accuracy,
        mean_absolute_error=metrics.mean_absolute_error,
        confidence_calibration=metrics.confidence_calibration,
    )
    return metrics


def rank_from_scores(
    scores: dict[str, float], confidences: dict[str, float] | None = None
) -> list[Prediction]:
    """Turn `{reel_id: score}` into ranked predictions, best first.

    Pass `confidences` from the simulations themselves. Without it every
    prediction reports 0.5, and confidence calibration becomes unmeasurable —
    which is exactly the metric we most want.
    """
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        Prediction(
            reel_id=reel_id,
            predicted_score=score,
            predicted_rank=index + 1,
            confidence=(confidences or {}).get(reel_id, 0.5),
        )
        for index, (reel_id, score) in enumerate(ordered)
    ]


async def simulate_dataset(
    dataset: EvaluationDataset,
    personas: list[Persona],
    content_by_reel: dict[str, ContentDNA],
) -> list[Prediction]:
    """Run the full simulation over every reel in a dataset.

    Deliberately takes the persona set and the Content DNA as arguments rather
    than resolving them: every reel in a sweep must be simulated against the
    **same** personas, or the comparison measures the personas instead of the
    reels.
    """
    from simulation.engine.engine import SimulationOptions, run_simulation_for_personas

    scores: dict[str, float] = {}
    confidences: dict[str, float] = {}
    # Bottleneck explanation costs a model call per reel and is not used by any
    # ranking metric, so a sweep skips it.
    options = SimulationOptions(explain_bottlenecks=False)

    for item in dataset.items:
        content = content_by_reel.get(item.reel_id)
        if content is None:
            log_event(logger, "evaluation_item_skipped", reel_id=item.reel_id, reason="no_content_dna")
            continue

        result, _ = await run_simulation_for_personas(
            personas, content, options=options, reel_id=item.reel_id
        )
        scores[item.reel_id] = result.overall_score
        confidences[item.reel_id] = result.confidence

    if not scores:
        raise ValueError(
            "No reel in the dataset had Content DNA. Populate `contentDnaRef` "
            "(Developer 2's pipeline) before running a sweep."
        )

    log_event(logger, "dataset_simulated", dataset_id=dataset.dataset_id, reels=len(scores))
    return rank_from_scores(scores, confidences)
