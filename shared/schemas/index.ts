/**
 * Barrel re-export for the ReelLab shared contracts.
 *
 * Import from here in application code:
 *   import type { SimulationResult } from '@shared/schemas';
 *
 * Only ever add `export *` lines to this file — keeping it to re-exports is
 * what stops it from becoming a merge-conflict magnet.
 */

export type * from './audience';
export type * from './persona';
export type * from './content';
export type * from './simulation';
export type * from './result';
export type * from './experiment';
