import { useCallback, useState } from 'react';

import { ApiError } from '@/services/apiClient';
import type { ApiResult } from '@/services/apiClient';
import type { LoadState } from '@/types';

/**
 * Run an async API call and track its state.
 *
 * Deliberately not a data-fetching library. Every page in ReelLab either loads
 * once or is triggered by a button, and this covers both in thirty lines.
 */
export interface AsyncState<T> {
  state: LoadState;
  data: T | null;
  /** True when the payload came from a fixture rather than a model. */
  mock: boolean;
  error: string | null;
  errorCode: string | null;
}

export function useAsync<Args extends unknown[], T>(
  fn: (...args: Args) => Promise<ApiResult<T>>,
) {
  const [result, setResult] = useState<AsyncState<T>>({
    state: 'idle',
    data: null,
    mock: false,
    error: null,
    errorCode: null,
  });

  const run = useCallback(
    async (...args: Args): Promise<T | null> => {
      setResult((previous) => ({ ...previous, state: 'loading', error: null, errorCode: null }));

      try {
        const { data, mock } = await fn(...args);
        setResult({ state: 'ready', data, mock, error: null, errorCode: null });
        return data;
      } catch (error) {
        const message =
          error instanceof ApiError
            ? error.message
            : error instanceof Error
              ? error.message
              : 'Something went wrong.';
        const code = error instanceof ApiError ? error.code : 'UNKNOWN';

        setResult({ state: 'error', data: null, mock: false, error: message, errorCode: code });
        return null;
      }
    },
    [fn],
  );

  const reset = useCallback(() => {
    setResult({ state: 'idle', data: null, mock: false, error: null, errorCode: null });
  }, []);

  return { ...result, run, reset };
}
