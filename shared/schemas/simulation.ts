/**
 * ReelLab shared contract — Simulation inputs and per-persona output.
 *
 * OWNER OF CHANGES: Developer 1 (AI / Simulation Lead).
 * Types only — no runtime code. See shared/README.md for the contract rules.
 */

import type { UnitScore } from './audience';
import type { ContentDNA } from './content';

/** The terminal decision a persona makes about a reel. */
export type ViewerAction =
  | 'swipe'
  | 'watch'
  | 'complete'
  | 'like'
  | 'save'
  | 'share'
  | 'comment';

/** Lifecycle of a simulation run, polled by the frontend. */
export type SimulationStatus =
  | 'queued'
  | 'analyzing_content'
  | 'simulating_personas'
  | 'propagating'
  | 'reflecting'
  | 'completed'
  | 'failed'
  | 'partial';

/**
 * How much to spend on a run. The engine maps depth to persona count and
 * model tier — see the cost-aware notes in docs/architecture.md.
 */
export type SimulationDepth = 'quick' | 'standard' | 'deep';

/** Request body for `POST /api/v1/simulation/run`. */
export interface SimulationRequest {
  /** Reel to simulate. Either this or `contentDna` must be provided. */
  reelId?: string;
  /** Pre-computed Content DNA, so simulation can run without a real upload. */
  contentDna?: ContentDNA;
  /** Audience graph to simulate against. */
  graphId?: string;
  /** Explicit persona ids; when omitted the engine selects from the graph. */
  personaIds?: string[];
  depth?: SimulationDepth;
  /** Set when this run evaluates a counterfactual variant. */
  variantId?: string;
}

/**
 * One synthetic viewer's reaction to one piece of content.
 *
 * Probabilities are independent estimates, not a distribution — they do not
 * need to sum to 1. `action` is the single sampled outcome.
 */
export interface PersonaSimulationResult {
  personaId: string;
  watchProbability: UnitScore;
  completionProbability: UnitScore;
  likeProbability: UnitScore;
  saveProbability: UnitScore;
  shareProbability: UnitScore;
  commentProbability: UnitScore;
  /** Second at which the persona swiped away; `null` if they completed. */
  swipeTime: number | null;
  action: ViewerAction;
  /** The model's first-person justification — surfaced verbatim in the UI. */
  reason: string;
  /** How confident the model is in this prediction, 0..1. */
  confidence: UnitScore;
  /** Present when this persona failed to simulate; the run continues without it. */
  error?: string;
}

/**
 * One step of the propagation cascade. Wave 0 is the seeded audience;
 * each subsequent wave is reached through shares from the previous one.
 */
export interface PropagationWave {
  wave: number;
  /** Segments reached in this wave. */
  segmentIds: string[];
  /** Estimated viewers reached in this wave. */
  reach: number;
  /** Share of wave-N viewers that pass it on to wave N+1, 0..1. */
  passThroughRate: UnitScore;
  /** True when the cascade dies here. */
  terminated: boolean;
  /** Why it terminated or narrowed, in one sentence. */
  note?: string;
}

/**
 * Observability envelope attached to anything an AI produced.
 * Populated by the AI service, persisted by the backend, never invented
 * by the frontend. Keeps model/prompt/cost accounting honest.
 */
export interface RunMetadata {
  model: string;
  modelVersion?: string;
  promptVersion?: string;
  latencyMs?: number;
  inputTokens?: number;
  outputTokens?: number;
  estimatedCostUsd?: number;
  personaCount?: number;
  simulationDurationMs?: number;
  /** True when the value was produced by a fixture, not a model. */
  mock: boolean;
}
