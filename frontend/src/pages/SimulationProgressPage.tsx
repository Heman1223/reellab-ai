import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button, Card, ErrorNote, PageHeader } from '@/components/ui';
import { useAsync } from '@/hooks/useAsync';
import { useLabState } from '@/hooks/useLabState';
import { runSimulation } from '@/services/reellabApi';
import { cn } from '@/utils/format';
import type { SimulationDepth } from '@/types';

/**
 * Step 4 — run the simulation.
 *
 * The stage list mirrors `SimulationStatus` in the shared contract. Right now
 * runs are synchronous, so the stages animate on a timer while the request is
 * in flight. When Developer 4 makes runs asynchronous, this page polls
 * `GET /simulation/:id` and reads the real `status` instead — the stage names
 * are already the same strings.
 */
const STAGES = [
  { key: 'analyzing_content', label: 'Reading the reel' },
  { key: 'simulating_personas', label: 'Personas watching' },
  { key: 'propagating', label: 'Modelling propagation' },
  { key: 'reflecting', label: 'Finding bottlenecks' },
] as const;

const DEPTHS: { value: SimulationDepth; label: string; hint: string }[] = [
  { value: 'quick', label: 'Quick', hint: '2 personas per segment' },
  { value: 'standard', label: 'Standard', hint: '4 personas per segment' },
  { value: 'deep', label: 'Deep', hint: '8 personas per segment' },
];

export default function SimulationProgressPage() {
  const navigate = useNavigate();
  const { reel, contentDna, graph, setSimulation } = useLabState();
  const [depth, setDepth] = useState<SimulationDepth>('standard');
  const [stage, setStage] = useState(-1);

  const simulation = useAsync(runSimulation);
  const running = simulation.state === 'loading';

  useEffect(() => {
    if (!running) return;

    setStage(0);
    const timer = setInterval(() => {
      setStage((current) => Math.min(current + 1, STAGES.length - 1));
    }, 900);

    return () => clearInterval(timer);
  }, [running]);

  async function start() {
    const result = await simulation.run({
      reelId: reel?.id ?? 'reel_001',
      contentDna: contentDna ?? undefined,
      graphId: graph?.graphId,
      depth,
    });

    if (result) {
      setSimulation(result);
      navigate('/results');
    }
  }

  return (
    <>
      <PageHeader
        title="Simulation"
        description="Each synthetic viewer watches the reel and decides for themselves. Nothing here is a formula applied to the video."
      />

      <Card title="Depth" subtitle="Persona count is the main driver of both accuracy and cost.">
        <div className="grid gap-3 sm:grid-cols-3">
          {DEPTHS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setDepth(option.value)}
              disabled={running}
              className={cn(
                'rounded-lg border px-4 py-3 text-left transition-colors disabled:opacity-50',
                depth === option.value
                  ? 'border-accent bg-accent/10'
                  : 'border-ink-600 hover:border-ink-500',
              )}
            >
              <div className="text-sm font-medium text-slate-100">{option.label}</div>
              <div className="mt-0.5 text-xs text-slate-500">{option.hint}</div>
            </button>
          ))}
        </div>

        <div className="mt-5">
          <Button onClick={start} disabled={running}>
            {running ? 'Simulating…' : 'Run simulation'}
          </Button>
        </div>
      </Card>

      {stage >= 0 && (
        <Card className="mt-6" title="Progress">
          <ol className="space-y-3">
            {STAGES.map((item, index) => {
              const done = index < stage || (!running && stage >= 0);
              const active = running && index === stage;

              return (
                <li key={item.key} className="flex items-center gap-3 text-sm">
                  <span
                    className={cn(
                      'h-2 w-2 rounded-full',
                      done ? 'bg-signal-strong' : active ? 'animate-pulse bg-accent' : 'bg-ink-500',
                    )}
                  />
                  <span className={cn(done || active ? 'text-slate-200' : 'text-slate-500')}>
                    {item.label}
                  </span>
                </li>
              );
            })}
          </ol>
        </Card>
      )}

      {simulation.error && (
        <div className="mt-6">
          <ErrorNote message={simulation.error} code={simulation.errorCode} />
        </div>
      )}
    </>
  );
}
