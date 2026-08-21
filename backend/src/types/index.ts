/**
 * Backend-internal types.
 *
 * Anything that crosses a service boundary belongs in `shared/schemas/`, not
 * here. This file is for shapes only the Node app cares about.
 */

/** Standard success envelope. Every 2xx JSON body has this shape. */
export interface ApiResponse<T> {
  data: T;
  /** True when the payload came from a fixture rather than a model. */
  mock: boolean;
  requestId?: string;
}

/** Standard failure envelope, produced by the central error handler. */
export interface ApiErrorResponse {
  error: { code: string; message: string; details?: unknown };
  requestId?: string;
}

export {};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      /** Correlation id assigned by `requestLogger`. */
      requestId?: string;
    }
  }
}
