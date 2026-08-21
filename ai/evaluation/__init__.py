"""Evaluation: does the simulation predict anything real? OWNER: Developer 1.

Public surface:

    evaluate_predictions(predictions, actuals) -> EvaluationMetrics
    run_evaluation(predictions, dataset_id?)   -> EvaluationMetrics
    rank_from_scores(scores, confidences?)     -> list[Prediction]
    simulate_dataset(dataset, personas, dna)   -> list[Prediction]
"""

from .datasets.loader import actual_ranking, load_dataset
from .harness.harness import rank_from_scores, run_evaluation, simulate_dataset
from .metrics.metrics import (
    HIT_THRESHOLD,
    actual_performance_score,
    confidence_calibration,
    evaluate_predictions,
    pairwise_ranking_accuracy,
    spearman_rank_correlation,
)

__all__ = [
    "actual_ranking",
    "load_dataset",
    "rank_from_scores",
    "run_evaluation",
    "simulate_dataset",
    "HIT_THRESHOLD",
    "actual_performance_score",
    "confidence_calibration",
    "evaluate_predictions",
    "pairwise_ranking_accuracy",
    "spearman_rank_correlation",
]
