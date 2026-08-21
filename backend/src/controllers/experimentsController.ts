import type { Request, Response } from 'express';

import {
  createExperiment,
  getExperiment,
  parseExperimentRequest,
} from '../services/experimentService';
import { ApiError } from '../utils/ApiError';
import { sendData } from '../utils/respond';

/** `POST /api/v1/experiments` */
export async function postCreateExperiment(req: Request, res: Response): Promise<void> {
  const request = parseExperimentRequest(req.body);
  const resolved = await createExperiment(request, req.requestId);
  sendData(req, res, resolved, 201);
}

/** `GET /api/v1/experiments/:id` */
export async function getExperimentById(req: Request, res: Response): Promise<void> {
  const id = req.params.id;
  if (!id) throw ApiError.badRequest('Missing experiment id.');

  const experiment = getExperiment(id);
  sendData(req, res, { data: experiment, mock: experiment.metadata?.mock ?? false });
}
