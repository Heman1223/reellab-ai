import { useEffect, useState } from 'react';

import { Button, Card, ErrorNote, PageHeader } from '@/components/ui';
import { useAsync } from '@/hooks/useAsync';
import { useLabState } from '@/hooks/useLabState';
import { runSimulation, discoverAudience } from '@/services/reellabApi';
import { cn } from '@/utils/format';

/**
 * Step 4 — run the simulation.
 */
const STAGES = [
  { key: 'discovering_audience', label: 'Discovering audience niches' },
  { key: 'analyzing_content', label: 'Reading the reel' },
  { key: 'simulating_personas', label: 'Personas watching' },
  { key: 'propagating', label: 'Modelling propagation' },
  { key: 'reflecting', label: 'Finding bottlenecks' },
] as const;

export default function SimulationProgressPage() {
  const { reel, contentDna, graph, setSimulation, setGraph, audienceDescription } = useLabState();
  const [stage, setStage] = useState(-1);
  const [setupError, setSetupError] = useState<string | null>(null);

  const simulation = useAsync(runSimulation);
  // Add a local boolean state to track overall running including audience discovery
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    if (!isRunning) return;

    setStage(0);
    const timer = setInterval(() => {
      setStage((current) => Math.min(current + 1, STAGES.length - 1));
    }, 1500);

    return () => clearInterval(timer);
  }, [isRunning]);

  async function start() {
    setSetupError(null);
    setIsRunning(true);
    let currentGraphId = graph?.graphId;

    try {
      // 1. Discover Audience
      setStage(0); // discovering_audience
      const audienceRes = await discoverAudience({ targetAudience: audienceDescription ?? undefined });
      if (audienceRes) {
        setGraph(audienceRes.data);
        currentGraphId = audienceRes.data.graphId;
      }
      
      // 2. Run Simulation
      setStage(1); // will progress automatically via timer, but advance here too
      const result = await simulation.run({
        reelId: reel?.id ?? 'reel_001',
        contentDna: contentDna ?? undefined,
        graphId: currentGraphId,
        depth: 'standard', // fixed depth for presentation
      });

      if (result) {
        setSimulation(result);
        setTimeout(() => document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' }), 100);
      }
    } catch (err) {
      setSetupError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsRunning(false);
    }
  }

  const hasError = simulation.error || setupError;

  return (
    <>
      <PageHeader
        title="Simulation"
        description="Each synthetic viewer watches the reel and decides for themselves. Nothing here is a formula applied to the video."
      />

      <Card title="Start Run" subtitle="This will generate distinct audience personas and run parallel simulations.">
        <div className="mt-2">
          <Button onClick={start} disabled={isRunning}>
            {isRunning ? 'Simulating…' : 'Run simulation'}
          </Button>
        </div>
      </Card>

      {stage >= 0 && (
        <Card className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500" title="Progress">
          <ol className="space-y-3">
            {STAGES.map((item, index) => {
              const done = index < stage || (!isRunning && stage >= 0 && !hasError);
              const active = isRunning && index === stage;

              return (
                <li key={item.key} className="flex items-center gap-3 text-sm">
                  <span
                    className={cn(
                      'h-2 w-2 rounded-full',
                      done ? 'bg-signal-strong' : active ? 'animate-pulse bg-accent' : 'bg-ink-500',
                    )}
                  />
                  <span className={cn(done || active ? 'text-slate-300' : 'text-slate-600')}>
                    {item.label}
                  </span>
                </li>
              );
            })}
          </ol>
        </Card>
      )}

      {hasError && (
        <div className="mt-6">
          <ErrorNote message={simulation.error || setupError || ''} code={simulation.errorCode} />
        </div>
      )}
    </>
  );
}
