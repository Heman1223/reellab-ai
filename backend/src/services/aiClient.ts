import { config } from '../config/env';
import { ApiError } from '../utils/ApiError';
import { logger } from '../utils/logger';
import { recordAiCall } from '../utils/observability';

/**
 * The one place the Node backend talks to the Python AI service.
 *
 * Everything about the AI boundary lives here: timeouts, failure translation,
 * and cost/latency logging. Services never call `fetch` themselves.
 *
 * Failure is expected, not exceptional. `callAi` throws typed `ApiError`s that
 * callers can catch to fall back to fixtures — which is exactly how the
 * mock-first workflow survives an AI service that is not running yet.
 */

export interface AiCallOptions {
  /** Overrides the default timeout for a single call. */
  timeoutMs?: number;
  /** Correlation id forwarded to the AI service logs. */
  requestId?: string;
}

async function request<T>(
  method: 'GET' | 'POST',
  endpoint: string,
  body: unknown,
  options: AiCallOptions = {},
): Promise<T> {
  const url = `${config.aiServiceUrl}${endpoint}`;
  const timeoutMs = options.timeoutMs ?? config.aiRequestTimeoutMs;
  const started = Date.now();

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(options.requestId ? { 'X-Request-Id': options.requestId } : {}),
      },
      body: method === 'POST' ? JSON.stringify(body ?? {}) : undefined,
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (error) {
    const latencyMs = Date.now() - started;
    recordAiCall({ operation: endpoint, success: false, latencyMs });

    const isTimeout = error instanceof Error && error.name === 'TimeoutError';
    if (isTimeout) {
      throw new ApiError('AI_TIMEOUT', `AI service did not respond within ${timeoutMs}ms.`, {
        endpoint,
      });
    }
    throw new ApiError(
      'AI_SERVICE_UNAVAILABLE',
      `Could not reach the AI service at ${config.aiServiceUrl}.`,
      { endpoint, cause: error instanceof Error ? error.message : String(error) },
    );
  }

  const latencyMs = Date.now() - started;

  if (!response.ok) {
    recordAiCall({ operation: endpoint, success: false, latencyMs });
    
    let detail = '';
    let aiMessage = '';
    let aiCode: string | undefined = undefined;
    
    try {
      const text = await response.text();
      detail = text.slice(0, 500);
      const json = JSON.parse(text);
      if (json.error) {
        aiMessage = json.error.message;
        aiCode = json.error.code;
      }
    } catch {}

    let code = 'AI_MALFORMED_OUTPUT';
    let status = 502;

    if (response.status === 429 || aiCode === 'AI_QUOTA_EXHAUSTED') {
      code = 'AI_QUOTA_EXHAUSTED';
      status = 429;
    } else if (response.status === 503 || aiCode === 'AI_SERVICE_UNAVAILABLE') {
      code = 'AI_SERVICE_UNAVAILABLE';
      status = 503;
    } else if (response.status >= 500) {
      code = 'AI_SERVICE_UNAVAILABLE';
      status = 503;
    }
    
    // We explicitly cast the code so it aligns with ApiError types.
    // If the frontend needs to know it's a quota issue, we can just pass AI_SERVICE_UNAVAILABLE if it's not registered.
    throw new ApiError(
      // @ts-expect-error AI_QUOTA_EXHAUSTED is dynamic here
      code,
      aiMessage || `AI service returned ${response.status} for ${endpoint}.`,
      { body: detail, aiCode },
      status,
    );
  }

  let parsed: unknown;
  try {
    parsed = await response.json();
  } catch {
    recordAiCall({ operation: endpoint, success: false, latencyMs });
    throw new ApiError('AI_MALFORMED_OUTPUT', `AI service returned non-JSON for ${endpoint}.`);
  }

  const envelope = parsed as { data?: T; mock?: boolean; metadata?: Record<string, unknown> };
  recordAiCall({
    operation: endpoint,
    success: true,
    latencyMs,
    mock: envelope.mock ?? false,
    ...(envelope.metadata ?? {}),
  });

  // The AI service always wraps its payload in `{ data, mock, metadata }`.
  return (envelope.data ?? (parsed as T)) as T;
}

export const aiClient = {
  post: <T>(endpoint: string, body: unknown, options?: AiCallOptions) =>
    request<T>('POST', endpoint, body, options),

  get: <T>(endpoint: string, options?: AiCallOptions) =>
    request<T>('GET', endpoint, undefined, options),

  /**
   * Cheap liveness probe used by `/api/v1/health`. Never throws — an AI service
   * that is down is a normal state during the first hours of the hackathon.
   */
  async isHealthy(timeoutMs = 1500): Promise<boolean> {
    try {
      const response = await fetch(`${config.aiServiceUrl}/health`, {
        signal: AbortSignal.timeout(timeoutMs),
      });
      return response.ok;
    } catch (error) {
      logger.debug('ai_health_check_failed', { error: String(error) });
      return false;
    }
  },
};

/** Endpoint paths exposed by the Python service. Keep in sync with `ai/main.py`. */
export const AI_ENDPOINTS = {
  audienceDiscover: '/ai/audience/discover',
  personasGenerate: '/ai/personas/generate',
  videoAnalyze: '/ai/video/analyze',
  simulationRun: '/ai/simulation/run',
  counterfactualGenerate: '/ai/counterfactual/generate',
  evaluationRun: '/ai/evaluation/run',
} as const;
