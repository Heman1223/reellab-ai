"""Turning individual reactions into segment-level numbers.

Deterministic arithmetic only — this is the part of the simulation that must
*not* be an AI decision. The model decides how each persona behaves; the maths
here decides what those behaviours add up to, and it needs to be inspectable and
reproducible.

OWNER: Developer 1.
"""

from __future__ import annotations

from statistics import mean

from schemas import (
    AudienceSegment,
    AudienceSegmentResult,
    Persona,
    PersonaSimulationResult,
)

#: Verdict thresholds on the 0-1 segment score. Tune with evaluation data, not
#: by intuition — and record the change in docs/failure-log.md when you do.
STRONG_THRESHOLD = 0.6
WEAK_THRESHOLD = 0.35


def usable(results: list[PersonaSimulationResult]) -> list[PersonaSimulationResult]:
    """Drop personas whose simulation failed, so they do not drag the average."""
    return [result for result in results if result.error is None]


def segment_score(results: list[PersonaSimulationResult]) -> float:
    """Weighted blend of the funnel: getting watched, finishing, and being passed on.

    Weights are a starting point, not a finding. Completion is weighted highest
    because it is the strongest signal a platform's ranking actually responds to;
    sharing is weighted next because it is what drives propagation.
    """
    if not results:
        return 0.0

    return round(
        0.35 * mean(r.watch_probability for r in results)
        + 0.40 * mean(r.completion_probability for r in results)
        + 0.15 * mean(r.share_probability for r in results)
        + 0.10 * mean(r.save_probability for r in results),
        4,
    )


def verdict_for(score: float) -> str:
    if score >= STRONG_THRESHOLD:
        return "strong"
    if score < WEAK_THRESHOLD:
        return "weak"
    return "mixed"


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
        verdict=verdict_for(score),
    )


def aggregate_confidence(results: list[PersonaSimulationResult]) -> float:
    """Mean model confidence, discounted for a small sample.

    Three personas agreeing is not the same evidence as fifteen agreeing, and
    reporting both as 0.8 would be a lie the creator has no way to detect.
    """
    if not results:
        return 0.0

    base = mean(result.confidence for result in results)
    sample_penalty = min(1.0, len(results) / 10)
    return round(base * (0.6 + 0.4 * sample_penalty), 4)


def overall_score(segment_results: list[AudienceSegmentResult]) -> float:
    """Reach-weighted blend across segments, weighted by how many personas ran."""
    if not segment_results:
        return 0.0

    total_personas = sum(result.persona_count for result in segment_results)
    if total_personas == 0:
        return 0.0

    return round(
        sum(result.score * result.persona_count for result in segment_results) / total_personas,
        4,
    )
