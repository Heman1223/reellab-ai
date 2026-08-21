import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

import multer from 'multer';

import { config } from '../config/env';
import { ApiError } from '../utils/ApiError';

/**
 * Reel upload handling.
 *
 * Disk storage, not memory — a 100 MB reel has no business sitting in the
 * Node heap. Files land in `UPLOAD_DIR` (gitignored) under a generated name;
 * the original filename is preserved in the request body, not on disk.
 *
 * This is infrastructure only. Nothing here inspects the video — that is
 * Developer 2's pipeline, reached through the AI service.
 */

const ACCEPTED_MIME_PREFIXES = ['video/'];
const ACCEPTED_EXTENSIONS = ['.mp4', '.mov', '.m4v', '.webm', '.avi', '.mkv'];

function ensureUploadDir(): string {
  fs.mkdirSync(config.uploadDir, { recursive: true });
  return config.uploadDir;
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => {
    try {
      cb(null, ensureUploadDir());
    } catch (error) {
      cb(error as Error, '');
    }
  },
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase() || '.mp4';
    cb(null, `${Date.now()}_${randomUUID().slice(0, 8)}${ext}`);
  },
});

export const uploadReel = multer({
  storage,
  limits: { fileSize: config.maxUploadBytes, files: 1 },
  fileFilter: (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    const mimeOk = ACCEPTED_MIME_PREFIXES.some((prefix) => file.mimetype.startsWith(prefix));
    const extOk = ACCEPTED_EXTENSIONS.includes(ext);

    if (mimeOk || extOk) return cb(null, true);

    cb(
      new ApiError(
        'UNSUPPORTED_VIDEO',
        `'${file.originalname}' is not a supported video. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}.`,
      ),
    );
  },
}).single('reel');
