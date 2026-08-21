"""Pydantic mirror of `shared/schemas/result.ts`."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ReelLabModel
from .simulation import (
    PersonaSimulationResult,
    PropagationWave,
    RunMetadata,
    SimulationStatus,
)


class AudienceSegmentResult(ReelLabModel):
    segment_id: str
    segment_name: str
    score: float = Field(ge=0.0, le=1.0)
    average_watch_probability: float = Field(ge=0.0, le=1.0)
    average_completion_probability: float = Field(ge=0.0, le=1.0)
    share_rate: float = Field(ge=0.0, le=1.0)
    save_rate: float = Field(ge=0.0, le=1.0)
    persona_count: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    verdict: Literal["strong", "mixed", "weak"]


class Bottleneck(ReelLabModel):
    """Where the reel loses the audience, and why.

    `likely_cause` is the output the creator actually acts on — a bottleneck
    without a causal hypothesis is just a number.
    """

    id: str
    stage: Literal["hook", "retention", "payoff", "cta", "propagation"]
    segment_ids: list[str] = Field(default_factory=list)
    description: str
    likely_cause: str
    severity: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class Warning(ReelLabModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class SimulationResult(ReelLabModel):
    simulation_id: str
    status: SimulationStatus = "completed"
    reel_id: str | None = None
    variant_id: str | None = None
    graph_id: str | None = None
    overall_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    audience_results: list[PersonaSimulationResult] = Field(default_factory=list)
    propagation_waves: list[PropagationWave] = Field(default_factory=list)
    audience_segment_results: list[AudienceSegmentResult] = Field(default_factory=list)
    bottlenecks: list[Bottleneck] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    created_at: str
    completed_at: str | None = None
    metadata: RunMetadata | None = None
