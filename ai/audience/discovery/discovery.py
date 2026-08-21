"""Audience discovery — the first AI step in the product.

    discover_audience(request) -> AudienceGraph

The creator gives us a niche in their own words. The model's job is to break
that into sub-niches that behave *differently from each other*, because a
segmentation whose segments all react the same way tells the creator nothing.

This is not a lookup table. Remove the model and there is no discovery step —
which is exactly the property the project is supposed to have.

OWNER: Developer 1.
"""

from __future__ import annotations

from llm import llm, with_fixture_fallback
from logging_utils import get_logger, log_event
from schemas import AudienceGraph, AudienceRequest

import fixtures

logger = get_logger("audience.discovery")

PROMPT_VERSION = "audience-discovery-v0"


def _build_prompt(request: AudienceRequest) -> str:
    """The prompt is the product here. Version it whenever you change it."""
    return f"""You are segmenting a short-form video audience for a creator.

Niche: {request.niche}
Primary audience: {request.target_audience}
Secondary audience: {request.secondary_audience or "none stated"}
Location: {request.location}
Language: {request.language}
Creator goal: {request.creator_goal}

Identify the sub-niches inside this audience that would react *differently* to
the same video. A segmentation whose segments all behave identically is useless.

For each segment give: a short name, a description of who they are and what they
respond to, distinguishing characteristics, and a relevance score (0-1) against
the creator's stated goal.

Also estimate, for each ordered pair of segments, how likely content is to
spread from one to the other. That adjacency is what the propagation engine runs
on.

Return JSON matching the AudienceGraph schema."""


async def _discover_with_model(request: AudienceRequest) -> AudienceGraph:
    result = await llm.complete_json(
        prompt=_build_prompt(request),
        prompt_version=PROMPT_VERSION,
        tier="reasoning",
    )
    return AudienceGraph.model_validate(result.data)


def _fixture_graph(request: AudienceRequest) -> AudienceGraph:
    graph = fixtures.audience_graph()
    # Echo the caller's own brief back so the response is coherent even though
    # the segments came from a fixture.
    return graph.model_copy(update={"request": request})


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
        mock=mock,
    )
    return graph, mock
