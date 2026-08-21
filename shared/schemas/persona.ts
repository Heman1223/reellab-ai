/**
 * ReelLab shared contract — Persona.
 *
 * OWNER OF CHANGES: Developer 1 (AI / Simulation Lead).
 * Types only — no runtime code. See shared/README.md for the contract rules.
 */

import type { AudienceSegment, UnitScore } from './audience';

/** How long a persona is willing to give a video before deciding to swipe. */
export interface AttentionProfile {
  /** Typical seconds before the persona decides to keep watching or swipe. */
  averageAttentionSeconds: number;
  /** How aggressively this persona swipes away, 0 (patient) .. 1 (ruthless). */
  swipeTendency: UnitScore;
  /** Things that reliably lose this persona, e.g. ["slow intro", "no captions"]. */
  dropOffTriggers: string[];
}

/** Baseline engagement rates, before any specific content is considered. */
export interface EngagementProfile {
  likeTendency: UnitScore;
  saveTendency: UnitScore;
  shareTendency: UnitScore;
  commentTendency: UnitScore;
  /** Chance this persona follows after a single strong reel, 0..1. */
  followTendency?: UnitScore;
}

/** Content this persona gravitates toward or bounces off. */
export interface ContentPreferences {
  preferredFormats: string[];
  preferredTones: string[];
  preferredDurationSeconds: { min: number; max: number };
  turnOffs: string[];
}

/**
 * A synthetic viewer. Personas are generated per `AudienceSegment` and are the
 * unit of simulation — one persona produces one `PersonaSimulationResult`.
 */
export interface Persona {
  id: string;
  /** The `AudienceSegment.id` this persona was generated for. */
  segmentId: string;
  name: string;
  /** One-line demographic sketch, e.g. "21, male, Pune, engineering student". */
  demographicSummary: string;
  interests: string[];
  behavioralTraits: string[];
  attentionProfile: AttentionProfile;
  engagementProfile: EngagementProfile;
  contentPreferences: ContentPreferences;
  /**
   * Compact natural-language brief handed to the reasoning model when this
   * persona watches a reel. Generated once, then cached — see the persona
   * caching note in docs/architecture.md.
   */
  systemBrief?: string;
}

/** Request body for persona generation. */
export interface PersonaGenerationRequest {
  segment: AudienceSegment;
  /** How many personas to generate for this segment. */
  count: number;
  /** Optional creator goal, so personas are generated with intent in mind. */
  creatorGoal?: string;
}
