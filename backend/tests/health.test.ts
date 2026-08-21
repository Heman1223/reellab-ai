import request from 'supertest';

import { createApp } from '../src/app';

const app = createApp();

describe('GET /api/v1/health', () => {
  it('reports ok even with no database and no AI service', async () => {
    const response = await request(app).get('/api/v1/health').expect(200);

    expect(response.body.status).toBe('ok');
    expect(response.body.service).toBe('reellab-backend');
    expect(response.body.dependencies.mongodb.connected).toBe(false);
    expect(response.body.dependencies.aiService.reachable).toBe(false);
    // With AI_PROVIDER=mock the API is honest about serving fixtures.
    expect(response.body.ai.mockMode).toBe(true);
  });

  it('returns a correlation id on every response', async () => {
    const response = await request(app).get('/api/v1/health').expect(200);
    expect(response.headers['x-request-id']).toBeTruthy();
  });
});

describe('unknown routes', () => {
  it('returns the standard error envelope', async () => {
    const response = await request(app).get('/api/v1/does-not-exist').expect(404);

    expect(response.body.error.code).toBe('NOT_FOUND');
    expect(typeof response.body.error.message).toBe('string');
  });
});
