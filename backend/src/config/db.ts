import mongoose from 'mongoose';

import { logger } from '../utils/logger';
import { config } from './env';

/**
 * MongoDB connection.
 *
 * The server must start whether or not Mongo is reachable. During a 24-hour
 * hackathon a developer without a local Mongo should still be able to run the
 * API against fixtures, and a dead database should degrade the product rather
 * than take the process down.
 */

export type DbStatus = 'disabled' | 'connecting' | 'connected' | 'unavailable';

let status: DbStatus = 'disabled';

export function getDbStatus(): DbStatus {
  return status;
}

export function isDbConnected(): boolean {
  return mongoose.connection.readyState === 1;
}

export async function connectDatabase(): Promise<DbStatus> {
  if (!config.mongoEnabled) {
    logger.warn('db_disabled', { reason: 'MONGODB_ENABLED=false' });
    status = 'disabled';
    return status;
  }

  status = 'connecting';

  mongoose.connection.on('disconnected', () => {
    status = 'unavailable';
    logger.warn('db_disconnected');
  });
  mongoose.connection.on('reconnected', () => {
    status = 'connected';
    logger.info('db_reconnected');
  });
  mongoose.connection.on('error', (err) => {
    status = 'unavailable';
    logger.warn('db_error', { error: err instanceof Error ? err.message : String(err) });
  });

  try {
    await mongoose.connect(config.mongoUri, {
      // Fail fast instead of blocking startup for 30s on a missing database.
      serverSelectionTimeoutMS: 3000,
    });
    status = 'connected';
    logger.info('db_connected', { uri: redactUri(config.mongoUri) });
  } catch (error) {
    status = 'unavailable';
    logger.warn('db_unavailable', {
      uri: redactUri(config.mongoUri),
      error: error instanceof Error ? error.message : String(error),
      note: 'Server continues in degraded mode; endpoints fall back to fixtures.',
    });
  }

  return status;
}

export async function disconnectDatabase(): Promise<void> {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect();
  }
  status = 'disabled';
}

/** Strip credentials before a URI ever reaches a log line. */
export function redactUri(uri: string): string {
  return uri.replace(/\/\/([^@]+)@/, '//***@');
}
