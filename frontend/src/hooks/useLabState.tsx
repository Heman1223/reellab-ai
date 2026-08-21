import { createContext, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import type {
  AudienceGraph,
  AudienceRequest,
  ContentDNA,
  CounterfactualExperiment,
  Reel,
  SimulationResult,
} from '@/types';

/**
 * The current experiment session.
 *
 * A creator moves through audience → upload → simulate → experiment, and each
 * step needs the previous one's output. One small context beats threading props
 * through nine pages, and it is far less than a state library would cost us.
 *
 * Nothing here is persisted. A refresh starts over — acceptable for now, and
 * the obvious thing to change once the backend stores projects.
 */
export interface LabState {
  request: AudienceRequest | null;
  graph: AudienceGraph | null;
  reel: Reel | null;
  contentDna: ContentDNA | null;
  simulation: SimulationResult | null;
  experiment: CounterfactualExperiment | null;
}

interface LabContextValue extends LabState {
  setRequest: (value: AudienceRequest | null) => void;
  setGraph: (value: AudienceGraph | null) => void;
  setReel: (value: Reel | null) => void;
  setContentDna: (value: ContentDNA | null) => void;
  setSimulation: (value: SimulationResult | null) => void;
  setExperiment: (value: CounterfactualExperiment | null) => void;
  reset: () => void;
}

const EMPTY: LabState = {
  request: null,
  graph: null,
  reel: null,
  contentDna: null,
  simulation: null,
  experiment: null,
};

const LabContext = createContext<LabContextValue | null>(null);

export function LabProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<LabState>(EMPTY);

  const value = useMemo<LabContextValue>(
    () => ({
      ...state,
      setRequest: (request) => setState((prev) => ({ ...prev, request })),
      setGraph: (graph) => setState((prev) => ({ ...prev, graph })),
      setReel: (reel) => setState((prev) => ({ ...prev, reel })),
      setContentDna: (contentDna) => setState((prev) => ({ ...prev, contentDna })),
      setSimulation: (simulation) => setState((prev) => ({ ...prev, simulation })),
      setExperiment: (experiment) => setState((prev) => ({ ...prev, experiment })),
      reset: () => setState(EMPTY),
    }),
    [state],
  );

  return <LabContext.Provider value={value}>{children}</LabContext.Provider>;
}

export function useLabState(): LabContextValue {
  const context = useContext(LabContext);
  if (!context) throw new Error('useLabState must be used inside <LabProvider>.');
  return context;
}
