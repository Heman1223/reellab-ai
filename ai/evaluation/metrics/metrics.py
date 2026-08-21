"""Evaluation metrics.

The question this module has to answer: **does our simulation predict anything
real?** If our predicted ranking of a creator's past reels does not correlate
with how those reels actually performed, the whole simulation is theatre — and
we would rather find that out on day one than during the demo.

Only the ranking metrics are implemented. Everything else returns `None`
deliberately: an unimplemented metric reported as `0.0` reads as a real,
catastrophic result, and someone will believe it.

OWNER: Developer 1.
"""

from __future__ import annotations

from itertools import combinations
from statistics import mean

from schemas import EvaluationDataset, EvaluationMetrics, Prediction


def pairwise_ranking_accuracy(
    predicted: dict[str, int], actual: dict[str, int]
) -> float | None:
    """Fraction of reel pairs we ordered correctly.

    More honest than a raw correlation on a handful of reels: with four items,
    "we got 5 of 6 pairs right" is interpretable, whereas a correlation
    coefficient is not.
    """
    shared = sorted(set(predicted) & set(actual))
    if len(shared) < 2:
        return None

    pairs = list(combinations(shared, 2))
    correct = sum(
        1
        for left, right in pairs
        if (predicted[left] < predicted[right]) == (actual[left] < actual[right])
    )
    return round(correct / len(pairs), 4)


def spearman_rank_correlation(
    predicted: dict[str, int], actual: dict[str, int]
) -> float | None:
    """Spearman's rho over the reels present in both rankings.

    Hand-rolled rather than pulling in scipy for one formula. Assumes distinct
    ranks, which our datasets have.
    """
    shared = sorted(set(predicted) & set(actual))
    n = len(shared)
    if n < 2:
        return None

    d_squared = sum((predicted[reel_id] - actual[reel_id]) ** 2 for reel_id in shared)
    return round(1 - (6 * d_squared) / (n * (n**2 - 1)), 4)


def evaluate_predictions(
    predictions: list[Prediction], dataset: EvaluationDataset
) -> EvaluationMetrics:
    """Compare a predicted ranking against ground truth."""
    actual = {item.reel_id: item.actual_rank for item in dataset.items}
    predicted = {
        prediction.reel_id: prediction.predicted_rank for prediction in predictions
    }
    shared = set(predicted) & set(actual)

    notes: list[str] = []
    if not shared:
        notes.append("No overlap between predictions and dataset; nothing was measured.")
    elif len(shared) < len(actual):
        notes.append(
            f"Only {len(shared)} of {len(actual)} dataset reels had predictions."
        )
    if len(shared) < 5:
        notes.append(
            "Fewer than 5 reels — treat these numbers as directional at best."
        )
    notes.append(
        "false_positives / false_negatives are not implemented yet "
        "(ai/evaluation/metrics/); null means unmeasured, not zero."
    )

    return EvaluationMetrics(
        item_count=len(shared),
        rank_correlation=spearman_rank_correlation(predicted, actual),
        pairwise_ranking_accuracy=pairwise_ranking_accuracy(predicted, actual),
        # TODO(Developer 1): define a "we predicted a hit" threshold, then count
        # predicted hits that flopped (false positives) and predicted flops that
        # took off (false negatives). Both need a threshold agreed with the team
        # first — picking one silently here would bake in an arbitrary choice.
        false_positives=None,
        false_negatives=None,
        mean_confidence=(
            round(mean(p.confidence for p in predictions), 4) if predictions else None
        ),
        notes=notes,
    )
