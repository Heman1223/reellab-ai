import type { Request, Response } from 'express';

import { getExperiment } from '../services/experimentService';
import { getSimulation } from '../services/simulationService';
import { ApiError, isApiError } from '../utils/ApiError';
import { sendData } from '../utils/respond';

/**
 * `GET /api/v1/results/:id`
 *
 * A convenience lookup for the frontend: the results dashboard has an id from
 * a URL and does not always know whether it belongs to a simulation or to an
 * experiment. This resolves either, tagging the payload with its `kind`.
 *
 * `GET /simulation/:id` and `GET /experiments/:id` remain the precise routes.
 */
export async function getResultById(req: Request, res: Response): Promise<void> {
  const id = req.params.id;
  if (!id) throw ApiError.badRequest('Missing result id.');

  try {
    const simulation = getSimulation(id);
    sendData(req, res, {
      data: { kind: 'simulation' as const, simulation },
      mock: simulation.metadata?.mock ?? false,
    });
    return;
  } catch (error) {
    if (!isApiError(error) || error.code !== 'NOT_FOUND') throw error;
  }

  try {
    const experiment = getExperiment(id);
    sendData(req, res, {
      data: { kind: 'experiment' as const, experiment },
      mock: experiment.metadata?.mock ?? false,
    });
    return;
  } catch (error) {
    if (!isApiError(error) || error.code !== 'NOT_FOUND') throw error;
  }

  throw ApiError.notFound('Result', id);
}
