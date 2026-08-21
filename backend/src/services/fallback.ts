import { config } from '../config/env';
import { isApiError } from '../utils/ApiError';
import { logger } from '../utils/logger';

/**
 * Mock-first execution.
 *
 * Try the real AI service; if it is unreachable, times out, or returns
 * something malformed, serve the development fixture instead and say so.
 * Every service in this folder is built on this one function, which is what
 * makes "the backend works before the AI service exists" true rather than
 * aspirational.
 *
 * Only *transport-level* AI failures fall back. A genuine 4xx from the AI
 * service (bad input) propagates, because hiding it would mean shipping a bug
 * behind a plausible-looking mock.
 */

export interface Resolved<T> {
  data: T;
  mock: boolean;
}

const FALLBACK_CODES = new Set(['AI_SERVICE_UNAVAILABLE', 'AI_TIMEOUT', 'AI_MALFORMED_OUTPUT']);

export async function withFixtureFallback<T>(
  operation: string,
  callAi: () => Promise<T>,
  fixture: () => T,
): Promise<Resolved<T>> {
  // `AI_PROVIDER=mock` short-circuits without even attempting a network call.
  if (config.aiProvider === 'mock') {
    logger.debug('serving_fixture', { operation, reason: 'AI_PROVIDER=mock' });
    return { data: fixture(), mock: true };
  }

  try {
    return { data: await callAi(), mock: false };
  } catch (error) {
    if (isApiError(error) && FALLBACK_CODES.has(error.code)) {
      logger.warn('ai_unavailable_serving_fixture', {
        operation,
        code: error.code,
        message: error.message,
      });
      return { data: fixture(), mock: true };
    }
    throw error;
  }
}
