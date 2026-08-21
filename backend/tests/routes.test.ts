import request from 'supertest';

import { createApp } from '../src/app';

const app = createApp();

/**
 * These tests assert that the mock-first contract holds: with no database and
 * no AI service, every route still answers with a well-formed payload that is
 * clearly labelled as a fixture. If this file goes red, the frontend team is
 * blocked.
 */
describe('mock-first API surface', () => {
  it('discovers an audience graph', async () => {
    const response = await request(app)
      .post('/api/v1/audience/discover')
      .send({
        niche: 'fitness',
        targetAudience: 'natural bodybuilding beginners',
        location: 'India',
        language: 'English',
        creatorGoal: 'increase reach among beginners',
      })
      .expect(201);

    expect(response.body.mock).toBe(true);
    expect(response.headers['x-reellab-mock']).toBe('true');
    expect(response.body.data.segments.length).toBeGreaterThanOrEqual(3);
    expect(response.body.data.segments[0]).toHaveProperty('relevanceScore');
  });

  it('rejects an incomplete audience request with the missing field names', async () => {
    const response = await request(app)
      .post('/api/v1/audience/discover')
      .send({ niche: 'fitness' })
      .expect(422);

    expect(response.body.error.code).toBe('VALIDATION_FAILED');
    expect(response.body.error.details.missing).toContain('targetAudience');
  });

  it('analyzes a reel into Content DNA', async () => {
    const response = await request(app)
      .post('/api/v1/reels/analyze')
      .send({ videoPath: 'data/sample_reels/does-not-exist.mp4' })
      .expect(200);

    expect(response.body.data).toHaveProperty('hook');
    expect(response.body.data).toHaveProperty('scenes');
    expect(response.body.mock).toBe(true);
  });

  it('runs a simulation and returns the same result by id', async () => {
    const run = await request(app)
      .post('/api/v1/simulation/run')
      .send({ reelId: 'reel_001', depth: 'quick' })
      .expect(201);

    const { simulationId } = run.body.data;
    expect(simulationId).toMatch(/^sim_/);
    expect(run.body.data.audienceResults.length).toBeGreaterThan(0);
    expect(run.body.data.bottlenecks.length).toBeGreaterThan(0);

    const fetched = await request(app).get(`/api/v1/simulation/${simulationId}`).expect(200);
    expect(fetched.body.data.simulationId).toBe(simulationId);
  });

  it('requires a reel or content DNA to simulate', async () => {
    const response = await request(app).post('/api/v1/simulation/run').send({}).expect(422);
    expect(response.body.error.code).toBe('VALIDATION_FAILED');
  });

  it('creates a counterfactual experiment against an existing simulation', async () => {
    const run = await request(app)
      .post('/api/v1/simulation/run')
      .send({ reelId: 'reel_001' })
      .expect(201);

    const response = await request(app)
      .post('/api/v1/experiments')
      .send({
        originalSimulationId: run.body.data.simulationId,
        modificationType: 'hook',
        variantCount: 2,
      })
      .expect(201);

    expect(response.body.data.variants.length).toBeGreaterThan(0);
    expect(response.body.data.recommendation).toHaveProperty('reasoning');
  });

  it('refuses an experiment whose baseline simulation does not exist', async () => {
    await request(app)
      .post('/api/v1/experiments')
      .send({ originalSimulationId: 'sim_nope', modificationType: 'hook' })
      .expect(404);
  });

  it('resolves a simulation through the generic results route', async () => {
    const run = await request(app)
      .post('/api/v1/simulation/run')
      .send({ reelId: 'reel_001' })
      .expect(201);

    const response = await request(app)
      .get(`/api/v1/results/${run.body.data.simulationId}`)
      .expect(200);

    expect(response.body.data.kind).toBe('simulation');
  });
});
