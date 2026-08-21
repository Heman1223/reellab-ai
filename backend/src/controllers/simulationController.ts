import type { Request, Response } from 'express';

import {
  getSimulation,
  parseSimulationRequest,
  runSimulation,
} from '../services/simulationService';
import { ApiError } from '../utils/ApiError';
import { sendData } from '../utils/respond';

/** `POST /api/v1/simulation/run` */
export async function postRunSimulation(req: Request, res: Response): Promise<void> {
  const request = parseSimulationRequest(req.body);
  const resolved = await runSimulation(request, req.requestId);

  // 207 signals that some personas failed but the run is still usable — a
  // single failed persona must never invalidate a simulation.
  const status = resolved.data.status === 'partial' ? 207 : 201;
  sendData(req, res, resolved, status);
}

/** `GET /api/v1/simulation/:id` */
export async function getSimulationById(req: Request, res: Response): Promise<void> {
  const id = req.params.id;
  if (!id) throw ApiError.badRequest('Missing simulation id.');

  const result = getSimulation(id);
  sendData(req, res, { data: result, mock: result.metadata?.mock ?? false });
}
