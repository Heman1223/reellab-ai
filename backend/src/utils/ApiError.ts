/**
 * Every failure the API returns on purpose is an `ApiError`.
 *
 * The `code` is a stable machine-readable string the frontend can branch on;
 * the `message` is for humans. Anything thrown that is *not* an `ApiError` is
 * treated as a bug and reported as a 500 with a generic message.
 *
 * The codes below are the failure modes listed in the project brief. Handling
 * them is Developer 4's job; producing them is everyone's.
 */
export type ApiErrorCode =
  | 'BAD_REQUEST'
  | 'NOT_FOUND'
  | 'VALIDATION_FAILED'
  | 'UPLOAD_FAILED'
  | 'UNSUPPORTED_VIDEO'
  | 'EMPTY_TRANSCRIPT'
  | 'AI_SERVICE_UNAVAILABLE'
  | 'AI_TIMEOUT'
  | 'AI_MALFORMED_OUTPUT'
  | 'PERSONA_GENERATION_FAILED'
  | 'SIMULATION_PARTIAL'
  | 'DATABASE_UNAVAILABLE'
  | 'INTERNAL';

const DEFAULT_STATUS: Record<ApiErrorCode, number> = {
  BAD_REQUEST: 400,
  NOT_FOUND: 404,
  VALIDATION_FAILED: 422,
  UPLOAD_FAILED: 400,
  UNSUPPORTED_VIDEO: 415,
  EMPTY_TRANSCRIPT: 422,
  AI_SERVICE_UNAVAILABLE: 503,
  AI_TIMEOUT: 504,
  AI_MALFORMED_OUTPUT: 502,
  PERSONA_GENERATION_FAILED: 502,
  SIMULATION_PARTIAL: 207,
  DATABASE_UNAVAILABLE: 503,
  INTERNAL: 500,
};

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;
  readonly details?: unknown;

  constructor(code: ApiErrorCode, message: string, details?: unknown, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status ?? DEFAULT_STATUS[code];
    this.details = details;
    Error.captureStackTrace?.(this, ApiError);
  }

  static badRequest(message: string, details?: unknown): ApiError {
    return new ApiError('BAD_REQUEST', message, details);
  }

  static notFound(resource: string, id?: string): ApiError {
    return new ApiError('NOT_FOUND', id ? `${resource} '${id}' not found` : `${resource} not found`);
  }

  static validation(message: string, details?: unknown): ApiError {
    return new ApiError('VALIDATION_FAILED', message, details);
  }

  toJSON(): { code: ApiErrorCode; message: string; details?: unknown } {
    return { code: this.code, message: this.message, ...(this.details ? { details: this.details } : {}) };
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}
