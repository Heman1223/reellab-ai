import { randomUUID } from 'node:crypto';
import type { NextFunction, Request, Response } from 'express';

import { logger } from '../utils/logger';

/**
 * One structured log line per request, plus a request id that is echoed back
 * in the `X-Request-Id` header and attached to `req.requestId` so services can
 * correlate their own logs with the request that caused them.
 */
export function requestLogger(req: Request, res: Response, next: NextFunction): void {
  const requestId = (req.header('x-request-id') ?? randomUUID()).slice(0, 64);
  req.requestId = requestId;
  res.setHeader('X-Request-Id', requestId);

  const started = Date.now();

  res.on('finish', () => {
    logger.info('http_request', {
      requestId,
      method: req.method,
      path: req.originalUrl,
      status: res.statusCode,
      durationMs: Date.now() - started,
    });
  });

  next();
}
