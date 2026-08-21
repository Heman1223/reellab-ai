"""Pydantic mirror of `shared/schemas/audience.ts`.

Keep the two field-for-field compatible. If you change one, change the other in
the same pull request.
"""

from __future__ import annotations

from pydantic import Field

from .base import ReelLabModel


class AudienceRequest(ReelLabModel):
    niche: str
    target_audience: str
    secondary_audience: str | None = None
    location: str
    language: str
    creator_goal: str


class AudienceSegment(ReelLabModel):
    id: str
    name: str
    description: str
    parent_segment: str | None = None
    characteristics: list[str] = Field(default_factory=list)
    relevance_score: float = Field(ge=0.0, le=1.0)
    estimated_share: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str | None = None


class SegmentAdjacency(ReelLabModel):
    from_segment_id: str
    to_segment_id: str
    spillover_probability: float = Field(ge=0.0, le=1.0)


class AudienceGraph(ReelLabModel):
    graph_id: str
    request: AudienceRequest
    segments: list[AudienceSegment]
    adjacency: list[SegmentAdjacency] = Field(default_factory=list)
