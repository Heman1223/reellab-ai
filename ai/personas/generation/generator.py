"""Persona generation.

    generate_personas(segment, count) -> list[Persona]

A persona is a synthetic viewer specific enough to make a *different* decision
than the persona next to it. Five personas that all say "nice video" are five
wasted model calls — the variance between them is the entire signal.

Personas are the expensive artefact in this system (one model call each) and are
worth caching per segment. `backend/src/models/Persona.ts` exists for that.

OWNER: Developer 1.
"""

from __future__ import annotations

from config import settings
from errors import PersonaGenerationError
from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from schemas import AudienceSegment, Persona

import fixtures

logger = get_logger("personas.generation")

PROMPT_VERSION = "persona-generation-v0"


def _build_prompt(segment: AudienceSegment, count: int, creator_goal: str | None) -> str:
    return f"""Generate {count} distinct synthetic viewers from this audience segment.

Segment: {segment.name}
Description: {segment.description}
Characteristics: {", ".join(segment.characteristics) or "none given"}
Creator goal: {creator_goal or "not stated"}

Each persona must be specific enough to make a different scrolling decision from
the others. Vary attention span, what makes them swipe, and what makes them
share rather than merely like.

For each persona provide: name, a one-line demographic sketch, interests,
behavioural traits, an attention profile (average attention in seconds, swipe
tendency 0-1, concrete drop-off triggers), an engagement profile (like / save /
share / comment tendencies 0-1), content preferences, and a short second-person
`systemBrief` that will be used as this persona's voice during simulation.

Return JSON matching a list of the Persona schema."""


async def _generate_with_model(
    segment: AudienceSegment, count: int, creator_goal: str | None
) -> list[Persona]:
    result = await llm.complete_json(
        prompt=_build_prompt(segment, count, creator_goal),
        prompt_version=PROMPT_VERSION,
        tier="reasoning",
    )

    raw = result.data
    if not isinstance(raw, list):
        raise PersonaGenerationError("Model did not return a list of personas.")

    return [Persona.model_validate(item) for item in raw]


async def generate_personas(
    segment: AudienceSegment,
    count: int = 3,
    creator_goal: str | None = None,
) -> tuple[list[Persona], bool]:
    """Generate personas for one segment. Returns `(personas, mock)`."""
    # Hard ceiling: persona count is the main driver of what a run costs.
    count = max(1, min(count, settings.max_personas))

    personas, mock = await with_fixture_fallback(
        "personas.generate",
        lambda: _generate_with_model(segment, count, creator_goal),
        lambda: fixtures.personas_for_segment(segment.id, count),
    )

    log_event(
        logger,
        "personas_generated",
        segment_id=segment.id,
        requested=count,
        produced=len(personas),
        mock=mock,
    )
    return personas, mock
