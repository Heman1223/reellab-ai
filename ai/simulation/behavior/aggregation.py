"""Turning individual reactions into segment- and audience-level numbers.

Deterministic arithmetic only — this is the part of the simulation that must
*not* be an AI decision. The model decides how each persona behaves; the maths
here decides what those behaviours add up to, and it needs to be inspectable and
reproducible.

## Scoring methodology

`segment_score` is a weighted blend of the funnel:

    0.35 * mean(watchProbability)        did it earn attention at all
    0.40 * mean(completionProbability)   did it hold that attention
    0.15 * mean(shareProbability)        will it travel
    0.10 * mean(saveProbability)         was it worth keeping

Completion carries the most weight because it is the strongest signal a
short-form platform's ranking actually responds to; sharing is next because it
is what drives propagation. **These weights are a starting point, not a
finding.** Tune them against `ai/evaluation/` once there is real data, and record
the change in docs/failure-log.md.

`overall_score` is the persona-count-weighted mean of segment scores. It is a
**simulated propagation potential on a 0-1 scale**. It is not a view count, not
a percentage, and not a prediction of Instagram reach. Anyone presenting it as
one is misrepresenting it.

OWNER: Developer 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, pstdev

from schemas import (
    AudienceGraph,
    AudienceSegment,
    AudienceSegmentResult,
    ContentDNA,
    Persona,
    PersonaSimulationResult,
)

#: Verdict thresholds on the 0-1 segment score. Tune with evaluation data, not
#: by intuition.
STRONG_THRESHOLD = 0.6
WEAK_THRESHOLD = 0.35

#: Funnel weights. See the methodology note above.
WEIGHT_WATCH = 0.35
WEIGHT_COMPLETION = 0.40
WEIGHT_SHARE = 0.15
WEIGHT_SAVE = 0.10

#: Sample size at which we stop discounting confidence for a small run.
FULL_SAMPLE = 10


def usable(results: list[PersonaSimulationResult]) -> list[PersonaSimulationResult]:
    """Drop personas whose simulation failed, so they do not drag the average."""
    return [result for result in results if result.error is None]


def segment_score(results: list[PersonaSimulationResult]) -> float:
    """Weighted funnel blend for one set of persona reactions."""
    if not results:
        return 0.0

    return round(
        WEIGHT_WATCH * mean(r.watch_probability for r in results)
        + WEIGHT_COMPLETION * mean(r.completion_probability for r in results)
        + WEIGHT_SHARE * mean(r.share_probability for r in results)
        + WEIGHT_SAVE * mean(r.save_probability for r in results),
        4,
    )


def verdict_for(score: float) -> str:
    if score >= STRONG_THRESHOLD:
        return "strong"
    if score < WEAK_THRESHOLD:
        return "weak"
    return "mixed"


def disagreement(results: list[PersonaSimulationResult]) -> float:
    """How much the personas disagree with each other, 0 (unanimous) .. ~0.5.

    Population standard deviation of the two funnel probabilities that matter
    most. High disagreement is not noise to be smoothed away — it means the reel
    genuinely splits this audience, and the creator should be told that rather
    than handed an average nobody in the segment would recognise.
    """
    if len(results) < 2:
        return 0.0

    return round(
        mean(
            [
                pstdev([r.watch_probability for r in results]),
                pstdev([r.completion_probability for r in results]),
            ]
        ),
        4,
    )


def aggregate_segment(
    segment: AudienceSegment,
    personas: list[Persona],
    results: list[PersonaSimulationResult],
) -> AudienceSegmentResult:
    """Roll one segment's persona results into a segment result."""
    persona_ids = {persona.id for persona in personas}
    relevant = usable([r for r in results if r.persona_id in persona_ids])

    if not relevant:
        return AudienceSegmentResult(
            segment_id=segment.id,
            segment_name=segment.name,
            score=0.0,
            average_watch_probability=0.0,
            average_completion_probability=0.0,
            share_rate=0.0,
            save_rate=0.0,
            persona_count=0,
            confidence=0.0,
            verdict="weak",
        )

    score = segment_score(relevant)

    return AudienceSegmentResult(
        segment_id=segment.id,
        segment_name=segment.name,
        score=score,
        average_watch_probability=round(mean(r.watch_probability for r in relevant), 4),
        average_completion_probability=round(
            mean(r.completion_probability for r in relevant), 4
        ),
        share_rate=round(mean(r.share_probability for r in relevant), 4),
        save_rate=round(mean(r.save_probability for r in relevant), 4),
        persona_count=len(relevant),
        confidence=aggregate_confidence(relevant),
        verdict=verdict_for(score),  # type: ignore[arg-type]
    )


def aggregate_confidence(results: list[PersonaSimulationResult]) -> float:
    """Mean model confidence, discounted for a small sample.

    Three personas agreeing is not the same evidence as fifteen agreeing, and
    reporting both as 0.8 would be a lie the creator has no way to detect.
    """
    if not results:
        return 0.0

    base = mean(result.confidence for result in results)
    sample_penalty = min(1.0, len(results) / FULL_SAMPLE)
    return round(base * (0.6 + 0.4 * sample_penalty), 4)


def overall_score(segment_results: list[AudienceSegmentResult]) -> float:
    """Persona-count-weighted mean across segments, 0-1."""
    if not segment_results:
        return 0.0

    total_personas = sum(result.persona_count for result in segment_results)
    if total_personas == 0:
        return 0.0

    return round(
        sum(result.score * result.persona_count for result in segment_results) / total_personas,
        4,
    )


# ---------------------------------------------------------------------------
# Confidence, explained
# ---------------------------------------------------------------------------

@dataclass
class ConfidenceBreakdown:
    """Why the confidence number is what it is.

    The hackathon's "handle being wrong" constraint is not satisfied by emitting
    a number called confidence — it is satisfied by being able to say *which*
    factor dragged it down. Every field here is 0-1, higher is better.
    """

    model_confidence: float = 0.0
    sample_size: float = 0.0
    success_rate: float = 0.0
    agreement: float = 0.0
    content_completeness: float = 0.0
    value: float = 0.0
    notes: list[str] = field(default_factory=list)

    def as_fields(self) -> dict[str, float]:
        return {
            "modelConfidence": self.model_confidence,
            "sampleSize": self.sample_size,
            "successRate": self.success_rate,
            "agreement": self.agreement,
            "contentCompleteness": self.content_completeness,
        }


#: Weights over the five confidence factors. They sum to 1.
CONFIDENCE_WEIGHTS = {
    "model_confidence": 0.30,
    "sample_size": 0.20,
    "success_rate": 0.20,
    "agreement": 0.15,
    "content_completeness": 0.15,
}


def content_gaps(content: ContentDNA | None) -> list[str]:
    """Missing Content DNA that would make the simulation less trustworthy.

    A persona reasoning over a reel with no transcript and no scene breakdown is
    guessing, and the result should not claim otherwise.
    """
    if content is None:
        return ["No Content DNA supplied at all."]

    gaps: list[str] = []
    if not content.transcript.strip():
        gaps.append("Transcript is empty; personas cannot react to what was said.")
    if not content.scenes:
        gaps.append("No scene breakdown; the viewer journey is a single undifferentiated block.")
    if content.duration_seconds <= 0:
        gaps.append("Duration is missing or zero.")
    if not content.topic.strip():
        gaps.append("No topic identified.")
    if content.hook.duration_seconds <= 0:
        gaps.append("Hook was not isolated; hook bottleneck detection will be unreliable.")
    return gaps


def compute_confidence(
    results: list[PersonaSimulationResult],
    *,
    requested: int,
    content: ContentDNA | None = None,
) -> ConfidenceBreakdown:
    """Overall run confidence, with the reasoning attached.

    Deliberately a weighted mean rather than a product: a product of five
    factors drives confidence toward zero on any real run and stops being
    informative. A mean keeps the number readable while still moving when a
    factor degrades.
    """
    succeeded = usable(results)
    breakdown = ConfidenceBreakdown()

    if not succeeded:
        breakdown.notes.append("No personas completed successfully; confidence is zero.")
        return breakdown

    gaps = content_gaps(content)

    breakdown.model_confidence = round(mean(r.confidence for r in succeeded), 4)
    breakdown.sample_size = round(min(1.0, len(succeeded) / FULL_SAMPLE), 4)
    breakdown.success_rate = round(len(succeeded) / max(1, requested), 4)
    # Disagreement tops out around 0.5 in practice; scale it onto 0-1.
    breakdown.agreement = round(max(0.0, 1.0 - disagreement(succeeded) * 2), 4)
    breakdown.content_completeness = round(max(0.0, 1.0 - 0.2 * len(gaps)), 4)

    breakdown.value = round(
        sum(
            getattr(breakdown, factor) * weight
            for factor, weight in CONFIDENCE_WEIGHTS.items()
        ),
        4,
    )

    if breakdown.success_rate < 1.0:
        breakdown.notes.append(
            f"{len(succeeded)}/{requested} personas completed successfully."
        )
    if breakdown.sample_size < 1.0:
        breakdown.notes.append(
            f"Only {len(succeeded)} personas simulated; below the {FULL_SAMPLE} "
            "needed for a stable estimate."
        )
    if breakdown.agreement < 0.6:
        breakdown.notes.append(
            "Personas disagree strongly — this reel splits the audience rather "
            "than performing uniformly."
        )
    breakdown.notes.extend(gaps)

    return breakdown


# ---------------------------------------------------------------------------
# Audience-level analysis
# ---------------------------------------------------------------------------

@dataclass
class AudienceAnalysis:
    """Which segments matter, derived from results rather than assumed."""

    strongest_segment_id: str | None = None
    weakest_segment_id: str | None = None
    #: Segments that performed well despite low goal-relevance — audiences the
    #: creator was not aiming at but is reaching.
    cross_niche_segment_ids: list[str] = field(default_factory=list)
    #: Segment with the widest gap between watching and finishing.
    largest_dropoff_segment_id: str | None = None
    largest_dropoff_delta: float = 0.0


#: A segment is a cross-niche opportunity when it beats this score while being
#: below this relevance to the creator's stated goal.
CROSS_NICHE_MIN_SCORE = 0.5
CROSS_NICHE_MAX_RELEVANCE = 0.7


def analyse_audience(
    segment_results: list[AudienceSegmentResult],
    graph: AudienceGraph | None = None,
) -> AudienceAnalysis:
    """Strongest, weakest, cross-niche and largest drop-off — all from data."""
    scored = [result for result in segment_results if result.persona_count > 0]
    if not scored:
        return AudienceAnalysis()

    relevance = (
        {segment.id: segment.relevance_score for segment in graph.segments} if graph else {}
    )

    best = max(scored, key=lambda result: result.score)
    worst = min(scored, key=lambda result: result.score)

    dropoffs = [
        (
            result.segment_id,
            round(result.average_watch_probability - result.average_completion_probability, 4),
        )
        for result in scored
    ]
    dropoff_segment, dropoff_delta = max(dropoffs, key=lambda item: item[1])

    return AudienceAnalysis(
        strongest_segment_id=best.segment_id,
        weakest_segment_id=worst.segment_id,
        cross_niche_segment_ids=[
            result.segment_id
            for result in scored
            if result.score >= CROSS_NICHE_MIN_SCORE
            and relevance.get(result.segment_id, 1.0) < CROSS_NICHE_MAX_RELEVANCE
        ],
        largest_dropoff_segment_id=dropoff_segment,
        largest_dropoff_delta=dropoff_delta,
    )
