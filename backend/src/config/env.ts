import fs from 'node:fs';
import path from 'node:path';
import dotenv from 'dotenv';

import { REPO_ROOT } from './paths';

// A single `.env` at the repo root serves the backend, the AI service and
// docker-compose. A `backend/.env` overrides it when present.
for (const candidate of [path.join(REPO_ROOT, '.env'), path.join(REPO_ROOT, 'backend', '.env')]) {
  if (fs.existsSync(candidate)) dotenv.config({ path: candidate });
}

function str(key: string, fallback: string): string {
  const value = process.env[key];
  return value === undefined || value === '' ? fallback : value;
}

function int(key: string, fallback: number): number {
  const raw = process.env[key];
  if (raw === undefined || raw === '') return fallback;
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function bool(key: string, fallback: boolean): boolean {
  const raw = process.env[key];
  if (raw === undefined || raw === '') return fallback;
  return ['1', 'true', 'yes', 'on'].includes(raw.toLowerCase());
}

export const config = {
  env: str('NODE_ENV', 'development'),
  port: int('PORT', 4000),
  apiPrefix: '/api/v1',

  mongoUri: str('MONGODB_URI', 'mongodb://localhost:27017/reellab'),
  /** When false the server never attempts a Mongo connection at all. */
  mongoEnabled: bool('MONGODB_ENABLED', true),

  aiServiceUrl: str('AI_SERVICE_URL', 'http://localhost:8000'),
  aiRequestTimeoutMs: int('AI_REQUEST_TIMEOUT_SECONDS', 120) * 1000,

  frontendUrl: str('FRONTEND_URL', 'http://localhost:5173'),

  aiProvider: str('AI_PROVIDER', 'mock'),
  aiApiKey: str('AI_API_KEY', ''),
  multimodalModel: str('MULTIMODAL_MODEL', 'claude-sonnet-5'),
  reasoningModel: str('REASONING_MODEL', 'claude-opus-5'),

  uploadDir: path.isAbsolute(str('UPLOAD_DIR', 'uploads'))
    ? str('UPLOAD_DIR', 'uploads')
    : path.join(REPO_ROOT, str('UPLOAD_DIR', 'uploads')),
  maxUploadBytes: int('MAX_UPLOAD_MB', 500) * 1024 * 1024,

  logLevel: str('LOG_LEVEL', 'info'),
} as const;

export type AppConfig = typeof config;

export const isProduction = config.env === 'production';
export const isTest = config.env === 'test';
