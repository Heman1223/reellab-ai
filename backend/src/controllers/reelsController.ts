import type { Request, Response } from 'express';

import { analyzeReel, registerUpload } from '../services/reelService';
import { ApiError } from '../utils/ApiError';
import { sendData } from '../utils/respond';

/** `POST /api/v1/reels/upload` — multipart, field name `reel`. */
export async function postUploadReel(req: Request, res: Response): Promise<void> {
  if (!req.file) {
    throw new ApiError('UPLOAD_FAILED', "No file received. Send a multipart field named 'reel'.");
  }

  const reel = registerUpload(req.file);
  sendData(req, res, { data: reel, mock: false }, 201);
}

/** `POST /api/v1/reels/analyze` — body: `{ reelId }` or `{ videoPath }`. */
export async function postAnalyzeReel(req: Request, res: Response): Promise<void> {
  const body = (req.body ?? {}) as { reelId?: string; videoPath?: string };
  const resolved = await analyzeReel(body, req.requestId);
  sendData(req, res, resolved, 200);
}
