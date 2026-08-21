import type { AudienceGraph, AudienceRequest } from '@shared/schemas/audience';
import type { Persona } from '@shared/schemas/persona';

import { ApiError } from '../utils/ApiError';
import { FIXTURES, loadFixture } from '../utils/fixtures';
import { AI_ENDPOINTS, aiClient } from './aiClient';
import { withFixtureFallback } from './fallback';
import { COLLECTIONS, memoryStore } from './store';
import type { Resolved } from './fallback';

export function parseAudienceRequest(body: unknown): AudienceRequest {
  if (typeof body !== 'object' || body === null) {
    throw ApiError.validation('Request body must be a JSON object.');
  }

  const raw = body as Record<string, unknown>;

  const targetAudience = typeof raw.targetAudience === 'string' && raw.targetAudience.trim() !== ''
    ? raw.targetAudience.trim()
    : 'General audience';

  return {
    niche: typeof raw.niche === 'string' && raw.niche.trim() !== '' ? raw.niche.trim() : 'General',
    targetAudience,
    ...(typeof raw.secondaryAudience === 'string' && raw.secondaryAudience.trim() !== ''
      ? { secondaryAudience: raw.secondaryAudience.trim() }
      : {}),
    location: typeof raw.location === 'string' && raw.location.trim() !== '' ? raw.location.trim() : 'Global',
    language: typeof raw.language === 'string' && raw.language.trim() !== '' ? raw.language.trim() : 'English',
    creatorGoal: typeof raw.creatorGoal === 'string' && raw.creatorGoal.trim() !== '' ? raw.creatorGoal.trim() : 'Grow audience and increase engagement',
  };
}

/**
 * Audience discovery. The AI service decides what the sub-niches are — the
 * backend only carries the request there and persists what comes back.
 */
export async function discoverAudience(
  request: AudienceRequest,
  requestId?: string,
): Promise<Resolved<AudienceGraph>> {
  const resolved = await withFixtureFallback<AudienceGraph>(
    'audience.discover',
    () => aiClient.post<AudienceGraph>(AI_ENDPOINTS.audienceDiscover, request, { requestId }),
    () => ({ ...loadFixture<AudienceGraph>(FIXTURES.audienceGraph), request }),
  );

  memoryStore.put(COLLECTIONS.graphs, resolved.data.graphId, resolved.data);
  return resolved;
}

export function getAudienceGraph(graphId: string): AudienceGraph {
  const stored = memoryStore.get<AudienceGraph>(COLLECTIONS.graphs, graphId);
  if (stored) return stored;

  const fixture = loadFixture<AudienceGraph>(FIXTURES.audienceGraph);
  if (fixture.graphId === graphId) return fixture;

  throw ApiError.notFound('Audience graph', graphId);
}

/**
 * Persona generation for a segment. Not exposed as its own REST route yet —
 * the simulation pipeline calls it — but kept as a named service so Developer 4
 * can wire `POST /api/v1/audience/:graphId/personas` in minutes if the frontend
 * needs it.
 */
export async function generatePersonas(
  graphId: string,
  segmentId: string,
  count = 3,
  requestId?: string,
): Promise<Resolved<Persona[]>> {
  const graph = getAudienceGraph(graphId);
  const segment = graph.segments.find((candidate) => candidate.id === segmentId);
  if (!segment) throw ApiError.notFound('Audience segment', segmentId);

  return withFixtureFallback<Persona[]>(
    'personas.generate',
    () =>
      aiClient.post<Persona[]>(
        AI_ENDPOINTS.personasGenerate,
        { segment, count, creatorGoal: graph.request.creatorGoal },
        { requestId },
      ),
    () =>
      loadFixture<Persona[]>(FIXTURES.personas)
        .filter((persona) => persona.segmentId === segmentId)
        .slice(0, count),
  );
}
