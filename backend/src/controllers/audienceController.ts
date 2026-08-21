import type { Request, Response } from 'express';

import { discoverAudience, parseAudienceRequest } from '../services/audienceService';
import { sendData } from '../utils/respond';

/** `POST /api/v1/audience/discover` */
export async function postDiscoverAudience(req: Request, res: Response): Promise<void> {
  const request = parseAudienceRequest(req.body);
  const resolved = await discoverAudience(request, req.requestId);
  sendData(req, res, resolved, 201);
}
