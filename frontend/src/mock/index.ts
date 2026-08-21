/**
 * Mock data for frontend development.
 *
 * These are the *same JSON files* the backend and the AI service read, imported
 * through the `@data` alias rather than copied. One fixture, three consumers,
 * no drift — see `data/README.md`.
 *
 * The casts are safe because `backend/tests/config.test.ts` and
 * `ai/tests/test_schemas.py` both validate these files against the contracts on
 * every test run. If a fixture drifts, those go red first.
 */

import audienceGraphJson from '@data/mock_personas/audience_graph.json';
import personasJson from '@data/mock_personas/personas.json';
import contentDnaJson from '@data/mock_personas/content_dna.json';
import simulationResultJson from '@data/mock_personas/simulation_result.json';
import experimentJson from '@data/mock_personas/counterfactual_experiment.json';

import type {
  AudienceGraph,
  ContentDNA,
  CounterfactualExperiment,
  Persona,
  SimulationResult,
} from '@/types';

export const mockAudienceGraph = audienceGraphJson as unknown as AudienceGraph;
export const mockPersonas = personasJson as unknown as Persona[];
export const mockContentDna = contentDnaJson as unknown as ContentDNA;
export const mockSimulationResult = simulationResultJson as unknown as SimulationResult;
export const mockExperiment = experimentJson as unknown as CounterfactualExperiment;

/** Look up a persona by id — the results dashboard joins on this constantly. */
export function personaById(id: string): Persona | undefined {
  return mockPersonas.find((persona) => persona.id === id);
}

/** Simulate network latency so loading states get exercised during development. */
export function delay<T>(value: T, ms = 400): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), ms);
  });
}
