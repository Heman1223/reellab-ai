import fs from 'node:fs';
import path from 'node:path';

import { MOCK_DIR } from '../config/paths';
import { ApiError } from './ApiError';
import { logger } from './logger';

/**
 * Load development fixtures from `data/mock_personas/`.
 *
 * Fixtures live on disk rather than inline in TypeScript so the Python AI
 * service and the Node backend read the exact same bytes — see data/README.md.
 * Results are cached because these files never change while the process runs.
 */
const cache = new Map<string, unknown>();

export function loadFixture<T>(filename: string): T {
  const cached = cache.get(filename);
  if (cached !== undefined) return cached as T;

  const filePath = path.join(MOCK_DIR, filename);

  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf-8')) as T;
    cache.set(filename, parsed);
    return parsed;
  } catch (error) {
    logger.error('fixture_load_failed', { filePath, error: String(error) });
    throw new ApiError(
      'INTERNAL',
      `Could not load development fixture '${filename}'. Expected it at ${filePath}.`,
    );
  }
}

export const FIXTURES = {
  audienceGraph: 'audience_graph.json',
  personas: 'personas.json',
  contentDna: 'content_dna.json',
  simulationResult: 'simulation_result.json',
  counterfactualExperiment: 'counterfactual_experiment.json',
} as const;
