import { createApp } from './app';
import { config } from './config/env';
import { connectDatabase, disconnectDatabase } from './config/db';
import { logger } from './utils/logger';

/**
 * Process entry point.
 *
 * Startup order is deliberate: the HTTP listener comes up first, then we try
 * the database. A missing MongoDB degrades the API; it must never stop it from
 * booting.
 */
async function main(): Promise<void> {
  const app = createApp();

  const server = app.listen(config.port, () => {
    logger.info('server_started', {
      port: config.port,
      env: config.env,
      api: `http://localhost:${config.port}${config.apiPrefix}`,
      aiServiceUrl: config.aiServiceUrl,
      aiProvider: config.aiProvider,
    });
  });

  const dbStatus = await connectDatabase();
  if (dbStatus !== 'connected') {
    logger.warn('running_without_database', {
      status: dbStatus,
      note: 'Reads and writes fall back to an in-process store. Restart loses state.',
    });
  }

  const shutdown = (signal: string) => {
    logger.info('shutdown_started', { signal });
    server.close(() => {
      void disconnectDatabase().finally(() => {
        logger.info('shutdown_complete');
        process.exit(0);
      });
    });

    // Do not hang forever on a stuck connection.
    setTimeout(() => process.exit(1), 8000).unref();
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));

  process.on('unhandledRejection', (reason) => {
    logger.error('unhandled_rejection', { reason: String(reason) });
  });
  process.on('uncaughtException', (error) => {
    logger.error('uncaught_exception', { error: error.message, stack: error.stack });
    process.exit(1);
  });
}

void main();
