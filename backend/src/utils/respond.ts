import type { Request, Response } from 'express';

import type { ApiResponse } from '../types';

/**
 * The one success envelope for the whole API:
 *
 *   { "data": ..., "mock": boolean, "requestId": "..." }
 *
 * `mock` is not decoration. Half this API serves fixtures during the first
 * hours of the hackathon, and nobody should ever demo a fixture believing it
 * came from a model. The `X-ReelLab-Mock` header carries the same signal for
 * anyone reading a network tab.
 */
export function sendData<T>(
  req: Request,
  res: Response,
  payload: { data: T; mock: boolean },
  status = 200,
): void {
  res.setHeader('X-ReelLab-Mock', String(payload.mock));

  const body: ApiResponse<T> = {
    data: payload.data,
    mock: payload.mock,
    ...(req.requestId ? { requestId: req.requestId } : {}),
  };

  res.status(status).json(body);
}
