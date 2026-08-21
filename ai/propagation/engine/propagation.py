"""Propagation cascade.

    simulate_propagation(graph, segment_results, persona_results) -> list[PropagationWave]

Deliberately deterministic. The AI decides whether a persona shares; this file
only works out where a share lands and whether the cascade survives another hop.
Mechanics like these should be reproducible and inspectable — if the cascade
dies, we want to be able to point at the arithmetic that killed it rather than
at a model's opinion.

Model:

    wave 0  the seeded segments (those we generated personas for)
    wave n  reach(n) = Σ  reach(n-1, s) × shareRate(s) × spillover(s → t) × AMPLIFICATION

`AMPLIFICATION` is how many new viewers one share is worth. Everything here is a
crude first approximation and is meant to be replaced once the evaluation
harness can tell us whether it predicts anything.

OWNER: Developer 1.
"""

from __future__ import annotations

from logging_utils import get_logger, log_event
from schemas import (
    AudienceGraph,
    AudienceSegmentResult,
    PersonaSimulationResult,
    PropagationWave,
)

logger = get_logger("propagation.engine")

#: Notional size of the seeded audience. Waves are relative to this, so the
#: absolute number matters less than the ratios between waves.
SEED_REACH = 1000.0

#: New viewers reached per share. A placeholder until evaluation data exists.
AMPLIFICATION = 12.0

#: Stop once a wave reaches fewer than this many people.
MIN_REACH = 1.0

#: Hard cap on hops, so a pathological adjacency matrix cannot loop forever.
MAX_WAVES = 5


def simulate_propagation(
    graph: AudienceGraph,
    segment_results: list[AudienceSegmentResult],
    persona_results: list[PersonaSimulationResult] | None = None,
) -> list[PropagationWave]:
    """Run the cascade and return one `PropagationWave` per hop."""
    results_by_segment = {result.segment_id: result for result in segment_results}
    if not results_by_segment:
        return []

    # Wave 0: everything we actually simulated, split by relevance.
    total_personas = sum(result.persona_count for result in segment_results) or 1
    reach: dict[str, float] = {
        result.segment_id: SEED_REACH * (result.persona_count / total_personas)
        for result in segment_results
    }

    waves: list[PropagationWave] = [
        PropagationWave(
            wave=0,
            segment_ids=sorted(reach),
            reach=round(sum(reach.values()), 2),
            pass_through_rate=_pass_through(reach, results_by_segment),
            terminated=False,
            note="Seed audience. Retention decides how much of this survives to spread.",
        )
    ]

    seen: set[str] = set(reach)

    for wave_index in range(1, MAX_WAVES):
        next_reach: dict[str, float] = {}

        for edge in graph.adjacency:
            source_reach = reach.get(edge.from_segment_id, 0.0)
            if source_reach <= 0:
                continue

            source_result = results_by_segment.get(edge.from_segment_id)
            if source_result is None:
                continue

            # Only viewers who watched can share; sharing without watching is
            # not a behaviour we want the model to be able to invent.
            effective_shares = (
                source_reach
                * source_result.average_watch_probability
                * source_result.share_rate
            )
            gained = effective_shares * edge.spillover_probability * AMPLIFICATION

            if gained > 0:
                next_reach[edge.to_segment_id] = next_reach.get(edge.to_segment_id, 0.0) + gained

        total_next = sum(next_reach.values())
        newly_reached = sorted(set(next_reach) - seen)
        terminated = total_next < MIN_REACH

        waves.append(
            PropagationWave(
                wave=wave_index,
                segment_ids=newly_reached,
                reach=round(total_next, 2),
                pass_through_rate=_pass_through(next_reach, results_by_segment),
                terminated=terminated,
                note=_note_for(wave_index, total_next, newly_reached, terminated),
            )
        )

        if terminated:
            break

        seen.update(next_reach)
        reach = next_reach

    log_event(
        logger,
        "propagation_simulated",
        wave_count=len(waves),
        final_reach=waves[-1].reach,
        terminated=waves[-1].terminated,
    )
    return waves


def _pass_through(
    reach: dict[str, float], results: dict[str, AudienceSegmentResult]
) -> float:
    """Reach-weighted share rate: the fraction of this wave that carries it onward."""
    total = sum(reach.values())
    if total <= 0:
        return 0.0

    weighted = sum(
        amount * results[segment_id].share_rate
        for segment_id, amount in reach.items()
        if segment_id in results
    )
    return round(min(1.0, weighted / total), 4)


def _note_for(
    wave: int, total_reach: float, newly_reached: list[str], terminated: bool
) -> str:
    if terminated:
        return (
            "Cascade dies here. Nothing in the previous wave shares enough to reach "
            "a new audience."
        )
    if not newly_reached:
        return f"Wave {wave} reaches {total_reach:.0f} more viewers, but no new segments."
    return f"Spills into {len(newly_reached)} new segment(s)."
