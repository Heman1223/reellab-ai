import { Badge, Card, EmptyState, MockBanner, PageHeader, StatTile } from '@/components/ui';
import { useLabState } from '@/hooks/useLabState';
import { mockAudienceGraph, mockSimulationResult } from '@/mock';
import { compactNumber, percent } from '@/utils/format';

/**
 * The propagation cascade.
 *
 * Wave 0 is the seeded audience; each later wave is reached through shares. The
 * interesting question is not how far it goes but *where it stops* — the wave
 * that terminates is usually the one worth fixing.
 *
 * Deliberately CSS bars rather than a charting library. A dependency for four
 * rectangles is not worth the install.
 */
export default function PropagationPage() {
  const { simulation, graph } = useLabState();
  const result = simulation ?? mockSimulationResult;
  const segments = (graph ?? mockAudienceGraph).segments;
  const isMock = simulation === null || (result.metadata?.mock ?? false);

  const waves = result.propagationWaves;
  const peak = Math.max(...waves.map((wave) => wave.reach), 1);
  const total = waves.reduce((sum, wave) => sum + wave.reach, 0);
  const died = waves.some((wave) => wave.terminated);

  const nameOf = (id: string) => segments.find((segment) => segment.id === id)?.name ?? id;

  return (
    <>
      <PageHeader
        title="Propagation"
        description="How far this reel travels beyond the audience it starts with, and where the cascade breaks."
      />

      <MockBanner mock={isMock} />

      {waves.length === 0 ? (
        <EmptyState title="No propagation data." hint="Run a simulation first." />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <StatTile label="Total reach" value={compactNumber(total)} hint="across all waves" />
            <StatTile label="Waves" value={String(waves.length)} />
            <StatTile
              label="Outcome"
              value={died ? 'Died out' : 'Still spreading'}
              hint={died ? `at wave ${waves.findIndex((w) => w.terminated)}` : undefined}
            />
          </div>

          <Card className="mt-6" title="Cascade">
            <ol className="space-y-5">
              {waves.map((wave) => (
                <li key={wave.wave}>
                  <div className="mb-1.5 flex flex-wrap items-center gap-3">
                    <span className="font-mono text-xs text-slate-500">wave {wave.wave}</span>
                    <span className="text-sm text-slate-200">
                      {compactNumber(wave.reach)} viewers
                    </span>
                    <span className="text-xs text-slate-500">
                      {percent(wave.passThroughRate)} pass it on
                    </span>
                    {wave.terminated && <Badge verdict="weak">terminated</Badge>}
                  </div>

                  <div className="h-2 w-full overflow-hidden rounded-full bg-ink-600">
                    <div
                      className={wave.terminated ? 'h-full bg-signal-weak' : 'h-full bg-accent'}
                      style={{ width: `${Math.max(1, (wave.reach / peak) * 100)}%` }}
                    />
                  </div>

                  {wave.segmentIds.length > 0 && (
                    <ul className="mt-2 flex flex-wrap gap-1.5">
                      {wave.segmentIds.map((id) => (
                        <li key={id}>
                          <Badge>{nameOf(id)}</Badge>
                        </li>
                      ))}
                    </ul>
                  )}

                  {wave.note && (
                    <p className="mt-2 text-xs leading-relaxed text-slate-500">{wave.note}</p>
                  )}
                </li>
              ))}
            </ol>
          </Card>
        </>
      )}
    </>
  );
}
