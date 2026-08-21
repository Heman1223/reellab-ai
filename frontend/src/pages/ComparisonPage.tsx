import {
  Badge,
  Card,
  EmptyState,
  MockBanner,
  ScoreBar,
} from '@/components/ui';
import { useLabState } from '@/hooks/useLabState';
import { mockAudienceGraph, mockExperiment, mockSimulationResult } from '@/mock';
import { cn, delta, score } from '@/utils/format';
import type { Variant, VariantComparison } from '@/types';

/**
 * Step 7 — original vs variants.
 *
 * The caveats are rendered as prominently as the recommendation on purpose. A
 * 0.03 win on a five-persona run is noise, and a comparison UI that hides that
 * teaches creators to trust numbers they should not.
 */
export default function ComparisonPage() {
  const { experiment, simulation, graph } = useLabState();
  const result = experiment ?? mockExperiment;
  const baseline = simulation ?? mockSimulationResult;
  const segments = (graph ?? mockAudienceGraph).segments;
  const isMock = experiment === null || (result.metadata?.mock ?? false);

  const comparisonFor = (variantId: string): VariantComparison | undefined =>
    result.comparison.find((entry) => entry.variantId === variantId);

  const nameOf = (id: string) => segments.find((segment) => segment.id === id)?.name ?? id;

  return (
    <>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-serif font-bold text-slate-900">Original vs Variants</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">{result.hypothesis}</p>
        </div>
        <Badge>{result.modificationType}</Badge>
      </div>

      <MockBanner mock={isMock} />

      {result.variants.length === 0 ? (
        <EmptyState title="No variants yet." hint="Run an experiment first." />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="border-ink-500">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">Original</h3>
                <span className="font-mono text-lg text-slate-700">
                  {score(baseline.overallScore)}
                </span>
              </div>
              <ScoreBar value={baseline.overallScore} />
              <p className="mt-3 text-xs leading-relaxed text-slate-500">
                The reel as it stands. Every variant below is measured against this.
              </p>
            </Card>

            {result.variants.map((variant) => (
              <VariantCard
                key={variant.id}
                variant={variant}
                comparison={comparisonFor(variant.id)}
                isWinner={result.recommendation.winningVariantId === variant.id}
              />
            ))}
          </div>

          <Card className="mt-6" title="Per-segment movement">
            {result.comparison.length === 0 ? (
              <p className="text-sm text-slate-500">No comparison data.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[36rem] text-sm">
                  <thead>
                    <tr className="border-b border-ink-600 text-left text-xs uppercase tracking-wider text-slate-500">
                      <th className="pb-2 pr-4 font-medium">Segment</th>
                      {result.variants.map((variant) => (
                        <th key={variant.id} className="pb-2 pr-4 font-medium">
                          {variant.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {segmentIds(result.comparison).map((segmentId) => (
                      <tr key={segmentId} className="border-b border-ink-700/60">
                        <td className="py-2 pr-4 text-slate-700">{nameOf(segmentId)}</td>
                        {result.variants.map((variant) => {
                          const value = comparisonFor(variant.id)?.segmentDeltas[segmentId];
                          return (
                            <td key={variant.id} className="py-2 pr-4 font-mono text-xs">
                              <span
                                className={cn(
                                  value === undefined
                                    ? 'text-slate-600'
                                    : value > 0
                                      ? 'text-signal-strong'
                                      : value < 0
                                        ? 'text-signal-weak'
                                        : 'text-slate-400',
                                )}
                              >
                                {value === undefined ? '—' : delta(value)}
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card className="mt-6" title="Recommendation">
            <p className="text-sm leading-relaxed text-slate-700">
              {result.recommendation.reasoning}
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Confidence {score(result.recommendation.confidence)}
            </p>

            {result.recommendation.caveats.length > 0 && (
              <ul className="mt-4 space-y-1.5 border-t border-ink-600 pt-4 text-xs leading-relaxed text-signal-mixed">
                {result.recommendation.caveats.map((caveat) => (
                  <li key={caveat}>· {caveat}</li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </>
  );
}

function VariantCard({
  variant,
  comparison,
  isWinner,
}: {
  variant: Variant;
  comparison?: VariantComparison;
  isWinner: boolean;
}) {
  return (
    <Card className={isWinner ? 'border-signal-strong/40' : undefined}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">{variant.label}</h3>
        <span className="font-mono text-lg text-slate-700">
          {variant.score !== undefined ? score(variant.score) : '—'}
        </span>
      </div>

      {variant.score !== undefined && <ScoreBar value={variant.score} />}

      {comparison && (
        <div className="mt-2 flex items-center gap-2">
          <span
            className={cn(
              'font-mono text-xs',
              comparison.scoreDelta > 0 ? 'text-signal-strong' : 'text-signal-weak',
            )}
          >
            {delta(comparison.scoreDelta)}
          </span>
          {isWinner && <Badge verdict="strong">recommended</Badge>}
        </div>
      )}

      <blockquote className="mt-3 border-l-2 border-accent-dim pl-3 text-sm italic leading-relaxed text-slate-700">
        “{variant.proposedChange}”
      </blockquote>

      <p className="mt-3 text-xs leading-relaxed text-slate-500">{variant.changeSummary}</p>
    </Card>
  );
}

/** Union of every segment id mentioned across the comparisons, in stable order. */
function segmentIds(comparisons: VariantComparison[]): string[] {
  const seen = new Set<string>();
  for (const comparison of comparisons) {
    for (const id of Object.keys(comparison.segmentDeltas)) seen.add(id);
  }
  return [...seen];
}
