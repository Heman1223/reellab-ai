import { randomUUID } from 'node:crypto';

import type {
  CounterfactualExperiment,
  ExperimentRequest,
  ModificationType,
} from '@shared/schemas/experiment';

import { ApiError } from '../utils/ApiError';
import { FIXTURES, loadFixture } from '../utils/fixtures';
import { mockMetadata } from '../utils/observability';
import { AI_ENDPOINTS, aiClient } from './aiClient';
import { withFixtureFallback } from './fallback';
import { COLLECTIONS, memoryStore } from './store';
import { getSimulation } from './simulationService';
import type { Resolved } from './fallback';

const MODIFICATION_TYPES: ModificationType[] = [
  'hook',
  'duration',
  'cta',
  'tone',
  'pacing',
  'audience',
];

export function parseExperimentRequest(body: unknown): ExperimentRequest {
  if (typeof body !== 'object' || body === null) {
    throw ApiError.validation('Request body must be a JSON object.');
  }

  const raw = body as Record<string, unknown>;

  if (typeof raw.originalSimulationId !== 'string' || raw.originalSimulationId.trim() === '') {
    throw ApiError.validation('`originalSimulationId` is required.');
  }

  if (!MODIFICATION_TYPES.includes(raw.modificationType as ModificationType)) {
    throw ApiError.validation(
      `\`modificationType\` must be one of: ${MODIFICATION_TYPES.join(', ')}.`,
    );
  }

  const variantCount = Number(raw.variantCount ?? 2);
  if (!Number.isInteger(variantCount) || variantCount < 1 || variantCount > 5) {
    throw ApiError.validation('`variantCount` must be an integer between 1 and 5.');
  }

  return {
    originalSimulationId: raw.originalSimulationId.trim(),
    modificationType: raw.modificationType as ModificationType,
    ...(typeof raw.instruction === 'string' ? { instruction: raw.instruction } : {}),
    variantCount,
  };
}

/**
 * Counterfactual experiment.
 *
 * Two AI responsibilities meet here and they belong to different developers:
 * Developer 2 generates the variants, Developer 1 re-simulates them. The
 * backend's job is to make sure the baseline exists, hand both jobs to the AI
 * service, and store what comes back.
 */
export async function createExperiment(
  request: ExperimentRequest,
  requestId?: string,
): Promise<Resolved<CounterfactualExperiment>> {
  // Fail loudly if the baseline is missing — comparing against nothing is worse
  // than not comparing.
  getSimulation(request.originalSimulationId);

  const experimentId = `exp_${randomUUID().slice(0, 8)}`;

  const resolved = await withFixtureFallback<CounterfactualExperiment>(
    'counterfactual.generate',
    () =>
      aiClient.post<CounterfactualExperiment>(
        AI_ENDPOINTS.counterfactualGenerate,
        { ...request, experimentId },
        { requestId },
      ),
    () => ({
      ...loadFixture<CounterfactualExperiment>(FIXTURES.counterfactualExperiment),
      experimentId,
      originalSimulationId: request.originalSimulationId,
      modificationType: request.modificationType,
      createdAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      metadata: mockMetadata(),
    }),
  );

  const stored: CounterfactualExperiment = { ...resolved.data, experimentId };
  memoryStore.put(COLLECTIONS.experiments, experimentId, stored);

  return { data: stored, mock: resolved.mock };
}

export function getExperiment(experimentId: string): CounterfactualExperiment {
  const stored = memoryStore.get<CounterfactualExperiment>(COLLECTIONS.experiments, experimentId);
  if (stored) return stored;

  const fixture = loadFixture<CounterfactualExperiment>(FIXTURES.counterfactualExperiment);
  if (fixture.experimentId === experimentId) return fixture;

  throw ApiError.notFound('Experiment', experimentId);
}
