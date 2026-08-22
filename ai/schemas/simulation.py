"""Pydantic mirror of `shared/schemas/simulation.ts`."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ReelLabModel
from .content import ContentDNA

ViewerAction = Literal["swipe", "watch", "complete", "like", "save", "share", "comment"]

SimulationStatus = Literal[
    "queued",
    "analyzing_content",
    "simulating_personas",
    "propagating",
    "reflecting",
    "completed",
    "failed",
    "partial",
]

SimulationDepth = Literal["quick", "standard", "deep"]


class SimulationRequest(ReelLabModel):
    simulation_id: str | None = None
    reel_id: str | None = None
    content_dna: ContentDNA | None = None
    graph_id: str | None = None
    persona_ids: list[str] = Field(default_factory=list)
    depth: SimulationDepth = "standard"
    personas_per_segment: int | None = None
    variant_id: str | None = None


class PersonaSimulationResult(ReelLabModel):
    """One synthetic viewer's reaction.

    The probabilities are independent estimates and do not form a distribution;
    `action` is the single sampled outcome. `reason` is the model's first-person
    justification and is shown to the creator verbatim — it is the part of the
    output that makes the simulation inspectable rather than a black box.
    """

    persona_id: str
    persona_name: str
    demographic_summary: str
    watch_probability: float = Field(ge=0.0, le=1.0)
    completion_probability: float = Field(ge=0.0, le=1.0)
    like_probability: float = Field(ge=0.0, le=1.0)
    save_probability: float = Field(ge=0.0, le=1.0)
    share_probability: float = Field(ge=0.0, le=1.0)
    comment_probability: float = Field(ge=0.0, le=1.0)
    swipe_time: float | None = None
    action: ViewerAction
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    error: str | None = None


class PropagationWave(ReelLabModel):
    wave: int = Field(ge=0)
    segment_ids: list[str] = Field(default_factory=list)
    reach: float = Field(ge=0.0)
    pass_through_rate: float = Field(ge=0.0, le=1.0)
    terminated: bool = False
    note: str | None = None


class RunMetadata(ReelLabModel):
    """Observability envelope attached to anything an AI produced."""

    model: str
    model_version: str | None = None
    prompt_version: str | None = None
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    persona_count: int | None = None
    simulation_duration_ms: float | None = None
    mock: bool = False
