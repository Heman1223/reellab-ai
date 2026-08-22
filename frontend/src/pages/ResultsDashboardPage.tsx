import {
  Badge,
  Button,
  Card,
  MockBanner,
  PageHeader,
  ScoreBar,
  StatTile,
} from '@/components/ui';
import { useLabState } from '@/hooks/useLabState';
import { percent, score } from '@/utils/format';
import type { AudienceSegmentResult, Bottleneck, PersonaSimulationResult } from '@/types';

/**
 * Step 5 — the results dashboard.
 */
export default function ResultsDashboardPage() {
  const { simulation } = useLabState();
  
  if (!simulation) return null;
  const result = simulation;
  const isMock = result.metadata?.mock ?? false;

  const strong = result.audienceSegmentResults.filter((s) => s.verdict === 'strong');
  const weak = result.audienceSegmentResults.filter((s) => s.verdict === 'weak');

  const personas = result.audienceResults.filter(p => !p.error);
  const likelyComplete = personas.filter(p => p.completionProbability >= 0.5).length;
  const likelySave = personas.filter(p => p.saveProbability >= 0.3).length;
  const likelyShare = personas.filter(p => p.shareProbability >= 0.2).length;
  const likelyLike = personas.filter(p => p.likeProbability >= 0.4).length;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <PageHeader
        title="Simulation Results"
        description="Where this reel works, where it does not, and why."
        action={<Badge>{result.status}</Badge>}
      />

      <MockBanner mock={isMock} />

      {/* Virality Potential Meter */}
      <div className="mb-8 mt-6 relative overflow-hidden rounded-2xl border border-ink-700 bg-gradient-to-br from-ink-800 to-ink-900 p-8 shadow-2xl">
        <div className="pointer-events-none absolute -right-20 -top-20 rounded-full bg-accent/20 p-40 blur-3xl" />
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-600">
          Virality Potential
        </h3>
        <div className="flex items-baseline gap-3">
          <span className="bg-gradient-to-br from-accent to-purple-500 bg-clip-text text-7xl font-black tracking-tight text-transparent">
            {(result.overallScore * 100).toFixed(0)}
          </span>
          <span className="text-2xl font-medium text-slate-600">/ 100</span>
        </div>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slate-600">
          Simulated algorithmic spread potential. Based on reach-weighted completion and share rates across all target segments.
        </p>

        {/* WHY THIS SCORE */}
        {(result.bottlenecks.length > 0 || strong.length > 0) && (
          <div className="mt-5 rounded-xl border border-ink-600 bg-white/50 p-4">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Why this score?</p>
            <ul className="space-y-1.5 text-sm text-slate-800">
              {result.bottlenecks.slice(0, 3).map(b => (
                <li key={b.id} className="flex items-start gap-2">
                  <span className="mt-0.5 text-red-500 font-bold">↓</span>
                  <span>{b.description}</span>
                </li>
              ))}
              {strong.length > 0 && (
                <li className="flex items-start gap-2">
                  <span className="mt-0.5 text-green-500 font-bold">↑</span>
                  <span>{strong[0].segmentName} shows strong engagement ({percent(strong[0].score)}).</span>
                </li>
              )}
            </ul>
          </div>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatTile label="Confidence" value={percent(result.confidence)} hint="sample-adjusted" />
        <StatTile label="Personas Simulated" value={String(result.audienceResults.length)} />
      </div>

      {/* Audience Summary */}
      {personas.length > 0 && (
        <Card className="mt-6" title="Audience Summary">
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-accent">{likelyComplete}</span>
              <span className="text-slate-500">of {personas.length} likely to complete</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-purple-500">{likelySave}</span>
              <span className="text-slate-500">likely to save</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-green-500">{likelyShare}</span>
              <span className="text-slate-500">likely to share</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-blue-500">{likelyLike}</span>
              <span className="text-slate-500">likely to like</span>
            </div>
          </div>
        </Card>
      )}

      {/* Synthetic Audience Personas */}
      {personas.length > 0 && (
        <Card className="mt-6" title="Synthetic Audience" subtitle={`${personas.length} AI-generated viewers watched this reel`}>
          <div className="grid gap-4 sm:grid-cols-2">
            {personas.map((persona) => (
              <PersonaCard key={persona.personaId} persona={persona} />
            ))}
          </div>
        </Card>
      )}

      <Card
        className="mt-6"
        title="Bottlenecks"
        subtitle="Where the reel loses people, and the model's hypothesis for why"
      >
        {result.bottlenecks.length === 0 ? (
          <p className="text-sm text-slate-500">
            {result.status === 'failed' || result.audienceResults.filter(r => !r.error).length === 0
              ? 'Insufficient simulation data.'
              : 'No bottlenecks identified. Excellent retention.'}
          </p>
        ) : (
          <ul className="space-y-6">
            {[...result.bottlenecks]
              .sort((a, b) => b.severity - a.severity)
              .map((bottleneck) => (
                <BottleneckRow key={bottleneck.id} bottleneck={bottleneck} />
              ))}
          </ul>
        )}
      </Card>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <Card title="Performs well" subtitle={`${strong.length} segment(s)`}>
          <SegmentList segments={strong} empty="No segment scored as strong." />
        </Card>
        <Card title="Performs poorly" subtitle={`${weak.length} segment(s)`}>
          <SegmentList segments={weak} empty="No segment scored as weak." />
        </Card>
      </div>

      <Card className="mt-6" title="All Audience Segments">
        <SegmentList segments={result.audienceSegmentResults} empty="No segment results." />
      </Card>

      {result.warnings.length > 0 && (
        <Card className="mt-6 border-amber-200 bg-amber-50" title="Hidden Opportunities & Warnings">
          <ul className="space-y-2 text-sm">
            {result.warnings.map((warning) => (
              <li key={warning.code} className="flex items-start gap-3">
                <span className="mt-0.5 shrink-0 rounded bg-amber-100 px-1.5 py-0.5 font-mono text-xs text-amber-800 border border-amber-200">
                  {warning.code}
                </span>
                <span className="leading-relaxed text-amber-900">{warning.message}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="mt-10 flex flex-col items-center justify-center border-t border-ink-700 pt-10 pb-4">
        <Button onClick={() => document.getElementById('experiments')?.scrollIntoView({ behavior: 'smooth' })} className="px-10 py-4 text-lg shadow-lg shadow-accent/20">
          Run Counterfactual Experiments
        </Button>
        <p className="mt-4 text-sm text-slate-500">Test what happens if you change the hook, tone, or audience.</p>
      </div>
    </div>
  );
}

const ACTION_LABELS: Record<string, string> = {
  swipe: '⬆ Swiped away',
  watch: '▶ Watched',
  complete: '✓ Completed',
  like: '❤ Liked',
  save: '🔖 Saved',
  share: '↗ Shared',
  comment: '💬 Commented',
};

function PersonaCard({ persona }: { persona: PersonaSimulationResult }) {
  const actionLabel = ACTION_LABELS[persona.action] ?? persona.action;
  const isPositive = ['complete', 'like', 'save', 'share', 'comment'].includes(persona.action);
  
  return (
    <div className="rounded-xl border border-ink-600 bg-white p-4 space-y-3">
      {/* WHO */}
      <div>
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-slate-900">{persona.personaName}</span>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${isPositive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {actionLabel}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-slate-500">{persona.demographicSummary}</p>
      </div>

      {/* HOW */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>Watch <strong className="text-slate-700">{percent(persona.watchProbability)}</strong></span>
        <span>Complete <strong className="text-slate-700">{percent(persona.completionProbability)}</strong></span>
        <span>Save <strong className="text-slate-700">{percent(persona.saveProbability)}</strong></span>
        {persona.swipeTime != null && (
          <span>Swiped at <strong className="text-slate-700">{persona.swipeTime.toFixed(1)}s</strong></span>
        )}
      </div>

      {/* WHY */}
      <blockquote className="border-l-2 border-accent/40 pl-3 text-xs italic text-slate-600 leading-relaxed">
        "{persona.reason}"
      </blockquote>
    </div>
  );
}


function BottleneckRow({ bottleneck }: { bottleneck: Bottleneck }) {
  return (
    <li className="relative rounded-lg border border-red-200 bg-red-50 p-5">
      <div className="absolute left-0 top-0 h-full w-1 rounded-l-lg bg-red-500" />
      <div className="mb-2 flex flex-wrap items-center gap-3">
        <Badge verdict="weak">{bottleneck.stage}</Badge>
        <span className="text-xs font-medium text-red-700">
          Severity: {percent(bottleneck.severity)}
        </span>
      </div>
      <p className="text-sm font-medium text-slate-900">{bottleneck.description}</p>
      <div className="mt-3 rounded-md bg-white border border-ink-600 p-3 text-sm leading-relaxed text-slate-700">
        <span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">
          AI Diagnosis
        </span>
        {bottleneck.likelyCause}
      </div>
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
    return <p className="text-sm italic text-slate-500">{empty}</p>;
  }

  return (
    <ul className="space-y-6">
      {segments.map((segment) => (
        <li key={segment.segmentId} className="group">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="text-sm font-semibold text-slate-900 transition-colors">{segment.segmentName}</span>
            <Badge verdict={segment.verdict}>{score(segment.score)}</Badge>
          </div>
          <ScoreBar value={segment.score} verdict={segment.verdict} />
          <div className="mt-2.5 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-500">
            <span className="flex items-center gap-1.5"><div className="h-1.5 w-1.5 rounded-full bg-slate-300" /> Watch: <span className="text-slate-700 font-medium">{percent(segment.averageWatchProbability)}</span></span>
            <span className="flex items-center gap-1.5"><div className="h-1.5 w-1.5 rounded-full bg-slate-300" /> Complete: <span className="text-slate-700 font-medium">{percent(segment.averageCompletionProbability)}</span></span>
            <span className="flex items-center gap-1.5"><div className="h-1.5 w-1.5 rounded-full bg-slate-300" /> Share: <span className="text-slate-700 font-medium">{percent(segment.shareRate)}</span></span>
            <span className="flex items-center gap-1.5"><div className="h-1.5 w-1.5 rounded-full bg-slate-300" /> Save: <span className="text-slate-700 font-medium">{percent(segment.saveRate)}</span></span>
          </div>
        </li>
      ))}
    </ul>
  );
}
