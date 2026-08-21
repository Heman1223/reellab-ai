import type { ApiEnvelope, ApiErrorBody } from '@/types';

/**
 * The HTTP boundary.
 *
 * One place that knows about the envelope, the error shape and the base URL.
 * Components never call `fetch`.
 */

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:4000/api/v1';

/** When true, `services/reellabApi.ts` serves local mocks instead of calling the API. */
export const USE_MOCKS: boolean = import.meta.env.VITE_USE_MOCKS !== 'false';

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: unknown;

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

/** Result of a call, carrying whether the backend served a fixture. */
export interface ApiResult<T> {
  data: T;
  mock: boolean;
}

async function request<T>(
  method: 'GET' | 'POST',
  path: string,
  body?: unknown,
): Promise<ApiResult<T>> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new ApiError(
      'NETWORK_ERROR',
      `Could not reach the API at ${API_BASE_URL}. Is the backend running?`,
      0,
      error,
    );
  }

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const errorBody = payload as ApiErrorBody | null;
    throw new ApiError(
      errorBody?.error?.code ?? 'UNKNOWN',
      errorBody?.error?.message ?? `Request failed with ${response.status}.`,
      response.status,
      errorBody?.error?.details,
    );
  }

  const envelope = payload as ApiEnvelope<T>;
  return { data: envelope.data, mock: envelope.mock ?? false };
}

export const apiClient = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),

  /** Multipart upload — the one call that does not send JSON. */
  async upload<T>(path: string, file: File, field = 'reel'): Promise<ApiResult<T>> {
    const form = new FormData();
    form.append(field, file);

    const response = await fetch(`${API_BASE_URL}${path}`, { method: 'POST', body: form });
    const payload: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      const errorBody = payload as ApiErrorBody | null;
      throw new ApiError(
        errorBody?.error?.code ?? 'UPLOAD_FAILED',
        errorBody?.error?.message ?? 'Upload failed.',
        response.status,
      );
    }

    const envelope = payload as ApiEnvelope<T>;
    return { data: envelope.data, mock: envelope.mock ?? false };
  },
};
