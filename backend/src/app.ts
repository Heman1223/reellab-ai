import cors from 'cors';
import express from 'express';
import type { Express } from 'express';

import { config } from './config/env';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import { requestLogger } from './middleware/requestLogger';
import routes from './routes';

// Side-effect import: augments Express's `Request` with `requestId`.
import './types';

/**
 * Build the Express app.
 *
 * Kept separate from `server.ts` so tests can mount the app with Supertest
 * without opening a port or touching MongoDB.
 */
export function createApp(): Express {
  const app = express();

  app.disable('x-powered-by');

  app.use(
    cors({
      // The dev frontend plus anything explicitly configured. Tighten before
      // any public deployment.
      origin: [config.frontendUrl, 'http://localhost:5173', 'http://127.0.0.1:5173'],
      credentials: true,
      exposedHeaders: ['X-Request-Id', 'X-ReelLab-Mock'],
    }),
  );

  app.use(express.json({ limit: '2mb' }));
  app.use(express.urlencoded({ extended: true }));
  app.use(requestLogger);

  app.get('/', (_req, res) => {
    res.json({
      service: 'reellab-backend',
      tagline: 'Experiment Before You Publish.',
      api: config.apiPrefix,
      health: `${config.apiPrefix}/health`,
    });
  });

  app.use(config.apiPrefix, routes);

  // Order matters: 404 first, then the error handler last.
  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}
