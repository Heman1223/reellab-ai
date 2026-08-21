"""Pydantic mirror of `shared/schemas/experiment.ts`."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ReelLabModel
from .content import ContentDNA
from .simulation import RunMetadata

ModificationType = Literal["hook", "duration", "cta", "tone", "pacing", "audience"]


class Variant(ReelLabModel):
    """A proposed change plus the Content DNA it would produce.

    Simulating `predicted_content_dna` is what makes the counterfactual cheap:
    the creator never has to re-edit the video to find out whether the change
    would have worked.
    """

    id: str
    label: str
    change_summary: str
    proposed_change: str
    predicted_content_dna: ContentDNA | None = None
    simulation_id: str | None = None
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class VariantComparison(ReelLabModel):
    variant_id: str
    score_delta: float
    segment_deltas: dict[str, float] = Field(default_factory=dict)
    biggest_gain_segment_id: str | None = None
    biggest_loss_segment_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class Recommendation(ReelLabModel):
    winning_variant_id: str | None = None
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
    caveats: list[str] = Field(default_factory=list)


class CounterfactualExperiment(ReelLabModel):
    experiment_id: str
    original_simulation_id: str
    hypothesis: str
    modification_type: ModificationType
    variants: list[Variant] = Field(default_factory=list)
    comparison: list[VariantComparison] = Field(default_factory=list)
    recommendation: Recommendation
    status: Literal["queued", "generating", "simulating", "completed", "failed"] = "completed"
    created_at: str
    completed_at: str | None = None
    metadata: RunMetadata | None = None


class ExperimentRequest(ReelLabModel):
    experiment_id: str | None = None
    original_simulation_id: str
    modification_type: ModificationType
    instruction: str | None = None
    variant_count: int = Field(default=2, ge=1, le=5)
