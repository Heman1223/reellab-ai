import { useState } from 'react';


import { Badge, Button, Card, EmptyState, ErrorNote, Loading } from '@/components/ui';
import { useAsync } from '@/hooks/useAsync';
import { useLabState } from '@/hooks/useLabState';
import { createExperiment } from '@/services/reellabApi';
import { cn } from '@/utils/format';
import type { ModificationType } from '@/types';

/**
 * Step 6 — the counterfactual.
 *
 * The creator picks one lever. The AI proposes changes aimed at the bottleneck
 * this specific reel hit, then each variant is re-simulated against the same
 * audience so the comparison means something.
 *
 * One lever at a time is a product constraint, not a UI limitation: a variant
 * that changes several things cannot be attributed to any of them.
 */
const LEVERS: { value: ModificationType; label: string; question: string }[] = [
  { value: 'hook', label: 'Hook', question: 'What if I change the hook?' },
  { value: 'duration', label: 'Duration', question: 'What if I shorten the reel?' },
  { value: 'cta', label: 'CTA', question: 'What if I change the call to action?' },
  { value: 'tone', label: 'Tone', question: 'What if it felt different?' },
  { value: 'pacing', label: 'Pacing', question: 'What if it moved faster?' },
  { value: 'audience', label: 'Audience', question: 'What if I targeted someone else?' },
];

export default function ExperimentsPage() {
  const { simulation, setExperiment } = useLabState();

  const [lever, setLever] = useState<ModificationType>('hook');
  const [instruction, setInstruction] = useState('');

  const experiment = useAsync(createExperiment);

  if (!simulation) {
    return <EmptyState title="No simulation yet." hint="Run a simulation first to unlock counterfactual experiments." />;
  }

  const baseline = simulation;

  async function run() {
    const created = await experiment.run({
      originalSimulationId: baseline.simulationId,
      modificationType: lever,
      instruction: instruction.trim() || undefined,
      variantCount: 2,
    });

    if (created) {
      setExperiment(created);
      setTimeout(() => document.getElementById('compare')?.scrollIntoView({ behavior: 'smooth' }), 100);
    }
  }

  const topBottleneck = [...baseline.bottlenecks].sort((a, b) => b.severity - a.severity)[0];

  return (
    <>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-serif font-bold text-slate-900">Counterfactual Experiments</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">Change one thing, re-run the same audience, and see what moves.</p>
        </div>
        <Badge>baseline {baseline.simulationId}</Badge>
      </div>

      {topBottleneck && (
        <Card
          className="mb-6"
          title="Suggested target"
          subtitle="The most severe bottleneck from the baseline run"
        >
          <p className="text-sm text-slate-700">{topBottleneck.description}</p>
          <p className="mt-1.5 text-sm text-slate-400">
            <span className="text-slate-500">Likely cause: </span>
            {topBottleneck.likelyCause}
          </p>
        </Card>
      )}

      <Card title="What do you want to change?">
        <div className="grid gap-2 sm:grid-cols-3">
          {LEVERS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setLever(option.value)}
              disabled={experiment.state === 'loading'}
              className={cn(
                'rounded-lg border px-4 py-3 text-left transition-colors disabled:opacity-50',
                lever === option.value
                  ? 'border-accent bg-accent/10'
                  : 'border-ink-600 hover:border-ink-500',
              )}
            >
              <div className="text-sm font-medium text-slate-900">{option.label}</div>
              <div className="mt-0.5 text-xs leading-snug text-slate-500">{option.question}</div>
            </button>
          ))}
        </div>

        <div className="mt-5">
          <label className="label">Steer (optional)</label>
          <input
            className="input"
            value={instruction}
            placeholder="make it feel less salesy"
            onChange={(event) => setInstruction(event.target.value)}
          />
        </div>

        <div className="mt-5">
          <Button onClick={run} disabled={experiment.state === 'loading'}>
            {experiment.state === 'loading' ? 'Running experiment…' : 'Generate and simulate variants'}
          </Button>
        </div>

        {experiment.state === 'loading' && (
          <Loading label="Generating variants and re-simulating…" />
        )}
        {experiment.error && (
          <div className="mt-4">
            <ErrorNote message={experiment.error} code={experiment.errorCode} />
          </div>
        )}
      </Card>
    </>
  );
}
