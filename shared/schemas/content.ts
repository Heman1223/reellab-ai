/**
 * ReelLab shared contract — Content (the "Content DNA").
 *
 * OWNER OF CHANGES: Developer 2 (Multimodal AI).
 * Types only — no runtime code. See shared/README.md for the contract rules.
 */

import type { UnitScore } from './audience';

/** One visually/semantically distinct span of the reel. */
export interface Scene {
  index: number;
  startSeconds: number;
  endSeconds: number;
  /** What is happening, in one sentence. */
  description: string;
  /** Dominant on-screen action, e.g. "talking head", "b-roll", "text card". */
  shotType?: string;
  /** Visual energy of this scene, 0 (static) .. 1 (frenetic). */
  energy?: UnitScore;
}

/** Aggregate visual signals extracted from frames. */
export interface VisualFeatures {
  /** Average shot changes per second across the reel. */
  cutsPerSecond: number;
  /** Whether readable on-screen text / captions were detected. */
  hasOnScreenText: boolean;
  /** Whether a human face is present for most of the reel. */
  facePresence: UnitScore;
  dominantColors: string[];
  /** Subjective production quality, 0..1. */
  productionQuality?: UnitScore;
}

/** Aggregate audio signals extracted from the audio track. */
export interface AudioFeatures {
  hasSpeech: boolean;
  hasMusic: boolean;
  /** Speaking rate in words per minute; 0 when there is no speech. */
  wordsPerMinute: number;
  /** Perceived loudness / energy of the track, 0..1. */
  energy: UnitScore;
  language?: string;
}

/** The opening moments that decide whether a viewer stays. */
export interface Hook {
  /** Transcript or description of the first ~3 seconds. */
  text: string;
  /** How long the hook runs. */
  durationSeconds: number;
  /** Hook archetype, e.g. "question", "bold claim", "pattern interrupt". */
  type: string;
  /** Model's judgement of hook strength, 0..1. */
  strength: UnitScore;
}

/** The call to action, if any. */
export interface CallToAction {
  present: boolean;
  text?: string;
  /** Where in the reel the CTA lands, in seconds. */
  atSecond?: number;
  type?: 'follow' | 'comment' | 'share' | 'save' | 'link' | 'other';
}

/**
 * The multimodal understanding of a single reel.
 *
 * This is the hand-off point between Developer 2 (produces it) and
 * Developer 1 (consumes it in simulation). Both sides can work in parallel
 * against `data/mock_personas/content_dna.json`.
 */
export interface ContentDNA {
  videoId: string;
  durationSeconds: number;
  transcript: string;
  topic: string;
  hook: Hook;
  /** Overall tone, e.g. "instructional", "hype", "conversational". */
  tone: string;
  /** Dominant emotional register, e.g. "motivating", "reassuring". */
  emotion: string;
  scenes: Scene[];
  visualFeatures: VisualFeatures;
  audioFeatures: AudioFeatures;
  cta: CallToAction;
  /** Model-flagged issues, e.g. "transcript empty", "audio-only". */
  warnings?: string[];
}

/** A reel as tracked by the backend, independent of its analysis. */
export interface Reel {
  id: string;
  /** Original filename supplied by the creator. */
  filename: string;
  /** Server-side path or object reference. Never a raw browser blob URL. */
  storagePath: string;
  sizeBytes: number;
  durationSeconds?: number;
  uploadedAt: string;
  status: 'uploaded' | 'analyzing' | 'analyzed' | 'failed';
  contentDnaId?: string;
}
