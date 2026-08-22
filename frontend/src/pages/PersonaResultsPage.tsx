import { Badge, Card, EmptyState, MockBanner, PageHeader, ScoreBar } from '@/components/ui';
import { useLabState } from '@/hooks/useLabState';
import { percent, seconds } from '@/utils/format';
import type { PersonaSimulationResult, ViewerAction } from '@/types';

/**
 * Individual synthetic viewers and what each of them did.
 */
const ACTION_TONE: Record<ViewerAction, 'strong' | 'mixed' | 'weak'> = {
  swipe: 'weak',
  watch: 'mixed',
  complete: 'strong',
  like: 'strong',
  save: 'strong',
  share: 'strong',
  comment: 'strong',
};

export default function PersonaResultsPage() {
  const { simulation } = useLabState();
  
  if (!simulation) return null;
  const result = simulation;
  const isMock = result.metadata?.mock ?? false;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <PageHeader
        title="Individual Viewers"
        description="Every synthetic viewer's decision, in their own words."
      />

      <MockBanner mock={isMock} />

      {result.audienceResults.length === 0 ? (
        <EmptyState title="No persona results." hint="Run a simulation first." />
      ) : (
        <div className="grid gap-6 md:grid-cols-2 mt-6">
          {result.audienceResults.map((reaction) => (
            <PersonaCard key={reaction.personaId} reaction={reaction} />
          ))}
        </div>
      )}
    </div>
  );
}

function extractNameFromId(id: string): string {
  // AI service generates slug IDs like segment__name_1
  const parts = id.split('__');
  if (parts.length > 1) {
    const namePart = parts[1].split('_')[0];
    if (namePart) {
      return namePart.charAt(0).toUpperCase() + namePart.slice(1);
    }
  }
  return id;
}

function PersonaCard({ reaction }: { reaction: PersonaSimulationResult }) {
  const failed = reaction.error !== undefined;
  
  const displayName = reaction.personaName || extractNameFromId(reaction.personaId);
  const demographic = reaction.demographicSummary || `Synthetic Viewer (${reaction.personaId.split('__')[0]})`;

  return (
    <Card className={failed ? 'opacity-60 border-red-300 bg-red-50' : 'border-ink-600 bg-white'}>
      <header className="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-ink-600 pb-4">
        <div>
          <h3 className="text-base font-bold text-slate-900">
            {displayName}
          </h3>
          <p className="mt-1 text-xs text-slate-500">{demographic}</p>
        </div>
        <div className="flex items-center gap-3">
          {reaction.swipeTime !== null && (
            <span className="rounded-md bg-ink-900 px-2 py-1 font-mono text-xs text-slate-600 border border-ink-700">
              Left at {seconds(reaction.swipeTime)}
            </span>
          )}
          <Badge verdict={ACTION_TONE[reaction.action]}>{reaction.action.toUpperCase()}</Badge>
        </div>
      </header>

      {failed ? (
        <p className="text-sm text-signal-weak">
          Simulation failed for this persona: {reaction.error}. Excluded from the averages.
        </p>
      ) : (
        <>
          <blockquote className="mb-6 rounded-r-lg border-l-4 border-accent bg-accent/5 p-4 text-sm italic leading-relaxed text-slate-700 font-serif">
            “{reaction.reason}”
          </blockquote>

          <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
            <ScoreBar value={reaction.watchProbability} label="Watch" />
            <ScoreBar value={reaction.completionProbability} label="Complete" />
            <ScoreBar value={reaction.shareProbability} label="Share" />
            <ScoreBar value={reaction.saveProbability} label="Save" />
            <ScoreBar value={reaction.likeProbability} label="Like" />
            <ScoreBar value={reaction.commentProbability} label="Comment" />
          </div>
        </>
      )}
    </Card>
  );
}
