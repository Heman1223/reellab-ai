"""Pydantic mirror of `shared/schemas/content.ts`."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import ReelLabModel


class Scene(ReelLabModel):
    index: int
    start_seconds: float
    end_seconds: float
    description: str
    shot_type: str | None = None
    energy: float | None = Field(default=None, ge=0.0, le=1.0)


class VisualFeatures(ReelLabModel):
    cuts_per_second: float = Field(ge=0.0)
    has_on_screen_text: bool
    face_presence: float = Field(ge=0.0, le=1.0)
    dominant_colors: list[str] = Field(default_factory=list)
    production_quality: float | None = Field(default=None, ge=0.0, le=1.0)


class AudioFeatures(ReelLabModel):
    has_speech: bool
    has_music: bool
    words_per_minute: float = Field(ge=0.0)
    energy: float = Field(ge=0.0, le=1.0)
    language: str | None = None


class Hook(ReelLabModel):
    text: str
    duration_seconds: float = Field(ge=0.0)
    type: str
    strength: float = Field(ge=0.0, le=1.0)


class CallToAction(ReelLabModel):
    present: bool
    text: str | None = None
    at_second: float | None = None
    type: Literal["follow", "comment", "share", "save", "link", "other"] | None = None


class ContentDNA(ReelLabModel):
    """The multimodal understanding of one reel.

    This is the hand-off between Developer 2 (produces it) and Developer 1
    (simulates against it).
    """

    video_id: str
    duration_seconds: float = Field(ge=0.0)
    transcript: str
    topic: str
    hook: Hook
    tone: str
    emotion: str
    scenes: list[Scene] = Field(default_factory=list)
    visual_features: VisualFeatures
    audio_features: AudioFeatures
    cta: CallToAction
    warnings: list[str] = Field(default_factory=list)


class VideoAnalysisRequest(ReelLabModel):
    """Either a path on disk or a fetchable URL — never the bytes themselves."""

    video_path: str | None = None
    video_url: str | None = None
    video_id: str | None = None
