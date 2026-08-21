import type { NextFunction, Request, Response } from 'express';
import { MulterError } from 'multer';

import { isProduction } from '../config/env';
import { ApiError, isApiError } from '../utils/ApiError';
import { logger } from '../utils/logger';

/** 404 for anything that reached the end of the router stack. */
export function notFoundHandler(req: Request, _res: Response, next: NextFunction): void {
  next(new ApiError('NOT_FOUND', `No route matches ${req.method} ${req.originalUrl}`));
}

/**
 * Centralised error handler. Every error the API returns is shaped the same:
 *
 *   { "error": { "code": "...", "message": "...", "details": ... }, "requestId": "..." }
 *
 * so the frontend has exactly one error shape to handle.
 */
export function errorHandler(
  error: unknown,
  req: Request,
  res: Response,
  _next: NextFunction,
): void {
  const apiError = normalise(error);

  const level = apiError.status >= 500 ? 'error' : 'warn';
  logger[level]('request_failed', {
    requestId: req.requestId,
    method: req.method,
    path: req.originalUrl,
    code: apiError.code,
    status: apiError.status,
    message: apiError.message,
    // Stack only for genuine bugs, and never in production responses.
    stack: apiError.status >= 500 && !isProduction ? apiError.stack : undefined,
  });

  res.status(apiError.status).json({
    error: apiError.toJSON(),
    requestId: req.requestId,
  });
}

function normalise(error: unknown): ApiError {
  if (isApiError(error)) return error;

  if (error instanceof MulterError) {
    const message =
      error.code === 'LIMIT_FILE_SIZE'
        ? 'The uploaded file is larger than MAX_UPLOAD_MB allows.'
        : `Upload failed: ${error.message}`;
    return new ApiError('UPLOAD_FAILED', message, { multerCode: error.code });
  }

  if (error instanceof SyntaxError && 'body' in error) {
    return ApiError.badRequest('Request body is not valid JSON.');
  }

  const message = error instanceof Error ? error.message : String(error);
  const internal = new ApiError(
    'INTERNAL',
    isProduction ? 'Something went wrong.' : message,
  );
  if (error instanceof Error && error.stack) internal.stack = error.stack;
  return internal;
}
