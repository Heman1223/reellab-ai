"""Persona generation.

    generate_personas(segment, count) -> (list[Persona], mock)

A persona is a synthetic viewer specific enough to make a *different* decision
than the persona next to it. Five personas that all say "nice video" are five
wasted model calls — the variance between them is the entire signal.

The prompt therefore optimises for behavioural spread, not demographic realism.
Two people with identical demographics who scroll differently are two useful
personas; two people with different ages who behave identically are one.

Personas are the second-largest cost in a run after simulation itself, and they
are stable for a given segment, so `PersonaCache` sits in front of generation.

OWNER: Developer 1.
"""

from __future__ import annotations

from pydantic import Field

from config import settings
from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from schemas import AudienceSegment, Persona
from schemas.base import ReelLabModel

import fixtures

from ..profiles.profiles import (
    behavioural_spread,
    cache_key,
    persona_cache,
    slug_id,
)

logger = get_logger("personas.generation")

PROMPT_VERSION = "persona-generation-v1"

#: Below this, the personas are near-duplicates and the simulation will produce
#: an artificially confident, artificially uniform result. Warn rather than fail:
#: a genuinely homogeneous segment is a legitimate finding.
MIN_SPREAD = 0.08


class _ProposedPersona(ReelLabModel):
    """A persona as the model proposes it, before we assign an id."""

    name: str
    demographic_summary: str = Field(description="One line: age, gender, place, situation.")
    interests: list[str] = Field(default_factory=list)
    behavioral_traits: list[str] = Field(
        default_factory=list,
        description="How they actually scroll, judge and engage.",
    )
    attention_profile: dict = Field(
        description=(
            "averageAttentionSeconds (number), swipeTendency (0-1), "
            "dropOffTriggers (list of concrete strings)."
        )
    )
    engagement_profile: dict = Field(
        description=(
            "likeTendency, saveTendency, shareTendency, commentTendency, "
            "followTendency — each 0-1."
        )
    )
    content_preferences: dict = Field(
        description=(
            "preferredFormats, preferredTones (lists), preferredDurationSeconds "
            "({min, max}), turnOffs (list)."
        )
    )
    system_brief: str = Field(
        description="Second-person brief used as this persona's voice during simulation."
    )


class _ProposedPersonas(ReelLabModel):
    personas: list[_ProposedPersona]


def build_prompt(segment: AudienceSegment, count: int, creator_goal: str | None) -> str:
    return f"""Generate {count} distinct synthetic viewers from this audience segment.

Segment: {segment.name}
Description: {segment.description}
Characteristics: {", ".join(segment.characteristics) or "none given"}
Creator goal: {creator_goal or "not stated"}

These personas exist to be simulated watching short-form videos. What matters is
that they make *different decisions* from each other, not that they are
demographically representative. Two viewers with the same age who scroll
differently are useful; two with different ages who behave identically are one
persona wearing two names.

Vary them along the axes that actually change a scrolling decision:
- how long they give a video before swiping (seconds, and be honest — for some
  audiences this is under three)
- what specifically makes them leave
- knowledge level, and whether they are curious or sceptical about claims
- whether their instinct is to save (useful to me) or to share (says something
  about me) — these are different impulses and most people lean to one
- when and how they watch: muted at work, at night after the gym, with friends

For each persona provide:
- name, demographicSummary (one line)
- interests, behavioralTraits
- attentionProfile: averageAttentionSeconds, swipeTendency (0-1),
  dropOffTriggers (concrete: "no captions", not "boring content")
- engagementProfile: likeTendency, saveTendency, shareTendency, commentTendency,
  followTendency — all 0-1. Be realistic: most short-form videos get none of
  these from most viewers, so most of these numbers should be low.
- contentPreferences: preferredFormats, preferredTones,
  preferredDurationSeconds {{min, max}}, turnOffs
- systemBrief: a short second-person brief ("You are ... You decide in about ...
  seconds. You leave when ...") used verbatim as this persona's voice when they
  watch a reel. Make it specific enough that it would produce a different
  reaction than the other personas in this batch.

Ground every persona in the segment above. Do not produce a generic viewer."""


async def _generate_with_model(
    segment: AudienceSegment, count: int, creator_goal: str | None
) -> list[Persona]:
    proposal, metadata = await llm.complete_model(
        _ProposedPersonas,
        prompt=build_prompt(segment, count, creator_goal),
        prompt_version=PROMPT_VERSION,
        tier="reasoning",
        max_tokens=1024 * max(2, count),
    )

    personas: list[Persona] = []
    for index, proposed in enumerate(proposal.personas[:count]):
        try:
            personas.append(
                Persona.model_validate(
                    {
                        **proposed.model_dump(by_alias=True),
                        "id": slug_id(segment.id, proposed.name, index),
                        "segmentId": segment.id,
                    }
                )
            )
        except Exception as exc:  # noqa: BLE001 — one bad persona is not a failed batch
            log_event(
                logger,
                "persona_discarded",
                segment_id=segment.id,
                name=proposed.name,
                error=str(exc)[:200],
            )

    if not personas:
        from errors import PersonaGenerationError

        raise PersonaGenerationError(
            f"No valid personas produced for segment '{segment.id}'.",
            details={"proposed": len(proposal.personas)},
        )

    log_event(
        logger,
        "persona_model_call",
        segment_id=segment.id,
        model=metadata.model,
        latency_ms=metadata.latency_ms,
        estimated_cost_usd=metadata.estimated_cost_usd,
    )
    return personas


def _fixture_personas(segment: AudienceSegment, count: int) -> list[Persona]:
    return fixtures.personas_for_segment(segment.id, count)


async def generate_personas(
    segment: AudienceSegment,
    count: int = 3,
    creator_goal: str | None = None,
    *,
    use_cache: bool = True,
) -> tuple[list[Persona], bool]:
    """Generate personas for one segment. Returns `(personas, mock)`.

    `count` is clamped to `AI_MAX_PERSONAS` — persona count is the main driver of
    what a run costs, so the ceiling is enforced here rather than trusted to
    callers.
    """
    count = max(1, min(count, settings.max_personas))
    key = cache_key(segment.id, count, PROMPT_VERSION)

    if use_cache:
        cached = persona_cache.get(key)
        if cached is not None:
            log_event(logger, "personas_cache_hit", segment_id=segment.id, count=len(cached))
            return cached, False

    personas, mock = await with_fixture_fallback(
        "personas.generate",
        lambda: _generate_with_model(segment, count, creator_goal),
        lambda: _fixture_personas(segment, count),
    )

    spread = behavioural_spread(personas)
    if spread < MIN_SPREAD and len(personas) > 1:
        log_event(
            logger,
            "personas_low_diversity",
            segment_id=segment.id,
            spread=spread,
            note="Personas behave near-identically; simulation confidence will be inflated.",
        )

    if use_cache and not mock:
        persona_cache.put(key, personas)

    log_event(
        logger,
        "personas_generated",
        segment_id=segment.id,
        requested=count,
        produced=len(personas),
        spread=spread,
        mock=mock,
    )
    return personas, mock
