/**
 * ReelLab shared contract — Counterfactual experiments.
 *
 * OWNER OF CHANGES: Developer 2 (generates variants) and Developer 1
 * (simulates them). Coordinate before changing.
 * Types only — no runtime code. See shared/README.md for the contract rules.
 */

import type { UnitScore } from './audience';
import type { ContentDNA } from './content';
import type { RunMetadata } from './simulation';

/** The lever the creator wants to pull. */
export type ModificationType =
  | 'hook'
  | 'duration'
  | 'cta'
  | 'tone'
  | 'pacing'
  | 'audience';

/**
 * One "what if". A variant is a *proposed* change plus the Content DNA that
 * change would produce — the simulation runs against `predictedContentDna`,
 * so no re-editing of the actual video is required.
 */
export interface Variant {
  id: string;
  label: string;
  /** What was changed, in the creator's language. */
  changeSummary: string;
  /** The concrete new asset, e.g. the rewritten hook line. */
  proposedChange: string;
  /** Content DNA as it would look after the change. Fed back into simulation. */
  predictedContentDna?: ContentDNA;
  /** Populated once the variant has been re-simulated. */
  simulationId?: string;
  /** Convenience mirror of the variant's `SimulationResult.overallScore`. */
  score?: UnitScore;
}

/** Head-to-head numbers for the original vs each variant. */
export interface VariantComparison {
  variantId: string;
  /** `overallScore` delta against the original, may be negative. */
  scoreDelta: number;
  /** Per-segment score deltas, keyed by `AudienceSegment.id`. */
  segmentDeltas: Record<string, number>;
  /** Segments that improved / regressed most, for the UI's highlight row. */
  biggestGainSegmentId?: string;
  biggestLossSegmentId?: string;
  confidence: UnitScore;
}

/** What the model recommends the creator actually do. */
export interface Recommendation {
  /** The winning variant, or `null` when the original is still best. */
  winningVariantId: string | null;
  reasoning: string;
  confidence: UnitScore;
  /** Explicit caveats — a low-confidence win must say so. */
  caveats: string[];
}

/**
 * A counterfactual experiment: one hypothesis, N variants, one comparison.
 * Created by `POST /api/v1/experiments`.
 */
export interface CounterfactualExperiment {
  experimentId: string;
  /** The baseline run everything is measured against. */
  originalSimulationId: string;
  /** The model's testable claim, e.g. "a question hook lifts 3s retention". */
  hypothesis: string;
  modificationType: ModificationType;
  variants: Variant[];
  comparison: VariantComparison[];
  recommendation: Recommendation;
  status: 'queued' | 'generating' | 'simulating' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
  metadata?: RunMetadata;
}

/** Request body for `POST /api/v1/experiments`. */
export interface ExperimentRequest {
  originalSimulationId: string;
  modificationType: ModificationType;
  /** Optional creator-supplied steer, e.g. "make it feel less salesy". */
  instruction?: string;
  /** How many variants to generate. Defaults to 2. */
  variantCount?: number;
}
