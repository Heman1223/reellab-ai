/**
 * ReelLab shared contract — Audience.
 *
 * OWNER OF CHANGES: Developer 1 (AI / Simulation Lead), with review from
 * Developer 3 (frontend) and Developer 4 (backend).
 *
 * CONTRACT RULES (see docs/development-workflow.md):
 *  - Additive changes only. New fields must be optional.
 *  - Never rename or repurpose an existing field mid-hackathon.
 *  - Types only. This file must stay free of runtime code so every consumer
 *    can `import type` it with zero bundling or emit consequences.
 */

/** A probability or normalised score in the inclusive range 0..1. */
export type UnitScore = number;

/**
 * What the creator tells us before any AI runs.
 * This is the single input that seeds audience discovery.
 */
export interface AudienceRequest {
  /** Broad vertical, e.g. "fitness", "personal finance", "study with me". */
  niche: string;
  /** Primary audience in the creator's own words. */
  targetAudience: string;
  /** Optional secondary audience the creator also wants to reach. */
  secondaryAudience?: string;
  /** Geography, e.g. "India", "Tier-2 India", "US + Canada". */
  location: string;
  /** Content language, e.g. "English", "Hinglish". */
  language: string;
  /** What the creator is optimising for, e.g. "increase reach among beginners". */
  creatorGoal: string;
}

/**
 * One node of the discovered audience graph.
 *
 * Segments form a shallow tree: a segment with `parentSegment === null` is a
 * top-level niche; children are AI-discovered sub-niches.
 */
export interface AudienceSegment {
  id: string;
  name: string;
  description: string;
  /** `null` for a root niche, otherwise the parent segment's `id`. */
  parentSegment: string | null;
  /** Short descriptive traits, e.g. ["price-sensitive", "watches at night"]. */
  characteristics: string[];
  /** How relevant this segment is to the creator's goal, 0..1. */
  relevanceScore: UnitScore;
  /** Rough share of the reachable audience this segment represents, 0..1. */
  estimatedShare?: UnitScore;
  /** Free-form AI justification, surfaced in the UI for transparency. */
  rationale?: string;
}

/**
 * The full result of `POST /api/v1/audience/discover`.
 * `segments` is flat; the frontend rebuilds the tree from `parentSegment`.
 */
export interface AudienceGraph {
  /** Stable id so the frontend can cache and the backend can persist. */
  graphId: string;
  request: AudienceRequest;
  segments: AudienceSegment[];
  /** Edges between segments used by the propagation engine, if discovered. */
  adjacency?: SegmentAdjacency[];
}

/**
 * Directed likelihood that content spreads from one segment to another.
 * Consumed by the propagation engine; optional during early development.
 */
export interface SegmentAdjacency {
  fromSegmentId: string;
  toSegmentId: string;
  /** Probability that a share in `from` reaches `to`, 0..1. */
  spilloverProbability: UnitScore;
}
