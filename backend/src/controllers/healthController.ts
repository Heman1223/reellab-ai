import type { Request, Response } from 'express';

import { config } from '../config/env';
import { getDbStatus, isDbConnected } from '../config/db';
import { aiClient } from '../services/aiClient';

/**
 * `GET /api/v1/health`
 *
 * Always answers 200 as long as the process is alive. A degraded dependency is
 * reported in the body, not by failing the probe — the API is genuinely usable
 * with both Mongo and the AI service down, and a health check that lies about
 * that would send people debugging the wrong thing.
 */
export async function getHealth(_req: Request, res: Response): Promise<void> {
  const aiReachable = await aiClient.isHealthy();

  res.status(200).json({
    status: 'ok',
    service: 'reellab-backend',
    version: '0.1.0',
    env: config.env,
    uptimeSeconds: Math.round(process.uptime()),
    dependencies: {
      mongodb: {
        status: getDbStatus(),
        connected: isDbConnected(),
      },
      aiService: {
        url: config.aiServiceUrl,
        reachable: aiReachable,
      },
    },
    ai: {
      provider: config.aiProvider,
      multimodalModel: config.multimodalModel,
      reasoningModel: config.reasoningModel,
      /** True when responses come from fixtures rather than a model. */
      mockMode: config.aiProvider === 'mock' || config.aiApiKey === '',
    },
    timestamp: new Date().toISOString(),
  });
}
