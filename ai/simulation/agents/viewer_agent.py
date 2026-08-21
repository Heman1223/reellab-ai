"""The viewer agent — one persona watching one reel.

    simulate_persona(persona, content) -> PersonaSimulationResult

This is the centre of the product. Everything else exists to set this call up or
to aggregate its output.

The model is asked to *be* the persona and narrate the decision, not to score
the video. That distinction matters: "rate this reel 0-10 for a college student"
produces a number with nothing behind it, while "you are Karan, you're
scrolling, here is what you see" produces a reason we can show the creator and
argue with.

OWNER: Developer 1.
"""

from __future__ import annotations

from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from personas.profiles.profiles import brief_for
from schemas import ContentDNA, Persona, PersonaSimulationResult

import fixtures

logger = get_logger("simulation.agents")

PROMPT_VERSION = "viewer-agent-v0"


def _describe_content(content: ContentDNA) -> str:
    """Render Content DNA as what a viewer would actually experience.

    Deliberately chronological rather than a feature dump — the persona has to
    decide *as the reel plays*, and a bullet list of aggregate features invites
    the model to judge the video from the outside instead.
    """
    scenes = "\n".join(
        f"  {scene.start_seconds:.1f}-{scene.end_seconds:.1f}s: {scene.description}"
        for scene in content.scenes
    ) or "  (no scene breakdown available)"

    captions = "yes" if content.visual_features.has_on_screen_text else "no"
    cta = content.cta.text if content.cta.present else "none"

    return f"""A {content.duration_seconds:.0f}-second vertical video.

First thing you see and hear ({content.hook.duration_seconds:.1f}s):
  "{content.hook.text}"

What happens:
{scenes}

Tone: {content.tone}. Emotional register: {content.emotion}.
On-screen text: {captions}. Cuts per second: {content.visual_features.cuts_per_second:.2f}.
Speaking pace: {content.audio_features.words_per_minute:.0f} words per minute.
Call to action: {cta}"""


def _build_prompt(persona: Persona, content: ContentDNA) -> str:
    return f"""{brief_for(persona)}

You are scrolling. This appears:

{_describe_content(content)}

Decide as yourself, in the moment — not as a critic evaluating the video.

Answer:
- Do you keep watching past the first few seconds, and if you swipe, at what
  second?
- Do you reach the end?
- Do you like, save, share, or comment? Be honest: most videos get none of these.
  Saving and sharing are different impulses — you save what is useful to you and
  share what says something about you.
- Why. One short first-person paragraph. This is shown to the creator, so it
  must name the specific thing that made you stay or leave.
- How confident you are that this is really what you would do (0-1).

Return JSON matching the PersonaSimulationResult schema."""


async def _simulate_with_model(
    persona: Persona, content: ContentDNA
) -> PersonaSimulationResult:
    result = await llm.complete_json(
        prompt=_build_prompt(persona, content),
        prompt_version=PROMPT_VERSION,
        tier="reasoning",
        max_tokens=1024,
    )
    parsed = PersonaSimulationResult.model_validate(result.data)
    return parsed.model_copy(update={"persona_id": persona.id})


def _fixture_result(persona: Persona) -> PersonaSimulationResult:
    """Reuse the fixture reaction for this persona, or the first one available."""
    results = fixtures.simulation_result().audience_results
    for candidate in results:
        if candidate.persona_id == persona.id:
            return candidate

    fallback = results[0]
    return fallback.model_copy(update={"persona_id": persona.id})


async def simulate_persona(
    persona: Persona, content: ContentDNA
) -> tuple[PersonaSimulationResult, bool]:
    """Simulate one persona watching one reel. Returns `(result, mock)`."""
    result, mock = await with_fixture_fallback(
        "simulation.persona",
        lambda: _simulate_with_model(persona, content),
        lambda: _fixture_result(persona),
    )

    log_event(
        logger,
        "persona_simulated",
        persona_id=persona.id,
        action=result.action,
        confidence=result.confidence,
        mock=mock,
    )
    return result, mock


def failed_result(persona: Persona, error: str) -> PersonaSimulationResult:
    """A neutral, zero-confidence result for a persona whose call failed.

    One failed persona must never take down a run. This keeps the persona in the
    output, flagged, so the aggregate can exclude it honestly rather than
    silently shrinking the sample.
    """
    return PersonaSimulationResult(
        persona_id=persona.id,
        watch_probability=0.0,
        completion_probability=0.0,
        like_probability=0.0,
        save_probability=0.0,
        share_probability=0.0,
        comment_probability=0.0,
        swipe_time=None,
        action="swipe",
        reason="This persona could not be simulated; excluded from the aggregate.",
        confidence=0.0,
        error=error,
    )
