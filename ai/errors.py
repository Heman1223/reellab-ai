"""Failure modes of the AI service.

The brief lists the failures this system has to survive: empty transcripts,
unsupported video, model timeouts, malformed model output, persona generation
failures, partial simulations. Each gets a type here so callers can decide what
to do rather than pattern-matching on message strings.
"""

from __future__ import annotations


class ReelLabAIError(Exception):
    """Base class. Carries a stable machine-readable `code`."""

    code = "AI_ERROR"
    http_status = 500

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict:
        return {"code": self.code, "message": self.message, "details": self.details}


class AINotConfiguredError(ReelLabAIError):
    """No provider or API key configured — fall back to a fixture."""

    code = "AI_NOT_CONFIGURED"
    http_status = 503


class ModelTimeoutError(ReelLabAIError):
    code = "AI_TIMEOUT"
    http_status = 504


class MalformedModelOutputError(ReelLabAIError):
    """The model returned something that did not validate against our schema.

    Expected often enough to be routine. Retry once with a repair prompt before
    surfacing it.
    """

    code = "AI_MALFORMED_OUTPUT"
    http_status = 502


class UnsupportedVideoError(ReelLabAIError):
    code = "UNSUPPORTED_VIDEO"
    http_status = 415


class EmptyTranscriptError(ReelLabAIError):
    """No speech detected. Not fatal — visual-only reels are legitimate."""

    code = "EMPTY_TRANSCRIPT"
    http_status = 422


class PersonaGenerationError(ReelLabAIError):
    code = "PERSONA_GENERATION_FAILED"
    http_status = 502


class PartialSimulationError(ReelLabAIError):
    """Some personas failed. The run is still usable and must be returned."""

    code = "SIMULATION_PARTIAL"
    http_status = 207
