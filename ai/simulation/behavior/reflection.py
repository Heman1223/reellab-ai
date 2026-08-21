"""Bottleneck analysis — why the reel failed where it failed.

    analyze_bottlenecks(content, persona_results, segment_results, waves) -> list[Bottleneck]

The numbers say *where* the reel loses people. This step says *why*, and the why
is what the creator can act on. "Segment X scores 0.24" is not a product; "four
of five viewers left before the first point because the opening states a
category rather than a stake" is.

The model reads the personas' own stated reasons and finds the pattern across
them. That is a genuinely hard reasoning task and the reason this step cannot be
a rule table.

OWNER: Developer 1.
"""

from __future__ import annotations

from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from schemas import (
    AudienceSegmentResult,
    Bottleneck,
    ContentDNA,
    PersonaSimulationResult,
    PropagationWave,
)

import fixtures

logger = get_logger("simulation.reflection")

PROMPT_VERSION = "bottleneck-analysis-v0"


def _build_prompt(
    content: ContentDNA,
    persona_results: list[PersonaSimulationResult],
    segment_results: list[AudienceSegmentResult],
    waves: list[PropagationWave],
) -> str:
    reactions = "\n".join(
        f"- {result.persona_id}: {result.action}"
        + (f" at {result.swipe_time:.1f}s" if result.swipe_time is not None else "")
        + f' — "{result.reason}"'
        for result in persona_results
    )

    segments = "\n".join(
        f"- {result.segment_name}: score {result.score:.2f} ({result.verdict}), "
        f"{result.persona_count} personas, share rate {result.share_rate:.2f}"
        for result in segment_results
    )

    cascade = "\n".join(
        f"- wave {wave.wave}: reach {wave.reach:.0f}, "
        f"pass-through {wave.pass_through_rate:.2f}"
        + (" (terminated)" if wave.terminated else "")
        for wave in waves
    )

    return f"""A reel was simulated against a synthetic audience. Explain why it
performed the way it did.

The reel opens with: "{content.hook.text}" ({content.hook.duration_seconds:.1f}s)
Duration: {content.duration_seconds:.0f}s. Tone: {content.tone}.

What each synthetic viewer did and said:
{reactions}

Segment results:
{segments}

Propagation:
{cascade}

Find the bottlenecks — the specific points where this reel loses people. For
each one give: the funnel stage (hook, retention, payoff, cta, or propagation),
which segments it affects, what breaks, and the most likely *cause*.

The cause is the part that matters. Ground it in what the viewers actually said,
not in general short-form advice. If the evidence is thin, say so through a low
confidence score rather than by hedging the wording.

Return JSON matching a list of the Bottleneck schema."""


async def _analyze_with_model(
    content: ContentDNA,
    persona_results: list[PersonaSimulationResult],
    segment_results: list[AudienceSegmentResult],
    waves: list[PropagationWave],
) -> list[Bottleneck]:
    result = await llm.complete_json(
        prompt=_build_prompt(content, persona_results, segment_results, waves),
        prompt_version=PROMPT_VERSION,
        tier="reasoning",
    )
    raw = result.data if isinstance(result.data, list) else []
    return [Bottleneck.model_validate(item) for item in raw]


async def analyze_bottlenecks(
    content: ContentDNA,
    persona_results: list[PersonaSimulationResult],
    segment_results: list[AudienceSegmentResult],
    waves: list[PropagationWave],
) -> tuple[list[Bottleneck], bool]:
    """Explain the failure. Returns `(bottlenecks, mock)`."""
    bottlenecks, mock = await with_fixture_fallback(
        "simulation.reflect",
        lambda: _analyze_with_model(content, persona_results, segment_results, waves),
        lambda: fixtures.simulation_result().bottlenecks,
    )

    log_event(logger, "bottlenecks_identified", count=len(bottlenecks), mock=mock)
    return bottlenecks, mock
