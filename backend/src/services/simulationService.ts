import { randomUUID } from 'node:crypto';

import type { SimulationRequest } from '@shared/schemas/simulation';
import type { SimulationResult } from '@shared/schemas/result';

import { ApiError } from '../utils/ApiError';
import { FIXTURES, loadFixture } from '../utils/fixtures';
import { mockMetadata } from '../utils/observability';
import { AI_ENDPOINTS, aiClient } from './aiClient';
import { withFixtureFallback } from './fallback';
import { COLLECTIONS, memoryStore } from './store';
import type { Resolved } from './fallback';

/**
 * Simulation orchestration.
 *
 * Deterministic work only: validate, assign an id, call the AI service, persist
 * the result, hand it back. Every decision inside the simulation — how each
 * persona reacts, why the cascade stops, what the bottleneck is — belongs to
 * the AI service.
 *
 * Runs are synchronous for now. If a real run grows past a few seconds,
 * Developer 4 turns `runSimulation` into a job that returns
 * `{ simulationId, status: 'queued' }` immediately; the frontend already polls
 * `GET /simulation/:id`, so nothing else has to change.
 */

export function parseSimulationRequest(body: unknown): SimulationRequest {
  if (typeof body !== 'object' || body === null) {
    throw ApiError.validation('Request body must be a JSON object.');
  }

  const raw = body as Record<string, unknown>;

  if (!raw.reelId && !raw.contentDna) {
    throw ApiError.validation('Provide either `reelId` or `contentDna`.');
  }

  const depth = raw.depth;
  if (depth !== undefined && !['quick', 'standard', 'deep'].includes(String(depth))) {
    throw ApiError.validation("`depth` must be one of 'quick', 'standard', 'deep'.");
  }

  return raw as unknown as SimulationRequest;
}

export async function runSimulation(
  request: SimulationRequest,
  requestId?: string,
): Promise<Resolved<SimulationResult>> {
  const simulationId = `sim_${randomUUID().slice(0, 8)}`;
  const startedAt = new Date().toISOString();

  const resolved = await withFixtureFallback<SimulationResult>(
    'simulation.run',
    () =>
      aiClient.post<SimulationResult>(
        AI_ENDPOINTS.simulationRun,
        { ...request, simulationId },
        { requestId },
      ),
    () => ({
      ...loadFixture<SimulationResult>(FIXTURES.simulationResult),
      simulationId,
      ...(request.reelId ? { reelId: request.reelId } : {}),
      ...(request.variantId ? { variantId: request.variantId } : {}),
      createdAt: startedAt,
      completedAt: new Date().toISOString(),
      metadata: mockMetadata({ personaCount: 5 }),
    }),
  );

  const stored: SimulationResult = { ...resolved.data, simulationId };
  memoryStore.put(COLLECTIONS.simulations, simulationId, stored);

  return { data: stored, mock: resolved.mock };
}

export function getSimulation(simulationId: string): SimulationResult {
  const stored = memoryStore.get<SimulationResult>(COLLECTIONS.simulations, simulationId);
  if (stored) return stored;

  // The fixture id is served so a frontend developer can hit
  // `GET /api/v1/simulation/sim_001` on a cold server and get a full result.
  const fixture = loadFixture<SimulationResult>(FIXTURES.simulationResult);
  if (fixture.simulationId === simulationId) return fixture;

  throw ApiError.notFound('Simulation', simulationId);
}
