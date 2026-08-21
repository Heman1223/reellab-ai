import { Card, EmptyState, MockBanner, StatTile } from '@/components/ui';
import { PropagationGraph } from '@/components/PropagationGraph';
import { useLabState } from '@/hooks/useLabState';
import { mockAudienceGraph, mockSimulationResult } from '@/mock';
import { compactNumber } from '@/utils/format';

/**
 * The propagation cascade.
 */
export default function PropagationPage() {
  const { simulation } = useLabState();
  const result = simulation ?? mockSimulationResult;
  const isMock = simulation === null || (result.metadata?.mock ?? false);

  const waves = result.propagationWaves;
  const total = waves.reduce((sum, wave) => sum + wave.reach, 0);
  const died = waves.some((wave) => wave.terminated);

  return (
    <div className="mt-16">
      <div className="mb-6">
        <h2 className="text-2xl font-serif font-bold text-slate-900 mb-2">Propagation Cascade</h2>
        <p className="text-slate-500">The algorithmic cascade, simulated across the network.</p>
      </div>

      <MockBanner mock={isMock} />

      {waves.length === 0 ? (
        <EmptyState title="No propagation data." hint="Run a simulation first." />
      ) : (
        <>
          <Card className="mb-6 shadow-sm border-ink-600" title="" subtitle="">
            <PropagationGraph waves={waves} />
          </Card>

          <div className="grid gap-3 sm:grid-cols-3 mb-6">
            <StatTile label="Total reach" value={compactNumber(total)} hint="across all waves" />
            <StatTile label="Waves" value={String(waves.length)} />
            <StatTile
              label="Outcome"
              value={died ? 'Died out' : 'Still spreading'}
              hint={died ? `at wave ${waves.findIndex((w) => w.terminated)}` : undefined}
            />
          </div>

        </>
      )}
    </div>
  );
}

