/**
 * Frontend type surface.
 *
 * Re-exports the shared contracts so components import from one place, plus the
 * few types only the UI cares about.
 *
 * Do not define API shapes here — they belong in `shared/schemas/`. If you need
 * a field the backend does not send, that is a contract change, not a frontend
 * type.
 */

export type * from '@shared/schemas';

/** Where a page is in the fetch lifecycle. */
export type LoadState = 'idle' | 'loading' | 'ready' | 'error';

/** The success envelope every backend 2xx uses. */
export interface ApiEnvelope<T> {
  data: T;
  mock: boolean;
  requestId?: string;
}

/** The failure envelope every backend 4xx/5xx uses. */
export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
  requestId?: string;
}
