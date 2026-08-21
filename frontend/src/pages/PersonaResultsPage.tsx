import { Badge, Card, EmptyState, MockBanner, PageHeader, ScoreBar } from '@/components/ui';
import { useLabState } from '@/hooks/useLabState';
import { mockSimulationResult, personaById } from '@/mock';
import { percent, seconds } from '@/utils/format';
import type { PersonaSimulationResult, ViewerAction } from '@/types';

/**
 * Individual synthetic viewers and what each of them did.
 *
 * The `reason` is the most important thing on this page. It is the difference
 * between "your reel scored 0.38" and "Karan left at 2.6 seconds because
 * nothing happened" — the second is something a creator can act on, and it is
 * the reason the simulation reasons rather than scores.
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
  const result = simulation ?? mockSimulationResult;
  const isMock = simulation === null || (result.metadata?.mock ?? false);

  return (
    <>
      <PageHeader
        title="Persona Results"
        description="Every synthetic viewer's decision, in their own words."
      />

      <MockBanner mock={isMock} />

      {result.audienceResults.length === 0 ? (
        <EmptyState title="No persona results." hint="Run a simulation first." />
      ) : (
        <div className="space-y-4">
          {result.audienceResults.map((reaction) => (
            <PersonaCard key={reaction.personaId} reaction={reaction} />
          ))}
        </div>
      )}
    </>
  );
}

function PersonaCard({ reaction }: { reaction: PersonaSimulationResult }) {
  const persona = personaById(reaction.personaId);
  const failed = reaction.error !== undefined;

  return (
    <Card className={failed ? 'opacity-60' : undefined}>
      <header className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            {persona?.name ?? reaction.personaId}
          </h3>
          {persona && (
            <p className="mt-0.5 text-xs text-slate-500">{persona.demographicSummary}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge verdict={ACTION_TONE[reaction.action]}>{reaction.action}</Badge>
          {reaction.swipeTime !== null && (
            <span className="font-mono text-xs text-slate-500">
              left at {seconds(reaction.swipeTime)}
            </span>
          )}
        </div>
      </header>

      {failed ? (
        <p className="text-sm text-signal-weak">
          Simulation failed for this persona: {reaction.error}. Excluded from the averages.
        </p>
      ) : (
        <>
          <blockquote className="border-l-2 border-ink-500 pl-4 text-sm italic leading-relaxed text-slate-700">
            “{reaction.reason}”
          </blockquote>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <ScoreBar value={reaction.watchProbability} label="Watch" />
            <ScoreBar value={reaction.completionProbability} label="Complete" />
            <ScoreBar value={reaction.shareProbability} label="Share" />
            <ScoreBar value={reaction.saveProbability} label="Save" />
            <ScoreBar value={reaction.likeProbability} label="Like" />
            <ScoreBar value={reaction.commentProbability} label="Comment" />
          </div>

          <p className="mt-3 text-xs text-slate-500">
            Confidence {percent(reaction.confidence)}
          </p>
        </>
      )}
    </Card>
  );
}
