"""Segment graph utilities.

Deterministic helpers only — shaping and validating the graph the model
produced. No model calls belong in this file. Keeping the mechanics here means
the AI in `discovery.py` can be judged on the quality of its segmentation rather
than on whether it remembered to produce a well-formed tree.

OWNER: Developer 1.
"""

from __future__ import annotations

from schemas import AudienceGraph, AudienceSegment, SegmentAdjacency


def root_segments(graph: AudienceGraph) -> list[AudienceSegment]:
    return [segment for segment in graph.segments if segment.parent_segment is None]


def children_of(graph: AudienceGraph, segment_id: str) -> list[AudienceSegment]:
    return [segment for segment in graph.segments if segment.parent_segment == segment_id]


def targetable_segments(graph: AudienceGraph) -> list[AudienceSegment]:
    """Leaf segments, most relevant first.

    Roots are the broad niche and are not simulated directly — personas are
    generated for the leaves, where behaviour actually differs.
    """
    leaves = [segment for segment in graph.segments if not children_of(graph, segment.id)]
    return sorted(leaves, key=lambda segment: segment.relevance_score, reverse=True)


def adjacency_from(graph: AudienceGraph, segment_id: str) -> list[SegmentAdjacency]:
    return [edge for edge in graph.adjacency if edge.from_segment_id == segment_id]


def validate_graph(graph: AudienceGraph) -> list[str]:
    """Structural problems in a graph, as human-readable strings.

    Run this on model output before trusting it. An empty list means the graph
    is well-formed; it says nothing about whether the segmentation is *good*.
    """
    problems: list[str] = []
    ids = {segment.id for segment in graph.segments}

    if not graph.segments:
        problems.append("Graph has no segments.")

    if len(ids) != len(graph.segments):
        problems.append("Duplicate segment ids.")

    for segment in graph.segments:
        if segment.parent_segment is not None and segment.parent_segment not in ids:
            problems.append(f"Segment '{segment.id}' references unknown parent '{segment.parent_segment}'.")

    for edge in graph.adjacency:
        if edge.from_segment_id not in ids:
            problems.append(f"Adjacency references unknown source '{edge.from_segment_id}'.")
        if edge.to_segment_id not in ids:
            problems.append(f"Adjacency references unknown target '{edge.to_segment_id}'.")

    if not root_segments(graph):
        problems.append("Graph has no root segment; every segment claims a parent.")

    return problems
