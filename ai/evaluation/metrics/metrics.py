"""Evaluation metrics.

The question this module answers: **does the simulation predict anything real?**
If our predicted ranking of a creator's past reels does not correlate with how
those reels actually performed, the simulation is theatre — and we would rather
find that out on day one than during the demo.

Unimplemented metrics return `None`, never `0.0`. A metric nobody has written
yet, reported as zero, reads as a real and catastrophic result, and someone will
believe it.

OWNER: Developer 1.
"""

from __future__ import annotations

from itertools import combinations
from statistics import mean, pstdev

from schemas import (
    ActualPerformance,
    EvaluationDataset,
    EvaluationItem,
    EvaluationMetrics,
    Prediction,
)

#: Weights for collapsing real-world metrics onto one 0-1 number, mirroring the
#: simulation's own funnel weights in `simulation.behavior.aggregation` so the
#: two are comparable. Change them together or the comparison is meaningless.
ACTUAL_WEIGHTS = {
    "three_second_retention": 0.35,
    "completion_rate": 0.40,
    "share_rate": 0.15,
    "save_rate": 0.10,
}

#: Engagement rates are small numbers; scale them onto 0-1 before blending, or
#: share and save contribute nothing. 5% share is an exceptional reel.
RATE_CEILING = {"share_rate": 0.05, "save_rate": 0.08}

#: What counts as "we predicted a hit". Used only for the false positive and
#: false negative counts. Arbitrary but explicit — argue with the number, not
#: with a hidden default.
HIT_THRESHOLD = 0.5


def actual_performance_score(actual: ActualPerformance) -> float:
    """Collapse real metrics onto the same 0-1 scale as `overallScore`."""
    parts = {
        "three_second_retention": actual.three_second_retention,
        "completion_rate": actual.completion_rate,
        "share_rate": min(1.0, actual.share_rate / RATE_CEILING["share_rate"]),
        "save_rate": min(1.0, actual.save_rate / RATE_CEILING["save_rate"]),
    }
    return round(sum(parts[key] * weight for key, weight in ACTUAL_WEIGHTS.items()), 4)


def pairwise_ranking_accuracy(
    predicted: dict[str, int], actual: dict[str, int]
) -> float | None:
    """Fraction of reel pairs we ordered correctly.

    More honest than a correlation on a handful of reels: with four items,
    "5 of 6 pairs right" is interpretable, whereas a coefficient is not.
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


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation. `None` when either series is constant."""
    if len(xs) < 2 or len(ys) != len(xs):
        return None

    mean_x, mean_y = mean(xs), mean(ys)
    sd_x, sd_y = pstdev(xs), pstdev(ys)
    if sd_x == 0 or sd_y == 0:
        return None

    covariance = mean((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return round(covariance / (sd_x * sd_y), 4)


def confidence_calibration(
    predictions: list[Prediction], errors: dict[str, float]
) -> float | None:
    """Does stated confidence track actual accuracy?

    Correlation between confidence and `1 - absolute error`. Positive means the
    system knows when it is on solid ground. **Near zero is the finding that
    matters**: it means the confidence number is decoration, and the "handle
    being wrong" claim does not hold.
    """
    paired = [(p.confidence, 1.0 - errors[p.reel_id]) for p in predictions if p.reel_id in errors]
    if len(paired) < 2:
        return None
    return pearson([c for c, _ in paired], [a for _, a in paired])


def _as_items(actuals: EvaluationDataset | list[EvaluationItem]) -> list[EvaluationItem]:
    return actuals.items if isinstance(actuals, EvaluationDataset) else list(actuals)


def evaluate_predictions(
    predictions: list[Prediction],
    actuals: EvaluationDataset | list[EvaluationItem],
) -> EvaluationMetrics:
    """Compare a predicted ranking against ground truth.

    `actuals` accepts a whole dataset or a bare list of items, so the harness and
    an ad-hoc caller can both use it.
    """
    items = _as_items(actuals)
    actual_rank = {item.reel_id: item.actual_rank for item in items}
    actual_score = {item.reel_id: actual_performance_score(item.actual) for item in items}
    predicted_rank = {p.reel_id: p.predicted_rank for p in predictions}

    shared = set(predicted_rank) & set(actual_rank)
    notes: list[str] = []

    if not shared:
        notes.append("No overlap between predictions and dataset; nothing was measured.")
    elif len(shared) < len(actual_rank):
        notes.append(f"Only {len(shared)} of {len(actual_rank)} dataset reels had predictions.")
    if 0 < len(shared) < 5:
        notes.append("Fewer than 5 reels — treat these numbers as directional at best.")

    errors = {
        p.reel_id: abs(p.predicted_score - actual_score[p.reel_id])
        for p in predictions
        if p.reel_id in actual_score
    }

    false_positives = sum(
        1
        for p in predictions
        if p.reel_id in actual_score
        and p.predicted_score >= HIT_THRESHOLD
        and actual_score[p.reel_id] < HIT_THRESHOLD
    )
    false_negatives = sum(
        1
        for p in predictions
        if p.reel_id in actual_score
        and p.predicted_score < HIT_THRESHOLD
        and actual_score[p.reel_id] >= HIT_THRESHOLD
    )

    calibration = confidence_calibration(predictions, errors)
    if calibration is not None and abs(calibration) < 0.2:
        notes.append(
            "Confidence barely correlates with accuracy — the confidence number is "
            "not yet carrying information."
        )

    return EvaluationMetrics(
        item_count=len(shared),
        rank_correlation=spearman_rank_correlation(predicted_rank, actual_rank),
        pairwise_ranking_accuracy=pairwise_ranking_accuracy(predicted_rank, actual_rank),
        mean_absolute_error=round(mean(errors.values()), 4) if errors else None,
        false_positives=false_positives if errors else None,
        false_negatives=false_negatives if errors else None,
        mean_confidence=round(mean(p.confidence for p in predictions), 4) if predictions else None,
        confidence_calibration=calibration,
        notes=notes,
    )
