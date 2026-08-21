"""Evaluation contracts.

These have no TypeScript mirror yet — evaluation is an internal AI concern for
now. Add one to `shared/schemas/` only when the frontend needs to display it.
"""

from __future__ import annotations

from pydantic import Field

from .base import ReelLabModel


class ActualPerformance(ReelLabModel):
    """Real-world metrics for a reel, from creator analytics."""

    views: int = Field(ge=0)
    three_second_retention: float = Field(ge=0.0, le=1.0)
    completion_rate: float = Field(ge=0.0, le=1.0)
    like_rate: float = Field(ge=0.0, le=1.0)
    save_rate: float = Field(ge=0.0, le=1.0)
    share_rate: float = Field(ge=0.0, le=1.0)
    comment_rate: float = Field(ge=0.0, le=1.0)


class EvaluationItem(ReelLabModel):
    reel_id: str
    title: str | None = None
    content_dna_ref: str | None = None
    actual: ActualPerformance
    actual_rank: int = Field(ge=1)


class EvaluationDataset(ReelLabModel):
    dataset_id: str
    description: str | None = None
    audience_graph_id: str | None = None
    items: list[EvaluationItem] = Field(default_factory=list)


class Prediction(ReelLabModel):
    reel_id: str
    predicted_score: float = Field(ge=0.0, le=1.0)
    predicted_rank: int = Field(ge=1)
    confidence: float = Field(ge=0.0, le=1.0)


class EvaluationMetrics(ReelLabModel):
    """What we report when asked 'does this simulation predict anything real?'

    Every field is `None` until someone implements it — an unimplemented metric
    reported as `0.0` would read as a real, terrible result.
    """

    item_count: int = Field(ge=0)
    rank_correlation: float | None = None
    pairwise_ranking_accuracy: float | None = None
    false_positives: int | None = None
    false_negatives: int | None = None
    mean_confidence: float | None = None
    notes: list[str] = Field(default_factory=list)


class EvaluationRequest(ReelLabModel):
    dataset_id: str | None = None
    predictions: list[Prediction] = Field(default_factory=list)
