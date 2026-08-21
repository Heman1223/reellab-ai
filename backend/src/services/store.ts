import { isDbConnected } from '../config/db';
import { logger } from '../utils/logger';

/**
 * A process-local key/value store used when MongoDB is unavailable.
 *
 * This is not a cache and not a database abstraction — it is the smallest
 * thing that lets `POST /simulation/run` be followed by `GET /simulation/:id`
 * on a laptop with no Mongo running. Developer 4 replaces the call sites with
 * Mongoose models as they land; the interface is deliberately trivial so that
 * swap is mechanical.
 *
 * Contents are lost on restart. That is fine and expected.
 */
const collections = new Map<string, Map<string, unknown>>();

function collection(name: string): Map<string, unknown> {
  let existing = collections.get(name);
  if (!existing) {
    existing = new Map<string, unknown>();
    collections.set(name, existing);
  }
  return existing;
}

export const memoryStore = {
  put<T>(name: string, id: string, value: T): T {
    collection(name).set(id, value);
    if (!isDbConnected()) {
      logger.debug('memory_store_write', { collection: name, id, reason: 'db_unavailable' });
    }
    return value;
  },

  get<T>(name: string, id: string): T | undefined {
    return collection(name).get(id) as T | undefined;
  },

  list<T>(name: string): T[] {
    return [...collection(name).values()] as T[];
  },

  clear(name?: string): void {
    if (name) collections.delete(name);
    else collections.clear();
  },
};

export const COLLECTIONS = {
  reels: 'reels',
  graphs: 'audienceGraphs',
  simulations: 'simulations',
  experiments: 'experiments',
} as const;
