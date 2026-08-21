"""Evaluation harness.

The loop we are trying to close:

    historical reel → our simulation → predicted ranking
                                            ↕ compare
                              actual performance (data/evaluation/)

Right now the harness only scores predictions someone hands it. Running the full
simulation over a dataset is the next step and needs the Content DNA for each
historical reel to exist first — `content_dna_ref` in the dataset is where that
goes.

OWNER: Developer 1.
"""

from __future__ import annotations

from logging_utils import get_logger, log_event
from schemas import EvaluationDataset, EvaluationMetrics, Prediction

from ..datasets.loader import load_dataset
from ..metrics.metrics import evaluate_predictions

logger = get_logger("evaluation.harness")


def run_evaluation(
    predictions: list[Prediction],
    dataset_id: str | None = None,
) -> EvaluationMetrics:
    """Score a set of predictions against a dataset."""
    dataset = load_dataset(dataset_id)
    metrics = evaluate_predictions(predictions, dataset)

    log_event(
        logger,
        "evaluation_completed",
        dataset_id=dataset.dataset_id,
        item_count=metrics.item_count,
        rank_correlation=metrics.rank_correlation,
        pairwise_ranking_accuracy=metrics.pairwise_ranking_accuracy,
    )
    return metrics


def rank_from_scores(scores: dict[str, float]) -> list[Prediction]:
    """Turn `{reel_id: score}` into ranked predictions, best first."""
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        Prediction(
            reel_id=reel_id,
            predicted_score=score,
            predicted_rank=index + 1,
            # Placeholder: the caller should pass the simulation's own confidence.
            confidence=0.5,
        )
        for index, (reel_id, score) in enumerate(ordered)
    ]


async def simulate_dataset(dataset: EvaluationDataset) -> list[Prediction]:
    """Run the full simulation over every reel in a dataset.

    TODO(Developer 1):
      1. For each item, load or produce its Content DNA (`content_dna_ref`).
      2. Run the simulation against a fixed audience graph — the same graph for
         every reel, or the comparison measures the graph rather than the reels.
      3. Rank by `overall_score` and hand the result to `run_evaluation`.

    Pin the audience graph and the prompt versions across the whole sweep.
    Without that, a re-run measures prompt drift instead of reel quality.
    """
    raise NotImplementedError(
        f"simulate_dataset is not implemented yet (ai/evaluation/harness/). "
        f"Dataset '{dataset.dataset_id}' has {len(dataset.items)} items."
    )
