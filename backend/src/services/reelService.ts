import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

import type { ContentDNA, Reel } from '@shared/schemas/content';

import { ApiError } from '../utils/ApiError';
import { FIXTURES, loadFixture } from '../utils/fixtures';
import { AI_ENDPOINTS, aiClient } from './aiClient';
import { withFixtureFallback } from './fallback';
import { COLLECTIONS, memoryStore } from './store';
import type { Resolved } from './fallback';

/**
 * Reel intake and analysis hand-off.
 *
 * The backend owns the file; the AI service owns the understanding. We pass a
 * *path*, never the bytes — Developer 2's pipeline reads from disk, which keeps
 * large payloads out of the HTTP hop between the two services.
 */

export function registerUpload(file: Express.Multer.File): Reel {
  const reel: Reel = {
    id: `reel_${randomUUID().slice(0, 8)}`,
    filename: file.originalname,
    storagePath: file.path,
    sizeBytes: file.size,
    uploadedAt: new Date().toISOString(),
    status: 'uploaded',
  };

  return memoryStore.put(COLLECTIONS.reels, reel.id, reel);
}

export function getReel(reelId: string): Reel {
  const reel = memoryStore.get<Reel>(COLLECTIONS.reels, reelId);
  if (!reel) throw ApiError.notFound('Reel', reelId);
  return reel;
}

/**
 * Run multimodal analysis. Accepts either a previously uploaded `reelId` or a
 * raw `videoPath` so Developer 2 can point it at `data/sample_reels/` without
 * going through an upload.
 */
export async function analyzeReel(
  input: { reelId?: string; videoPath?: string },
  requestId?: string,
): Promise<Resolved<ContentDNA>> {
  let videoPath = input.videoPath;
  let reel: Reel | undefined;

  if (input.reelId) {
    reel = getReel(input.reelId);
    videoPath = path.resolve(reel.storagePath);
  } else if (videoPath) {
    videoPath = path.resolve(videoPath);
  }

  if (!videoPath) {
    throw ApiError.validation('Provide either `reelId` or `videoPath`.');
  }

  // Only enforce existence for a real analysis run. In mock mode the path is
  // allowed to be fictional so the frontend can drive the flow end to end.
  if (!fs.existsSync(videoPath) && !isMockMode()) {
    throw new ApiError('UPLOAD_FAILED', `No file at '${videoPath}'.`);
  }

  if (reel) {
    reel.status = 'analyzing';
    memoryStore.put(COLLECTIONS.reels, reel.id, reel);
  }

  try {
    const resolved = await withFixtureFallback<ContentDNA>(
      'video.analyze',
      () => aiClient.post<ContentDNA>(AI_ENDPOINTS.videoAnalyze, { videoPath }, { requestId }),
      () => ({
        ...loadFixture<ContentDNA>(FIXTURES.contentDna),
        ...(reel ? { videoId: reel.id } : {}),
      }),
    );

    if (reel) {
      reel.status = 'analyzed';
      reel.durationSeconds = resolved.data.durationSeconds;
      memoryStore.put(COLLECTIONS.reels, reel.id, reel);
    }

    return resolved;
  } catch (error) {
    if (reel) {
      reel.status = 'failed';
      memoryStore.put(COLLECTIONS.reels, reel.id, reel);
    }
    throw error;
  }
}

function isMockMode(): boolean {
  return process.env.AI_PROVIDER === 'mock' || process.env.AI_PROVIDER === undefined;
}
