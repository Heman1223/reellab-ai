"""Propagation cascade.

    simulate_propagation(persona_results, seed=42) -> list[PropagationWave]

Deliberately deterministic mechanics. The AI decides whether a persona shares;
this file works out where that share lands and whether the cascade survives
another hop. When a cascade dies we want to point at the arithmetic that killed
it, not at a model's opinion.

## Model

    wave 0   the seeded audience, split across segments by persona count
    wave n   for each segment s that was reached:
                 viewers who actually watched   = reach(s) x meanWatch(s)
                 sharers ~ Binomial(watchers, meanShare(s))     [seeded]
                 new viewers in segment t       = sharers x spillover(s->t)
                                                             x AMPLIFICATION

Sampling is a normal approximation to the binomial, drawn from a seeded RNG, so
a run is **reproducible for a given seed** while still being a simulation rather
than a closed-form expectation. Without a seed one is derived from the persona
ids, so repeating the same run repeats the same cascade.

Stops when a wave reaches fewer than `MIN_REACH` people, or at `MAX_WAVES`.

This is a synthetic experimental environment. It is not a model of any real
platform's recommendation system, and `AMPLIFICATION` in particular is an
invented constant with no empirical basis yet — see docs/failure-log.md.

OWNER: Developer 1.
"""

from __future__ import annotations

import hashlib
import math
import random

from logging_utils import get_logger, log_event
from schemas import (
    AudienceGraph,
    AudienceSegmentResult,
    Persona,
    PersonaSimulationResult,
    PropagationWave,
)

logger = get_logger("propagation.engine")

#: Notional size of the seeded audience. Waves are relative to this, so the
#: absolute number matters less than the ratios between them.
SEED_REACH = 1000.0

#: New viewers reached per share. A placeholder until evaluation data exists.
AMPLIFICATION = 12.0

#: Stop once a wave reaches fewer than this many people.
MIN_REACH = 1.0

#: Hard cap on hops, so a dense adjacency matrix cannot run away.
MAX_WAVES = 5

#: Fallback bucket when we cannot attribute personas to segments.
UNSEGMENTED = "all"


def _derive_seed(persona_results: list[PersonaSimulationResult]) -> int:
    """Stable seed from the run's persona ids, so default runs reproduce."""
    raw = "|".join(sorted(result.persona_id for result in persona_results))
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8], 16)


def _segment_of(persona_id: str, personas: list[Persona] | None) -> str:
    """Attribute a persona result to its segment.

    Prefers the persona objects when the caller has them; otherwise recovers the
    segment from the `{segmentId}__{name}_{n}` id convention in
    `personas.profiles.slug_id`.
    """
    if personas:
        for persona in personas:
            if persona.id == persona_id:
                return persona.segment_id
    if "__" in persona_id:
        return persona_id.split("__", 1)[0]
    return UNSEGMENTED


def _behaviour_by_segment(
    persona_results: list[PersonaSimulationResult],
    personas: list[Persona] | None,
    segment_results: list[AudienceSegmentResult] | None,
) -> dict[str, tuple[float, float]]:
    """`{segmentId: (meanWatch, meanShare)}`, from segment results or personas."""
    if segment_results:
        return {
            result.segment_id: (result.average_watch_probability, result.share_rate)
            for result in segment_results
            if result.persona_count > 0
        }

    grouped: dict[str, list[PersonaSimulationResult]] = {}
    for result in persona_results:
        if result.error is not None:
            continue
        grouped.setdefault(_segment_of(result.persona_id, personas), []).append(result)

    return {
        segment_id: (
            sum(r.watch_probability for r in group) / len(group),
            sum(r.share_probability for r in group) / len(group),
        )
        for segment_id, group in grouped.items()
        if group
    }


def _sample_sharers(rng: random.Random, viewers: float, probability: float) -> float:
    """Draw a sharer count, normal-approximating Binomial(viewers, probability).

    Exact binomial sampling would mean looping once per viewer; at a thousand
    seeded viewers per wave that is wasted time for an identical distribution.
    """
    if viewers <= 0 or probability <= 0:
        return 0.0
    if probability >= 1:
        return viewers

    expected = viewers * probability
    spread = math.sqrt(viewers * probability * (1 - probability))
    return max(0.0, min(viewers, rng.gauss(expected, spread)))


def simulate_propagation(
    persona_results: list[PersonaSimulationResult],
    *,
    graph: AudienceGraph | None = None,
    segment_results: list[AudienceSegmentResult] | None = None,
    personas: list[Persona] | None = None,
    seed: int | None = None,
    seed_reach: float = SEED_REACH,
    amplification: float = AMPLIFICATION,
    max_waves: int = MAX_WAVES,
) -> list[PropagationWave]:
    """Run the cascade and return one `PropagationWave` per hop.

    Only `persona_results` is required. Supplying `graph` enables cross-segment
    spillover; without it the cascade stays inside the segments it started in,
    which is the honest answer when we do not know how audiences connect.
    """
    succeeded = [result for result in persona_results if result.error is None]
    if not succeeded:
        return []

    behaviour = _behaviour_by_segment(succeeded, personas, segment_results)
    if not behaviour:
        return []

    rng = random.Random(seed if seed is not None else _derive_seed(succeeded))

    # --- wave 0: split the seed audience by how much of it we simulated ------
    counts = {segment_id: 0 for segment_id in behaviour}
    for result in succeeded:
        segment_id = _segment_of(result.persona_id, personas)
        if segment_id in counts:
            counts[segment_id] += 1
    total = sum(counts.values()) or len(behaviour)

    reach: dict[str, float] = {
        segment_id: seed_reach * ((counts.get(segment_id, 0) or 1) / total)
        for segment_id in behaviour
    }

    waves: list[PropagationWave] = [
        PropagationWave(
            wave=0,
            segment_ids=sorted(reach),
            reach=round(sum(reach.values()), 2),
            pass_through_rate=_pass_through(reach, behaviour),
            terminated=False,
            note="Seed audience. Retention decides how much of this survives to spread.",
        )
    ]

    adjacency = graph.adjacency if graph else []
    seen: set[str] = set(reach)

    for wave_index in range(1, max_waves):
        next_reach: dict[str, float] = {}

        for segment_id, current in reach.items():
            watch, share = behaviour.get(segment_id, (0.0, 0.0))
            watchers = current * watch
            sharers = _sample_sharers(rng, watchers, share)
            if sharers <= 0:
                continue

            edges = [edge for edge in adjacency if edge.from_segment_id == segment_id]
            if not edges:
                # No known neighbours: shares still reach more of the same
                # segment, but at a heavy discount. Assuming they reach nobody
                # would understate a reel that genuinely spreads within a group.
                gained = sharers * amplification * 0.25
                if gained > 0:
                    next_reach[segment_id] = next_reach.get(segment_id, 0.0) + gained
                continue

            for edge in edges:
                if edge.to_segment_id not in behaviour:
                    continue
                gained = sharers * edge.spillover_probability * amplification
                if gained > 0:
                    next_reach[edge.to_segment_id] = (
                        next_reach.get(edge.to_segment_id, 0.0) + gained
                    )

        total_next = sum(next_reach.values())
        newly_reached = sorted(set(next_reach) - seen)
        terminated = total_next < MIN_REACH

        waves.append(
            PropagationWave(
                wave=wave_index,
                segment_ids=newly_reached,
                reach=round(total_next, 2),
                pass_through_rate=_pass_through(next_reach, behaviour),
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
        seed=seed,
        final_reach=waves[-1].reach,
        terminated=waves[-1].terminated,
    )
    return waves


def _pass_through(reach: dict[str, float], behaviour: dict[str, tuple[float, float]]) -> float:
    """Reach-weighted share rate: the fraction of this wave that carries it on."""
    total = sum(reach.values())
    if total <= 0:
        return 0.0

    weighted = sum(
        amount * behaviour.get(segment_id, (0.0, 0.0))[1]
        for segment_id, amount in reach.items()
    )
    return round(max(0.0, min(1.0, weighted / total)), 4)


def _note_for(wave: int, total_reach: float, newly_reached: list[str], terminated: bool) -> str:
    if terminated:
        return (
            "Cascade dies here. Nothing in the previous wave shares enough to reach "
            "a new audience."
        )
    if not newly_reached:
        return f"Wave {wave} reaches {total_reach:.0f} more viewers, but no new segments."
    return f"Spills into {len(newly_reached)} new segment(s)."
