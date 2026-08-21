"""Audience discovery and segmentation. OWNER: Developer 1.

Public surface:

    discover_audience(request)      -> (AudienceGraph, mock)
    targetable_segments(graph)      -> leaf segments, most relevant first
    validate_graph(graph)           -> list of structural problems
    assemble_graph(...)             -> build a graph from name-keyed model output
"""

from .discovery.discovery import audience_cache_key, discover_audience
from .segmentation.segmentation import (
    adjacency_from,
    assemble_graph,
    children_of,
    graph_id_for,
    root_segments,
    targetable_segments,
    validate_graph,
)

__all__ = [
    "discover_audience",
    "audience_cache_key",
    "adjacency_from",
    "assemble_graph",
    "children_of",
    "graph_id_for",
    "root_segments",
    "targetable_segments",
    "validate_graph",
]
