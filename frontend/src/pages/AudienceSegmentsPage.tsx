import { Link } from 'react-router-dom';

import { Badge, Card, EmptyState, MockBanner, PageHeader, ScoreBar } from '@/components/ui';
import { useLabState } from '@/hooks/useLabState';
import { mockAudienceGraph } from '@/mock';
import { percent } from '@/utils/format';
import type { AudienceSegment } from '@/types';

/**
 * Step 2 — the discovered audience graph.
 *
 * Segments are flat with a `parentSegment` pointer; the tree is rebuilt here.
 * Root segments are the broad niche and are not simulated — the leaves are
 * where behaviour actually differs.
 */
export default function AudienceSegmentsPage() {
  const { graph } = useLabState();
  // Fall back to the fixture so this page is useful on a cold load.
  const data = graph ?? mockAudienceGraph;
  const isMock = graph === null;

  const roots = data.segments.filter((segment) => segment.parentSegment === null);
  const childrenOf = (id: string) =>
    data.segments.filter((segment) => segment.parentSegment === id);

  return (
    <>
      <PageHeader
        title="Audience Segments"
        description="Sub-niches the AI found inside your audience, and how likely content is to spread between them."
      />

      <MockBanner mock={isMock} />

      {data.segments.length === 0 ? (
        <EmptyState
          title="No segments yet."
          hint="Run audience discovery from Audience Setup."
        />
      ) : (
        <div className="space-y-6">
          {roots.map((root) => (
            <div key={root.id} className="space-y-3">
              <div className="flex items-baseline gap-3">
                <h2 className="text-sm font-semibold text-slate-200">{root.name}</h2>
                <span className="text-xs text-slate-500">root niche · not simulated directly</span>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {childrenOf(root.id).map((segment) => (
                  <SegmentCard key={segment.id} segment={segment} />
                ))}
              </div>
            </div>
          ))}

          <Card title="Propagation edges" subtitle="How content is expected to spread between segments">
            {data.adjacency && data.adjacency.length > 0 ? (
              <ul className="space-y-2 text-sm">
                {data.adjacency.map((edge) => (
                  <li key={`${edge.fromSegmentId}-${edge.toSegmentId}`} className="flex items-center gap-3">
                    <span className="text-slate-300">{nameOf(data.segments, edge.fromSegmentId)}</span>
                    <span className="text-slate-600">→</span>
                    <span className="text-slate-300">{nameOf(data.segments, edge.toSegmentId)}</span>
                    <span className="ml-auto font-mono text-xs text-slate-400">
                      {percent(edge.spilloverProbability)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No adjacency discovered.</p>
            )}
          </Card>

          <div className="text-sm text-slate-400">
            Next: <Link className="text-accent hover:underline" to="/upload">upload a reel</Link>.
          </div>
        </div>
      )}
    </>
  );
}

function SegmentCard({ segment }: { segment: AudienceSegment }) {
  return (
    <Card>
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-100">{segment.name}</h3>
        <Badge>{percent(segment.relevanceScore)} relevant</Badge>
      </div>

      <p className="mb-3 text-sm leading-relaxed text-slate-400">{segment.description}</p>

      <ScoreBar value={segment.relevanceScore} label="Relevance to your goal" />

      <ul className="mt-3 flex flex-wrap gap-1.5">
        {segment.characteristics.map((characteristic) => (
          <li key={characteristic}>
            <Badge>{characteristic}</Badge>
          </li>
        ))}
      </ul>

      {segment.rationale && (
        <p className="mt-3 border-t border-ink-600 pt-3 text-xs italic leading-relaxed text-slate-500">
          {segment.rationale}
        </p>
      )}
    </Card>
  );
}

function nameOf(segments: AudienceSegment[], id: string): string {
  return segments.find((segment) => segment.id === id)?.name ?? id;
}
