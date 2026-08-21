import fs from 'node:fs';
import path from 'node:path';

import { config } from '../src/config/env';
import { getDbStatus, isDbConnected, redactUri } from '../src/config/db';
import { MOCK_DIR, REPO_ROOT } from '../src/config/paths';
import { FIXTURES, loadFixture } from '../src/utils/fixtures';

describe('configuration', () => {
  it('resolves the repo root from either src or dist', () => {
    expect(fs.existsSync(path.join(REPO_ROOT, 'shared', 'schemas'))).toBe(true);
    expect(fs.existsSync(path.join(REPO_ROOT, 'data'))).toBe(true);
  });

  it('has a usable Mongo URI even when nothing is configured', () => {
    expect(config.mongoUri).toMatch(/^mongodb(\+srv)?:\/\//);
  });

  it('never logs Mongo credentials', () => {
    expect(redactUri('mongodb://test-user:test-password@localhost:27017/reellab-test')).toBe(
      'mongodb://***@localhost:27017/reellab-test',
    );
    expect(redactUri('mongodb://localhost:27017/reellab')).toBe(
      'mongodb://localhost:27017/reellab',
    );
  });

  it('reports a disconnected database rather than throwing', () => {
    expect(isDbConnected()).toBe(false);
    expect(['disabled', 'unavailable', 'connecting']).toContain(getDbStatus());
  });
});

describe('fixtures', () => {
  it('loads every fixture the mock API depends on', () => {
    for (const filename of Object.values(FIXTURES)) {
      expect(fs.existsSync(path.join(MOCK_DIR, filename))).toBe(true);
      expect(loadFixture(filename)).toBeTruthy();
    }
  });

  it('keeps persona ids consistent between the persona and simulation fixtures', () => {
    const personas = loadFixture<Array<{ id: string; segmentId: string }>>(FIXTURES.personas);
    const simulation = loadFixture<{ audienceResults: Array<{ personaId: string }> }>(
      FIXTURES.simulationResult,
    );

    const personaIds = new Set(personas.map((persona) => persona.id));
    for (const result of simulation.audienceResults) {
      expect(personaIds.has(result.personaId)).toBe(true);
    }
  });

  it('keeps segment ids consistent between the graph and the simulation fixtures', () => {
    const graph = loadFixture<{ segments: Array<{ id: string }> }>(FIXTURES.audienceGraph);
    const simulation = loadFixture<{ audienceSegmentResults: Array<{ segmentId: string }> }>(
      FIXTURES.simulationResult,
    );

    const segmentIds = new Set(graph.segments.map((segment) => segment.id));
    for (const result of simulation.audienceSegmentResults) {
      expect(segmentIds.has(result.segmentId)).toBe(true);
    }
  });
});
