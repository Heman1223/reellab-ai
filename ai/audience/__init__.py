"""Audience discovery and segmentation. OWNER: Developer 1."""

from .discovery.discovery import discover_audience
from .segmentation.segmentation import (
    adjacency_from,
    children_of,
    root_segments,
    targetable_segments,
    validate_graph,
)

__all__ = [
    "discover_audience",
    "adjacency_from",
    "children_of",
    "root_segments",
    "targetable_segments",
    "validate_graph",
]
