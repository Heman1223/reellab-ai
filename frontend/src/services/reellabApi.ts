import {
  delay,
  mockAudienceGraph,
  mockContentDna,
  mockExperiment,
  mockSimulationResult,
} from '@/mock';
import { USE_MOCKS, apiClient } from '@/services/apiClient';
import type {
  AudienceGraph,
  AudienceRequest,
  ContentDNA,
  CounterfactualExperiment,
  ExperimentRequest,
  Reel,
  SimulationRequest,
  SimulationResult,
} from '@/types';
import type { ApiResult } from '@/services/apiClient';

/**
 * Typed calls to the ReelLab API, one function per endpoint.
 *
 * Every function has a mock branch guarded by `VITE_USE_MOCKS`. That is what
 * lets Developer 3 build the entire UI before the backend or the AI service
 * exists — and, later, lets anyone develop offline.
 *
 * Flip it in `.env`:
 *
 *   VITE_USE_MOCKS=true    local fixtures, no network      (default)
 *   VITE_USE_MOCKS=false   real backend at VITE_API_BASE_URL
 *
 * Keep the two branches returning the same shape. When they diverge, the UI
 * looks finished and breaks on integration day.
 */

export async function discoverAudience(
  request: Partial<AudienceRequest>,
): Promise<ApiResult<AudienceGraph>> {
  if (USE_MOCKS) {
    return delay({ data: { ...mockAudienceGraph, request: request as AudienceRequest }, mock: true }, 700);
  }
  return apiClient.post<AudienceGraph>('/audience/discover', request);
}

export async function uploadReel(file: File): Promise<ApiResult<Reel>> {
  if (USE_MOCKS) {
    return delay(
      {
        data: {
          id: 'reel_mock',
          filename: file.name,
          storagePath: `uploads/${file.name}`,
          sizeBytes: file.size,
          uploadedAt: new Date().toISOString(),
          status: 'uploaded' as const,
        },
        mock: true,
      },
      600,
    );
  }
  return apiClient.upload<Reel>('/reels/upload', file);
}

export async function analyzeReel(input: {
  reelId?: string;
  videoPath?: string;
}): Promise<ApiResult<ContentDNA>> {
  if (USE_MOCKS) {
    return delay({ data: mockContentDna, mock: true }, 900);
  }
  return apiClient.post<ContentDNA>('/reels/analyze', input);
}

export async function runSimulation(
  request: SimulationRequest,
): Promise<ApiResult<SimulationResult>> {
  if (USE_MOCKS) {
    return delay({ data: mockSimulationResult, mock: true }, 1200);
  }
  return apiClient.post<SimulationResult>('/simulation/run', request);
}

export async function getSimulation(id: string): Promise<ApiResult<SimulationResult>> {
  if (USE_MOCKS) {
    return delay({ data: { ...mockSimulationResult, simulationId: id }, mock: true }, 300);
  }
  return apiClient.get<SimulationResult>(`/simulation/${id}`);
}

export async function createExperiment(
  request: ExperimentRequest,
): Promise<ApiResult<CounterfactualExperiment>> {
  if (USE_MOCKS) {
    return delay(
      {
        data: {
          ...mockExperiment,
          originalSimulationId: request.originalSimulationId,
          modificationType: request.modificationType,
        },
        mock: true,
      },
      1400,
    );
  }
  return apiClient.post<CounterfactualExperiment>('/experiments', request);
}

export async function getExperiment(
  id: string,
): Promise<ApiResult<CounterfactualExperiment>> {
  if (USE_MOCKS) {
    return delay({ data: { ...mockExperiment, experimentId: id }, mock: true }, 300);
  }
  return apiClient.get<CounterfactualExperiment>(`/experiments/${id}`);
}
