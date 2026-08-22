"""Bottleneck analysis — where the reel fails, and why.

    analyze_bottlenecks(content, persona_results, segment_results, waves, ...) -> (list[Bottleneck], mock)

Two steps with a deliberate split:

1. **Detection is deterministic.** `detect_signals` finds *where* the funnel
   breaks by measuring the simulation output — how many personas left before the
   hook ended, how wide the watch-to-completion gap is, whether the cascade
   died. Severity comes from those measurements. This is arithmetic and it is
   reproducible.

2. **Explanation is AI.** The model reads the personas' own stated reasons and
   works out *why* the pattern exists. That is the part the creator acts on, and
   it is genuinely hard reasoning — finding the common thread across fifteen
   first-person accounts is not something a rule table can do.

When the model is unavailable, the fallback reports the measurement and says
plainly that the cause was not analysed. It does **not** invent a plausible
explanation from a template — a fabricated cause is worse than an admitted gap,
because the creator would act on it.

OWNER: Developer 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean

from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from schemas import (
    AudienceSegmentResult,
    Bottleneck,
    ContentDNA,
    PersonaSimulationResult,
    PropagationWave,
)
from schemas.base import ReelLabModel

logger = get_logger("simulation.reflection")

PROMPT_VERSION = "bottleneck-analysis-v1"

#: Short-form viewers decide inside roughly this window.
DECISION_WINDOW_SECONDS = 3.0

#: Detection thresholds. Each one is a measurement, not a judgement — the
#: judgement is what the model adds on top.
HOOK_LOSS_FRACTION = 0.4       # share of personas gone before the hook ends
RETENTION_GAP = 0.25           # watch minus completion
PAYOFF_WATCH_FLOOR = 0.55      # they stayed...
PAYOFF_COMPLETION_CEILING = 0.3  # ...but did not finish
CTA_ENGAGEMENT_CEILING = 0.12  # they finished but did nothing
PROPAGATION_SHARE_CEILING = 0.1
WEAK_SEGMENT_SCORE = 0.35


@dataclass
class BottleneckSignal:
    """A measured failure point, before any model has explained it."""

    id: str
    stage: str
    segment_ids: list[str]
    description: str
    severity: float
    evidence: list[str] = field(default_factory=list)


def _quotes(results: list[PersonaSimulationResult], limit: int = 6) -> list[str]:
    """Persona reasons, shortest first — the terse ones are usually the sharpest."""
    reasons = [r.reason.strip() for r in results if r.error is None and r.reason.strip()]
    return sorted(reasons, key=len)[:limit]


def detect_signals(
    content: ContentDNA | None,
    persona_results: list[PersonaSimulationResult],
    segment_results: list[AudienceSegmentResult],
    waves: list[PropagationWave] | None = None,
) -> list[BottleneckSignal]:
    """Measure where the funnel breaks. Pure function over simulation output."""
    succeeded = [r for r in persona_results if r.error is None]
    if not succeeded:
        return []

    signals: list[BottleneckSignal] = []
    hook_end = content.hook.duration_seconds if content else DECISION_WINDOW_SECONDS
    cutoff = max(DECISION_WINDOW_SECONDS, hook_end)

    # --- hook -------------------------------------------------------------
    early_leavers = [
        r for r in succeeded if r.swipe_time is not None and r.swipe_time <= cutoff
    ]
    early_fraction = len(early_leavers) / len(succeeded)
    if early_fraction >= HOOK_LOSS_FRACTION:
        affected = _segments_for(early_leavers, persona_results, segment_results)
        signals.append(
            BottleneckSignal(
                id="bn_hook",
                stage="hook",
                segment_ids=affected,
                description=(
                    f"{len(early_leavers)} of {len(succeeded)} personas left within "
                    f"{cutoff:.1f}s — before the hook finished."
                ),
                severity=round(max(0.0, min(1.0, early_fraction * 1.2)), 4),
                evidence=_quotes(early_leavers),
            )
        )

    # --- retention --------------------------------------------------------
    for segment in segment_results:
        if segment.persona_count == 0:
            continue
        gap = segment.average_watch_probability - segment.average_completion_probability
        if gap >= RETENTION_GAP:
            signals.append(
                BottleneckSignal(
                    id=f"bn_retention_{segment.segment_id}",
                    stage="retention",
                    segment_ids=[segment.segment_id],
                    description=(
                        f"{segment.segment_name}: {segment.average_watch_probability:.0%} start "
                        f"watching but only {segment.average_completion_probability:.0%} finish."
                    ),
                    severity=round(max(0.0, min(1.0, gap * 2)), 4),
                )
            )

    # --- payoff -----------------------------------------------------------
    mean_watch = mean(r.watch_probability for r in succeeded)
    mean_completion = mean(r.completion_probability for r in succeeded)
    if mean_watch >= PAYOFF_WATCH_FLOOR and mean_completion <= PAYOFF_COMPLETION_CEILING:
        signals.append(
            BottleneckSignal(
                id="bn_payoff",
                stage="payoff",
                segment_ids=[],
                description=(
                    f"Personas stay ({mean_watch:.0%} watch) but do not finish "
                    f"({mean_completion:.0%} complete). The middle does not pay off."
                ),
                severity=round(max(0.0, min(1.0, (mean_watch - mean_completion) * 1.5)), 4),
                evidence=_quotes(succeeded),
            )
        )

    # --- cta --------------------------------------------------------------
    finishers = [r for r in succeeded if r.completion_probability >= 0.4]
    if finishers:
        engagement = mean(
            max(r.like_probability, r.save_probability, r.share_probability, r.comment_probability)
            for r in finishers
        )
        if engagement <= CTA_ENGAGEMENT_CEILING:
            signals.append(
                BottleneckSignal(
                    id="bn_cta",
                    stage="cta",
                    segment_ids=[],
                    description=(
                        f"{len(finishers)} personas reach the end but peak engagement "
                        f"is only {engagement:.0%}. Nothing converts the attention."
                    ),
                    severity=round(max(0.0, min(1.0, 1.0 - engagement * 4)), 4),
                    evidence=_quotes(finishers),
                )
            )

    # --- propagation ------------------------------------------------------
    mean_share = mean(r.share_probability for r in succeeded)
    died_early = bool(waves) and any(w.terminated and w.wave <= 2 for w in waves)
    if mean_share <= PROPAGATION_SHARE_CEILING or died_early:
        weak_sharers = [
            s.segment_id
            for s in segment_results
            if s.persona_count > 0 and s.share_rate <= PROPAGATION_SHARE_CEILING
        ]
        wave_note = ""
        if died_early and waves:
            terminal = next(w for w in waves if w.terminated)
            wave_note = f" The cascade dies at wave {terminal.wave}."
        signals.append(
            BottleneckSignal(
                id="bn_propagation",
                stage="propagation",
                segment_ids=weak_sharers,
                description=(
                    f"Mean share probability is {mean_share:.0%}, so the reel converts "
                    f"through saves rather than shares.{wave_note}"
                ),
                severity=round(max(0.0, min(1.0, 1.0 - mean_share * 5)), 4),
                evidence=_quotes(succeeded),
            )
        )

    # --- whole segments failing -------------------------------------------
    for segment in segment_results:
        if segment.persona_count > 0 and segment.score < WEAK_SEGMENT_SCORE:
            signals.append(
                BottleneckSignal(
                    id=f"bn_segment_{segment.segment_id}",
                    stage="retention",
                    segment_ids=[segment.segment_id],
                    description=(
                        f"{segment.segment_name} scores {segment.score:.2f} — this segment "
                        "is not being reached at all."
                    ),
                    severity=round(max(0.0, min(1.0, 1.0 - segment.score * 2)), 4),
                )
            )

    signals.sort(key=lambda signal: signal.severity, reverse=True)
    return signals


def _segments_for(
    subset: list[PersonaSimulationResult],
    all_results: list[PersonaSimulationResult],
    segment_results: list[AudienceSegmentResult],
) -> list[str]:
    """Best-effort mapping from personas back to their segments.

    Persona ids are `{segmentId}__{name}_{n}` (see `personas.profiles.slug_id`),
    so the segment is recoverable without threading the persona objects through
    every call. Falls back to an empty list when ids came from elsewhere, which
    the contract permits.
    """
    known = {segment.segment_id for segment in segment_results}
    found: list[str] = []
    _ = all_results

    for result in subset:
        prefix = result.persona_id.split("__", 1)[0]
        if prefix in known and prefix not in found:
            found.append(prefix)
    return found


# ---------------------------------------------------------------------------
# AI reflection
# ---------------------------------------------------------------------------

class _ProposedCause(ReelLabModel):
    signal_id: str
    likely_cause: str
    confidence: float


class _ProposedCauses(ReelLabModel):
    causes: list[_ProposedCause]


def build_prompt(
    content: ContentDNA | None,
    signals: list[BottleneckSignal],
    persona_results: list[PersonaSimulationResult],
) -> str:
    measured = "\n\n".join(
        f"signalId: {signal.id}\n"
        f"stage: {signal.stage}\n"
        f"measured: {signal.description}"
        + (
            "\nwhat those viewers said:\n"
            + "\n".join(f'  - "{quote}"' for quote in signal.evidence)
            if signal.evidence
            else ""
        )
        for signal in signals
    )

    reactions = "\n".join(
        f"- {r.action}"
        + (f" at {r.swipe_time:.1f}s" if r.swipe_time is not None else "")
        + f': "{r.reason}"'
        for r in persona_results
        if r.error is None
    )

    opening = (
        f'The reel opens with: "{content.hook.text}" '
        f"({content.hook.duration_seconds:.1f}s). "
        f"Duration {content.duration_seconds:.0f}s, tone {content.tone}."
        if content
        else "No Content DNA was available for this run."
    )

    return f"""A reel was simulated against a synthetic audience. The failure points
below were **measured** from the simulation. Your job is to explain what caused
each one.

{opening}

Measured failure points:

{measured}

Everything the synthetic viewers said:
{reactions}

For each signalId above, give the most likely *cause*, grounded in what those
viewers actually said. Not general short-form advice — the specific thing about
this reel that produced this pattern. "The hook is weak" restates the
measurement; "the opening names a category instead of a stake, so there is
nothing to stay for" is a cause.

Give a confidence (0-1) for each. If the viewer reasons do not actually support
a clear cause, say so in the cause text and give it a low confidence. A
low-confidence honest answer is more useful to us than a confident guess."""


def _to_bottleneck(signal: BottleneckSignal, cause: str, confidence: float) -> Bottleneck:
    return Bottleneck(
        id=signal.id,
        stage=signal.stage,  # type: ignore[arg-type]
        segment_ids=signal.segment_ids,
        description=signal.description,
        likely_cause=cause,
        severity=signal.severity,
        confidence=confidence,
    )


async def _explain_with_model(
    content: ContentDNA | None,
    signals: list[BottleneckSignal],
    persona_results: list[PersonaSimulationResult],
) -> list[Bottleneck]:
    proposal, metadata = await llm.complete_model(
        _ProposedCauses,
        prompt=build_prompt(content, signals, persona_results),
        prompt_version=PROMPT_VERSION,
        tier="reasoning",
        max_tokens=2048,
    )

    causes = {cause.signal_id: cause for cause in proposal.causes}
    log_event(
        logger,
        "reflection_model_call",
        model=metadata.model,
        signals=len(signals),
        explained=len(causes),
        estimated_cost_usd=metadata.estimated_cost_usd,
    )

    return [
        _to_bottleneck(
            signal,
            causes[signal.id].likely_cause if signal.id in causes else UNEXPLAINED,
            max(0.0, min(1.0, causes[signal.id].confidence)) if signal.id in causes else 0.0,
        )
        for signal in signals
    ]


UNEXPLAINED = (
    "Cause not analysed — the reasoning model was unavailable for this run. "
    "The measurement above is from the simulation and stands on its own."
)


def _measured_only(signals: list[BottleneckSignal]) -> list[Bottleneck]:
    """Honest fallback: report the measurement, admit the cause is unknown."""
    return [_to_bottleneck(signal, UNEXPLAINED, 0.0) for signal in signals]


async def analyze_bottlenecks(
    content: ContentDNA | None,
    persona_results: list[PersonaSimulationResult],
    segment_results: list[AudienceSegmentResult],
    waves: list[PropagationWave] | None = None,
    *,
    max_bottlenecks: int = 5,
) -> tuple[list[Bottleneck], bool]:
    """Detect and explain the failure points. Returns `(bottlenecks, mock)`."""
    signals = detect_signals(content, persona_results, segment_results, waves)[:max_bottlenecks]

    if not signals:
        log_event(logger, "no_bottlenecks_detected")
        return [], False

    bottlenecks, mock = await with_fixture_fallback(
        "simulation.reflect",
        lambda: _explain_with_model(content, signals, persona_results),
        lambda: _measured_only(signals),
    )

    log_event(logger, "bottlenecks_identified", count=len(bottlenecks), mock=mock)
    return bottlenecks, mock
