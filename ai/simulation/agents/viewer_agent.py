"""The viewer agent — one persona watching one reel.

    simulate_persona(persona, content) -> (PersonaSimulationResult, mock)

This is the centre of the product. Everything else exists to set this call up or
to aggregate its output.

The model is asked to *be* the persona and narrate the decision, not to score
the video. That distinction is the difference between a real simulation and a
rubric: "rate this reel 0-10 for a college student" produces a number with
nothing behind it, while "you are Karan, you are scrolling, here is what
appears" produces a reason we can show the creator and argue with.

Probabilities coming back from the model are checked for *coherence*, not just
range. A viewer cannot complete a video they never watched, and cannot share one
they swiped past in two seconds. Those clamps are deterministic on purpose —
they are arithmetic, not judgement.

OWNER: Developer 1.
"""

from __future__ import annotations

from pydantic import Field

from errors import MalformedModelOutputError
from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from personas.profiles.profiles import brief_for
from schemas import ContentDNA, Persona, PersonaSimulationResult
from schemas.base import ReelLabModel

import fixtures

logger = get_logger("simulation.agents")

PROMPT_VERSION = "viewer-agent-v1"


class _ViewerReaction(ReelLabModel):
    """What the model returns for one persona. Bounds enforced by Pydantic."""

    watch_probability: float = Field(ge=0.0, le=1.0)
    completion_probability: float = Field(ge=0.0, le=1.0)
    like_probability: float = Field(ge=0.0, le=1.0)
    save_probability: float = Field(ge=0.0, le=1.0)
    share_probability: float = Field(ge=0.0, le=1.0)
    comment_probability: float = Field(ge=0.0, le=1.0)
    swipe_time: float | None = Field(
        default=None,
        ge=0.0,
        description="Second at which you swiped away. null if you watched to the end.",
    )
    action: str = Field(
        description="One of: swipe, watch, complete, like, save, share, comment.",
    )
    reason: str = Field(
        description="First person, one short paragraph. Names the specific thing "
        "that made you stay or leave.",
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="How sure you are this is really what you would do."
    )


VALID_ACTIONS = {"swipe", "watch", "complete", "like", "save", "share", "comment"}


def describe_content(content: ContentDNA) -> str:
    """Render Content DNA as what a viewer would actually experience.

    Chronological rather than a feature dump. The persona has to decide *as the
    reel plays*; handing the model a bullet list of aggregate features invites it
    to review the video from the outside instead of watching it.
    """
    scenes = "\n".join(
        f"  {scene.start_seconds:.1f}-{scene.end_seconds:.1f}s: {scene.description}"
        for scene in content.scenes
    ) or "  (no scene breakdown available)"

    captions = "yes" if content.visual_features.has_on_screen_text else "no"
    cta = content.cta.text if content.cta.present else "none"
    transcript = content.transcript.strip() or "(no speech detected)"

    return f"""A {content.duration_seconds:.0f}-second vertical video.

The first thing you see and hear ({content.hook.duration_seconds:.1f}s):
  "{content.hook.text}"

What happens next:
{scenes}

What is said: {transcript[:1200]}

Tone: {content.tone}. Emotional register: {content.emotion}.
On-screen text: {captions}. Cuts per second: {content.visual_features.cuts_per_second:.2f}.
Speaking pace: {content.audio_features.words_per_minute:.0f} words per minute.
Call to action: {cta}"""


def build_prompt(persona: Persona, content: ContentDNA) -> str:
    return f"""{brief_for(persona)}

You are scrolling. This appears:

{describe_content(content)}

Work through it the way you actually would, in order:

1. It starts playing. Does anything hold you in the first second or two?
2. The hook — is it about something you care about? Do you even understand what
   it is offering?
3. If you are still here, are you interested enough to keep going?
4. Do you reach the end, or does something lose you partway?
5. If you finish it: does it earn a like, a save, a share, or a comment? These
   are different impulses. You save what is useful to *you*. You share what says
   something about *you* to other people. Most videos earn none of them.

Then answer as yourself:
- watchProbability: you get past the opening and keep watching.
- completionProbability: you reach the end. This cannot exceed watchProbability.
- like / save / share / commentProbability: each 0-1, judged separately.
- swipeTime: the second you swiped away, or null if you watched to the end.
- action: your single most notable outcome — one of swipe, watch, complete,
  like, save, share, comment.
- reason: one short first-person paragraph naming the *specific* thing that made
  you stay or leave. "It was boring" is useless. "He spent four seconds saying
  nothing and I still didn't know what the video was about" is useful. This is
  shown to the creator.
- confidence: how sure you are this is really what you would do. If this content
  is outside anything you have an opinion about, say so with a low number.

Be honest rather than generous. You are one person scrolling, not a focus
group, and most videos do not get engagement from you."""


def _coerce(reaction: _ViewerReaction, persona: Persona, content: ContentDNA) -> PersonaSimulationResult:
    """Repair coherence problems the schema bounds cannot catch.

    Range validation is Pydantic's job. This handles the *relationships*: you
    cannot finish what you did not start, you cannot engage with what you swiped
    past, and you cannot swipe at second 40 of a 34-second video.
    """
    watch = reaction.watch_probability
    completion = min(reaction.completion_probability, watch)

    # Engagement is conditional on having watched. Without this a model can hand
    # back "swiped at 2.6s" alongside a 0.5 share probability, which then feeds
    # a propagation cascade that never should have started.
    ceiling = watch
    like = min(reaction.like_probability, ceiling)
    save = min(reaction.save_probability, ceiling)
    share = min(reaction.share_probability, ceiling)
    comment = min(reaction.comment_probability, ceiling)

    action = reaction.action.strip().lower()
    if action not in VALID_ACTIONS:
        action = "swipe" if watch < 0.5 else "watch"

    swipe_time = reaction.swipe_time
    if action in {"complete", "like", "save", "share", "comment"}:
        # These outcomes imply they stayed.
        swipe_time = None
    elif swipe_time is not None:
        swipe_time = max(0.0, min(swipe_time, content.duration_seconds))

    return PersonaSimulationResult(
        persona_id=persona.id,
        persona_name=persona.name,
        demographic_summary=persona.demographic_summary,
        watch_probability=watch,
        completion_probability=completion,
        like_probability=like,
        save_probability=save,
        share_probability=share,
        comment_probability=comment,
        swipe_time=swipe_time,
        action=action,  # type: ignore[arg-type]
        reason=reaction.reason.strip(),
        confidence=reaction.confidence,
    )


async def _simulate_with_model(persona: Persona, content: ContentDNA) -> PersonaSimulationResult:
    reaction, metadata = await llm.complete_model(
        _ViewerReaction,
        prompt=build_prompt(persona, content),
        prompt_version=PROMPT_VERSION,
        tier="reasoning",
        max_tokens=900,
    )

    if not reaction.reason.strip():
        raise MalformedModelOutputError(
            "Viewer agent returned an empty reason.",
            details={"personaId": persona.id},
        )

    log_event(
        logger,
        "viewer_agent_call",
        persona_id=persona.id,
        model=metadata.model,
        latency_ms=metadata.latency_ms,
        estimated_cost_usd=metadata.estimated_cost_usd,
    )
    return _coerce(reaction, persona, content)


def _fixture_result(persona: Persona) -> PersonaSimulationResult:
    """Reuse the fixture reaction for this persona, or the first one available."""
    results = fixtures.simulation_result().audience_results
    for candidate in results:
        if candidate.persona_id == persona.id:
            return candidate
    return results[0].model_copy(update={"persona_id": persona.id})


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
    silently shrinking the sample and reporting the same confidence.
    """
    return PersonaSimulationResult(
        persona_id=persona.id,
        persona_name=persona.name,
        demographic_summary=persona.demographic_summary,
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
        error=error[:300],
    )
