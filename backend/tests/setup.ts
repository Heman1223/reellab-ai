/**
 * Test environment guard rails.
 *
 * Tests must not reach a real database, a real AI service or a real model. Set
 * before any module reads `process.env`, which is why this runs as a Jest
 * `setupFiles` entry rather than `setupFilesAfterEnv`.
 */
process.env.NODE_ENV = 'test';
process.env.MONGODB_ENABLED = 'false';
process.env.AI_PROVIDER = 'mock';
process.env.AI_API_KEY = '';
process.env.LOG_LEVEL = 'error';
// Point at a port nothing is listening on, so an accidental call fails fast.
process.env.AI_SERVICE_URL = 'http://127.0.0.1:59999';
