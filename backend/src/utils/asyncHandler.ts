import type { NextFunction, Request, RequestHandler, Response } from 'express';

/**
 * Wrap an async route handler so a rejected promise reaches the centralised
 * error handler instead of hanging the request.
 *
 * Express 4 does not await handlers, so every `async` controller must be
 * wrapped. Forgetting this is the most common way to lose an error silently.
 */
export function asyncHandler(
  handler: (req: Request, res: Response, next: NextFunction) => Promise<unknown>,
): RequestHandler {
  return (req, res, next) => {
    handler(req, res, next).catch(next);
  };
}
