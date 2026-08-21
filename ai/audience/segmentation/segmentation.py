"""Segment graph assembly, repair and traversal.

Deterministic only — no model calls belong in this file. Keeping the mechanics
here means the AI in `discovery.py` is judged on the quality of its segmentation
rather than on whether it remembered to produce a well-formed tree.

The repair step matters more than it looks. A model that invents a parent name
it never defined, or an adjacency edge pointing at a segment that does not
exist, produces a graph that renders with holes in it three services away. Fix
it here, once, where the failure is visible.

OWNER: Developer 1.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from schemas import AudienceGraph, AudienceRequest, AudienceSegment, SegmentAdjacency

#: Root + sub-niche + one optional split. Deeper than this is a knowledge graph,
#: which is not what a 24-hour hackathon needs.
MAX_DEPTH = 3

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(name: str, prefix: str = "seg") -> str:
    """`"Beginner Natural Lifters"` -> `"seg_beginner_natural_lifters"`."""
    cleaned = _SLUG_STRIP.sub("_", name.strip().lower()).strip("_")
    return f"{prefix}_{cleaned[:48]}" if cleaned else f"{prefix}_unnamed"


def graph_id_for(request: AudienceRequest) -> str:
    """Deterministic graph id, so the same brief yields the same id.

    Deterministic rather than random because a stable id is what makes caching
    and re-running an experiment against "the same audience" possible later.
    """
    raw = f"{request.niche}|{request.target_audience}|{request.location}|{request.language}"
    return f"graph_{hashlib.sha256(raw.lower().encode('utf-8')).hexdigest()[:12]}"


def _clamp(value: float | None, low: float = 0.0, high: float = 1.0) -> float | None:
    if value is None:
        return None
    return max(low, min(high, float(value)))


def assemble_graph(
    *,
    request: AudienceRequest,
    segments: list[dict[str, Any]],
    adjacency: list[dict[str, Any]],
) -> AudienceGraph:
    """Turn name-keyed model output into a validated, id-keyed `AudienceGraph`.

    Repairs performed, all of them silent by design because each has an obvious
    correct answer:
      - assigns stable slug ids, de-duplicating collisions
      - resolves `parentName` / `fromName` / `toName` to ids
      - drops a parent reference that names a segment we do not have
      - flattens anything deeper than `MAX_DEPTH` onto its nearest valid ancestor
      - guarantees exactly one root
      - drops self-loops and duplicate edges, keeping the strongest
    """
    if not segments:
        raise ValueError("Cannot assemble a graph with no segments.")

    # --- ids ---------------------------------------------------------------
    by_name: dict[str, str] = {}
    used: set[str] = set()
    records: list[dict[str, Any]] = []

    for raw in segments:
        name = str(raw.get("name") or "").strip() or "Unnamed segment"
        segment_id = slugify(name)
        if segment_id in used:
            segment_id = f"{segment_id}_{len(used)}"
        used.add(segment_id)
        by_name[name.lower()] = segment_id
        records.append({**raw, "name": name, "id": segment_id})

    # --- parents -----------------------------------------------------------
    for record in records:
        parent_name = (record.get("parent_name") or "").strip().lower()
        parent_id = by_name.get(parent_name)
        # A parent that points at itself is the same bug as no parent at all.
        record["parent_segment"] = None if parent_id == record["id"] else parent_id

    _ensure_single_root(records)
    _cap_depth(records)

    built = [
        AudienceSegment(
            id=record["id"],
            name=record["name"],
            description=str(record.get("description") or "").strip() or record["name"],
            parent_segment=record["parent_segment"],
            characteristics=[str(item) for item in (record.get("characteristics") or [])],
            relevance_score=_clamp(record.get("relevance_score")) or 0.0,
            estimated_share=_clamp(record.get("estimated_share")),
            rationale=record.get("rationale"),
        )
        for record in records
    ]

    return AudienceGraph(
        graph_id=graph_id_for(request),
        request=request,
        segments=built,
        adjacency=_resolve_edges(adjacency, by_name, {segment.id for segment in built}),
    )


def _ensure_single_root(records: list[dict[str, Any]]) -> None:
    """Guarantee exactly one `parent_segment is None`.

    Zero roots means every segment claims a parent, which is a cycle. More than
    one root means the tree is a forest and `targetable_segments` would treat
    context nodes as targets.
    """
    roots = [record for record in records if record["parent_segment"] is None]

    if len(roots) == 1:
        return

    if not roots:
        # Break the cycle at the most relevant segment.
        records.sort(key=lambda record: record.get("relevance_score") or 0, reverse=True)
        records[0]["parent_segment"] = None
        return

    # Keep the least goal-specific segment as the root; it is the broad niche.
    roots.sort(key=lambda record: record.get("relevance_score") or 0)
    primary = roots[0]
    for extra in roots[1:]:
        extra["parent_segment"] = primary["id"]


def _cap_depth(records: list[dict[str, Any]]) -> None:
    """Reparent anything below `MAX_DEPTH` onto its deepest allowed ancestor."""
    parents = {record["id"]: record["parent_segment"] for record in records}

    def ancestry(segment_id: str) -> list[str]:
        chain: list[str] = []
        current = parents.get(segment_id)
        seen = {segment_id}
        while current and current not in seen:
            chain.append(current)
            seen.add(current)
            current = parents.get(current)
        return chain

    for record in records:
        chain = ancestry(record["id"])
        depth = len(chain) + 1
        if depth <= MAX_DEPTH:
            continue
        # chain[0] is the immediate parent; walk out to the one that sits at
        # MAX_DEPTH - 1 and attach there.
        record["parent_segment"] = chain[depth - MAX_DEPTH]


def _resolve_edges(
    adjacency: list[dict[str, Any]],
    by_name: dict[str, str],
    valid_ids: set[str],
) -> list[SegmentAdjacency]:
    """Resolve name-keyed edges to ids, dropping anything unusable."""
    best: dict[tuple[str, str], float] = {}

    for raw in adjacency:
        source = by_name.get(str(raw.get("from_name") or "").strip().lower())
        target = by_name.get(str(raw.get("to_name") or "").strip().lower())

        if not source or not target or source == target:
            continue
        if source not in valid_ids or target not in valid_ids:
            continue

        probability = _clamp(raw.get("spillover_probability")) or 0.0
        if probability <= 0:
            continue

        key = (source, target)
        best[key] = max(best.get(key, 0.0), probability)

    return [
        SegmentAdjacency(from_segment_id=source, to_segment_id=target, spillover_probability=value)
        for (source, target), value in sorted(best.items())
    ]


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

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

    An empty list means the graph is well-formed. It says nothing about whether
    the segmentation is any *good* — that is what evaluation is for.
    """
    problems: list[str] = []
    ids = {segment.id for segment in graph.segments}

    if not graph.segments:
        problems.append("Graph has no segments.")

    if len(ids) != len(graph.segments):
        problems.append("Duplicate segment ids.")

    for segment in graph.segments:
        if segment.parent_segment is not None and segment.parent_segment not in ids:
            problems.append(
                f"Segment '{segment.id}' references unknown parent '{segment.parent_segment}'."
            )

    for edge in graph.adjacency:
        if edge.from_segment_id not in ids:
            problems.append(f"Adjacency references unknown source '{edge.from_segment_id}'.")
        if edge.to_segment_id not in ids:
            problems.append(f"Adjacency references unknown target '{edge.to_segment_id}'.")

    roots = root_segments(graph)
    if not roots:
        problems.append("Graph has no root segment; every segment claims a parent.")
    elif len(roots) > 1:
        problems.append(f"Graph has {len(roots)} roots; expected exactly one.")

    if not targetable_segments(graph):
        problems.append("Graph has no leaf segments to simulate.")

    return problems
