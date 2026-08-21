/**
 * ReelLab shared contract — aggregated simulation results.
 *
 * OWNER OF CHANGES: Developer 1 (AI / Simulation Lead), consumed heavily by
 * Developer 3 (frontend). Additive changes only.
 * Types only — no runtime code. See shared/README.md for the contract rules.
 */

import type { UnitScore } from './audience';
import type {
  PersonaSimulationResult,
  PropagationWave,
  RunMetadata,
  SimulationStatus,
} from './simulation';

/** Rolled-up performance for a single audience segment. */
export interface AudienceSegmentResult {
  segmentId: string;
  segmentName: string;
  /** Segment-level score, 0..1. */
  score: UnitScore;
  /** Mean of the per-persona probabilities within this segment. */
  averageWatchProbability: UnitScore;
  averageCompletionProbability: UnitScore;
  shareRate: UnitScore;
  saveRate: UnitScore;
  /** How many personas were actually simulated for this segment. */
  personaCount: number;
  confidence: UnitScore;
  /** `strong` and `weak` drive the "performs well / poorly" UI split. */
  verdict: 'strong' | 'mixed' | 'weak';
}

/** Where the reel loses the audience, and the model's explanation why. */
export interface Bottleneck {
  id: string;
  /** Stage of the funnel that breaks. */
  stage: 'hook' | 'retention' | 'payoff' | 'cta' | 'propagation';
  /** Segments most affected. Empty means it is global. */
  segmentIds: string[];
  /** Plain-language description of what breaks. */
  description: string;
  /** The model's causal hypothesis — this is what the creator acts on. */
  likelyCause: string;
  /** Estimated impact if fixed, 0..1. */
  severity: UnitScore;
  confidence: UnitScore;
}

/** A non-fatal problem the creator should know about. */
export interface Warning {
  code: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
}

/**
 * The complete output of one simulation run.
 * `status: 'partial'` is normal and expected — a few failed personas must
 * never invalidate the run.
 */
export interface SimulationResult {
  simulationId: string;
  status: SimulationStatus;
  /** Reel or variant this result describes. */
  reelId?: string;
  variantId?: string;
  graphId?: string;
  /** Headline score, 0..1. One output among many — not the product. */
  overallScore: UnitScore;
  /** Aggregate confidence across the run, 0..1. */
  confidence: UnitScore;
  /** Every persona-level reaction. */
  audienceResults: PersonaSimulationResult[];
  propagationWaves: PropagationWave[];
  audienceSegmentResults: AudienceSegmentResult[];
  bottlenecks: Bottleneck[];
  warnings: Warning[];
  createdAt: string;
  completedAt?: string;
  metadata?: RunMetadata;
}
