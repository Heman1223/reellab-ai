import { Link } from 'react-router-dom';

import {
  Badge,
  Card,
  MockBanner,
  PageHeader,
  ScoreBar,
  StatTile,
} from '@/components/ui';
import { useLabState } from '@/hooks/useLabState';
import { mockSimulationResult } from '@/mock';
import { percent, score } from '@/utils/format';
import type { AudienceSegmentResult, Bottleneck } from '@/types';

/**
 * Step 5 — the results dashboard.
 *
 * Ordering is a product decision: the bottlenecks come before the segment
 * breakdown, and the headline score is a single small tile among several. The
 * score is one output; the diagnosis is the product.
 */
export default function ResultsDashboardPage() {
  const { simulation } = useLabState();
  const result = simulation ?? mockSimulationResult;
  const isMock = simulation === null || (result.metadata?.mock ?? false);

  const strong = result.audienceSegmentResults.filter((s) => s.verdict === 'strong');
  const weak = result.audienceSegmentResults.filter((s) => s.verdict === 'weak');

  return (
    <>
      <PageHeader
        title="Results"
        description="Where this reel works, where it does not, and why."
        action={<Badge>{result.status}</Badge>}
      />

      <MockBanner mock={isMock} />

      <div className="grid gap-3 sm:grid-cols-4">
        <StatTile label="Overall" value={score(result.overallScore)} hint="0–1, reach-weighted" />
        <StatTile label="Confidence" value={percent(result.confidence)} hint="sample-adjusted" />
        <StatTile label="Personas" value={String(result.audienceResults.length)} />
        <StatTile
          label="Waves"
          value={String(result.propagationWaves.length)}
          hint={result.propagationWaves.at(-1)?.terminated ? 'cascade died' : 'still spreading'}
        />
      </div>

      <Card
        className="mt-6"
        title="Bottlenecks"
        subtitle="Where the reel loses people, and the model's hypothesis for why"
      >
        {result.bottlenecks.length === 0 ? (
          <p className="text-sm text-slate-500">No bottlenecks identified.</p>
        ) : (
          <ul className="space-y-4">
            {[...result.bottlenecks]
              .sort((a, b) => b.severity - a.severity)
              .map((bottleneck) => (
                <BottleneckRow key={bottleneck.id} bottleneck={bottleneck} />
              ))}
          </ul>
        )}
      </Card>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Card title="Performs well" subtitle={`${strong.length} segment(s)`}>
          <SegmentList segments={strong} empty="No segment scored as strong." />
        </Card>
        <Card title="Performs poorly" subtitle={`${weak.length} segment(s)`}>
          <SegmentList segments={weak} empty="No segment scored as weak." />
        </Card>
      </div>

      <Card className="mt-6" title="All segments">
        <SegmentList segments={result.audienceSegmentResults} empty="No segment results." />
      </Card>

      {result.warnings.length > 0 && (
        <Card className="mt-6" title="Warnings">
          <ul className="space-y-1.5 text-sm">
            {result.warnings.map((warning) => (
              <li key={warning.code} className="flex gap-3">
                <span className="font-mono text-xs text-slate-500">{warning.code}</span>
                <span className="text-slate-400">{warning.message}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="mt-6 flex flex-wrap gap-4 text-sm text-slate-400">
        <Link className="text-accent hover:underline" to="/personas">
          Individual reactions
        </Link>
        <Link className="text-accent hover:underline" to="/propagation">
          Propagation
        </Link>
        <Link className="text-accent hover:underline" to="/experiments">
          Run a counterfactual
        </Link>
      </div>
    </>
  );
}

function BottleneckRow({ bottleneck }: { bottleneck: Bottleneck }) {
  return (
    <li className="border-l-2 border-signal-weak/40 pl-4">
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <Badge verdict="weak">{bottleneck.stage}</Badge>
        <span className="text-xs text-slate-500">
          severity {percent(bottleneck.severity)} · confidence {percent(bottleneck.confidence)}
        </span>
      </div>
      <p className="text-sm text-slate-300">{bottleneck.description}</p>
      <p className="mt-1.5 text-sm leading-relaxed text-slate-400">
        <span className="text-slate-500">Likely cause: </span>
        {bottleneck.likelyCause}
      </p>
    </li>
  );
}

function SegmentList({
  segments,
  empty,
}: {
  segments: AudienceSegmentResult[];
  empty: string;
}) {
  if (segments.length === 0) {
    return <p className="text-sm text-slate-500">{empty}</p>;
  }

  return (
    <ul className="space-y-4">
      {segments.map((segment) => (
        <li key={segment.segmentId}>
          <div className="mb-1.5 flex items-center justify-between gap-3">
            <span className="text-sm text-slate-200">{segment.segmentName}</span>
            <Badge verdict={segment.verdict}>{score(segment.score)}</Badge>
          </div>
          <ScoreBar value={segment.score} verdict={segment.verdict} />
          <div className="mt-1.5 flex flex-wrap gap-x-4 text-xs text-slate-500">
            <span>watch {percent(segment.averageWatchProbability)}</span>
            <span>complete {percent(segment.averageCompletionProbability)}</span>
            <span>share {percent(segment.shareRate)}</span>
            <span>save {percent(segment.saveRate)}</span>
            <span>{segment.personaCount} personas</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
