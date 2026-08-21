"""Pydantic mirror of `shared/schemas/persona.ts`."""

from __future__ import annotations

from pydantic import Field

from .audience import AudienceSegment
from .base import ReelLabModel


class AttentionProfile(ReelLabModel):
    average_attention_seconds: float = Field(ge=0.0)
    swipe_tendency: float = Field(ge=0.0, le=1.0)
    drop_off_triggers: list[str] = Field(default_factory=list)


class EngagementProfile(ReelLabModel):
    like_tendency: float = Field(ge=0.0, le=1.0)
    save_tendency: float = Field(ge=0.0, le=1.0)
    share_tendency: float = Field(ge=0.0, le=1.0)
    comment_tendency: float = Field(ge=0.0, le=1.0)
    follow_tendency: float | None = Field(default=None, ge=0.0, le=1.0)


class DurationRange(ReelLabModel):
    min: float
    max: float


class ContentPreferences(ReelLabModel):
    preferred_formats: list[str] = Field(default_factory=list)
    preferred_tones: list[str] = Field(default_factory=list)
    preferred_duration_seconds: DurationRange
    turn_offs: list[str] = Field(default_factory=list)


class Persona(ReelLabModel):
    id: str
    segment_id: str
    name: str
    demographic_summary: str
    interests: list[str] = Field(default_factory=list)
    behavioral_traits: list[str] = Field(default_factory=list)
    attention_profile: AttentionProfile
    engagement_profile: EngagementProfile
    content_preferences: ContentPreferences
    system_brief: str | None = None


class PersonaGenerationRequest(ReelLabModel):
    segment: AudienceSegment
    count: int = Field(default=3, ge=1, le=25)
    creator_goal: str | None = None
