import type { RunMetadata } from '@shared/schemas/simulation';

import { logger } from './logger';

/**
 * Minimal cost/latency accounting.
 *
 * The brief asks that we be *able* to track model, prompt version, latency,
 * tokens, cost, persona count, duration and confidence — not that we build an
 * observability platform. So: one timer helper and one log line. When someone
 * wants dashboards later, they parse the JSON logs.
 */

export interface TimedResult<T> {
  value: T;
  latencyMs: number;
}

export async function timed<T>(fn: () => Promise<T>): Promise<TimedResult<T>> {
  const started = Date.now();
  const value = await fn();
  return { value, latencyMs: Date.now() - started };
}

export interface AiCallRecord extends Partial<RunMetadata> {
  operation: string;
  success: boolean;
}

/**
 * Emit one structured line per AI call. Keep the field names identical to
 * `RunMetadata` so logs and persisted results line up.
 */
export function recordAiCall(record: AiCallRecord): void {
  logger.info('ai_call', {
    event: 'ai_call',
    operation: record.operation,
    success: record.success,
    model: record.model,
    modelVersion: record.modelVersion,
    promptVersion: record.promptVersion,
    latencyMs: record.latencyMs,
    inputTokens: record.inputTokens,
    outputTokens: record.outputTokens,
    estimatedCostUsd: record.estimatedCostUsd,
    personaCount: record.personaCount,
    mock: record.mock ?? false,
  });
}

/** Metadata stamped on any response served from a fixture. */
export function mockMetadata(overrides: Partial<RunMetadata> = {}): RunMetadata {
  return {
    model: 'fixture',
    promptVersion: 'n/a',
    latencyMs: 0,
    mock: true,
    ...overrides,
  };
}
