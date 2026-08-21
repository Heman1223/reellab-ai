"""Audience discovery — the first AI step in the product.

    discover_audience(request) -> (AudienceGraph, mock)

The creator gives us a niche in their own words. The model's job is to break
that into sub-niches that behave *differently from each other*, because a
segmentation whose segments all react the same way tells the creator nothing.

Nothing about the segmentation is hard-coded. The only fitness-specific strings
in this module are inside a worked example in the prompt, shown to demonstrate
the *shape* of a good answer — the model is explicitly told not to reuse it.

**Why the model does not choose ids.** It proposes segments by *name* and links
them by name; `segmentation.assemble_graph` derives stable slug ids and resolves
the references. Models are unreliable at keeping an id consistent between a
`segments` array and an `adjacency` array twenty lines later, and a dangling
edge is a silent hole in the propagation cascade.

OWNER: Developer 1.
"""

from __future__ import annotations

import hashlib

from pydantic import Field

from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from schemas import AudienceGraph, AudienceRequest
from schemas.base import ReelLabModel

import fixtures

from ..segmentation.segmentation import assemble_graph, validate_graph

logger = get_logger("audience.discovery")

PROMPT_VERSION = "audience-discovery-v1"

#: Segment count bounds. Too few and there is nothing to compare; too many and
#: every segment gets one persona and the whole run is noise.
MIN_SEGMENTS = 3
MAX_SEGMENTS = 8


class _ProposedSegment(ReelLabModel):
    """One segment as the model proposes it, before we assign ids."""

    name: str = Field(description="Short, specific segment name.")
    description: str = Field(description="Who they are and what they respond to.")
    parent_name: str | None = Field(
        default=None,
        description="Name of the parent segment, or null for the root niche.",
    )
    characteristics: list[str] = Field(
        default_factory=list,
        description="Traits that make this segment behave differently from its siblings.",
    )
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="Relevance to the creator's stated goal."
    )
    estimated_share: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Share of the reachable audience."
    )
    rationale: str | None = Field(
        default=None, description="Why this segment was identified."
    )


class _ProposedEdge(ReelLabModel):
    """A directed spillover link, expressed by segment name."""

    from_name: str
    to_name: str
    spillover_probability: float = Field(ge=0.0, le=1.0)


class _ProposedAudience(ReelLabModel):
    segments: list[_ProposedSegment]
    adjacency: list[_ProposedEdge] = Field(default_factory=list)


def audience_cache_key(request: AudienceRequest) -> str:
    """Stable key for `niche + target audience + location + language + goal`.

    Nothing reads this yet. It exists so persona and audience caching stays a
    small change rather than a refactor — see the cost notes in ai/README.md.
    """
    raw = "|".join(
        [
            request.niche.strip().lower(),
            request.target_audience.strip().lower(),
            (request.secondary_audience or "").strip().lower(),
            request.location.strip().lower(),
            request.language.strip().lower(),
            request.creator_goal.strip().lower(),
            PROMPT_VERSION,
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_prompt(request: AudienceRequest) -> str:
    """The prompt is the product here. Bump PROMPT_VERSION whenever it changes."""
    return f"""Segment a short-form video audience for a creator.

Niche: {request.niche}
Primary audience: {request.target_audience}
Secondary audience: {request.secondary_audience or "none stated"}
Location: {request.location}
Language: {request.language}
Creator goal: {request.creator_goal}

Identify the sub-niches inside this audience that would react *differently* to
the same video. A segmentation whose segments all behave identically is useless —
the differences are the entire point.

Structure:
- Exactly one root segment (parentName = null) representing the whole niche in
  this location. It is context, not a target.
- Between {MIN_SEGMENTS - 1} and {MAX_SEGMENTS - 1} sub-segments beneath it.
- Go at most one level deeper than that, and only where a sub-segment genuinely
  splits into two groups that behave differently.

For each segment give:
- name: short and specific. "Beginner Natural Lifters", not "Beginners".
- description: who they are, what they already believe, what earns their
  attention, and what makes them leave.
- characteristics: traits that drive *behaviour* — attention span, scepticism,
  when they watch, whether they share — not just demographics.
- relevanceScore (0-1) against the creator's stated goal.
- estimatedShare (0-1) of the reachable audience.
- rationale: what in the creator's brief led you to this segment.

Then, for pairs of segments where it applies, give adjacency: how likely content
is to spread from one to the other, referencing segments by their exact `name`.
This is what the propagation engine runs on. Think about who actually forwards
things to whom — a segment that watches a lot but shares nothing is a dead end.

Worked example of the *shape* of a good answer, for a completely different
niche — do not reuse any of its content:
  root "Home Cooking — UK", children "Batch-Cooking Parents" (time-poor, saves
  everything, shares almost nothing) and "Student First Kitchens" (cost-driven,
  shares in group chats), with adjacency from the students to the parents at a
  low probability because the audiences barely overlap.

Derive everything from the creator's actual brief above."""


async def _discover_with_model(request: AudienceRequest) -> AudienceGraph:
    proposal, metadata = await llm.complete_model(
        _ProposedAudience,
        prompt=build_prompt(request),
        prompt_version=PROMPT_VERSION,
        tier="reasoning",
        max_tokens=4096,
    )

    graph = assemble_graph(
        request=request,
        segments=[segment.model_dump() for segment in proposal.segments],
        adjacency=[edge.model_dump() for edge in proposal.adjacency],
    )

    problems = validate_graph(graph)
    if problems:
        # Structural problems are repaired by `assemble_graph`, so anything left
        # is worth knowing about but not worth failing the run over.
        log_event(logger, "audience_graph_problems", problems=problems[:5])

    log_event(
        logger,
        "audience_model_call",
        model=metadata.model,
        latency_ms=metadata.latency_ms,
        estimated_cost_usd=metadata.estimated_cost_usd,
    )
    return graph


def _fixture_graph(request: AudienceRequest) -> AudienceGraph:
    """Echo the caller's brief back over the fixture segments."""
    return fixtures.audience_graph().model_copy(update={"request": request})


async def discover_audience(request: AudienceRequest) -> tuple[AudienceGraph, bool]:
    """Discover the audience graph. Returns `(graph, mock)`."""
    graph, mock = await with_fixture_fallback(
        "audience.discover",
        lambda: _discover_with_model(request),
        lambda: _fixture_graph(request),
    )

    log_event(
        logger,
        "audience_discovered",
        niche=request.niche,
        segment_count=len(graph.segments),
        cache_key=audience_cache_key(request),
        mock=mock,
    )
    return graph, mock
