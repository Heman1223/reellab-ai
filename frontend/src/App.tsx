import { AppShell } from '@/components/AppShell';
import LandingPage from '@/pages/LandingPage';
import ReelUploadPage from '@/pages/ReelUploadPage';
import SimulationProgressPage from '@/pages/SimulationProgressPage';
import ResultsDashboardPage from '@/pages/ResultsDashboardPage';
import PersonaResultsPage from '@/pages/PersonaResultsPage';
import PropagationPage from '@/pages/PropagationPage';
import ExperimentsPage from '@/pages/ExperimentsPage';
import ComparisonPage from '@/pages/ComparisonPage';
import { useLabState } from '@/hooks/useLabState';

export default function App() {
  const { contentDna, simulation, experiment } = useLabState();

  return (
    <AppShell>
      <div className="space-y-24 pb-24">
        <section id="hero">
          <LandingPage />
        </section>

        <section id="upload" className="scroll-mt-12">
          <ReelUploadPage />
        </section>

        {contentDna && (
          <section id="simulate" className="scroll-mt-12 border-t border-ink-700 pt-16">
            <SimulationProgressPage />
          </section>
        )}

        {simulation && (
          <section id="results" className="scroll-mt-12 space-y-16 border-t border-ink-700 pt-16">
            <ResultsDashboardPage />
            <PersonaResultsPage />
            <PropagationPage />
            <div id="experiments" className="scroll-mt-12 border-t border-ink-700 pt-16">
              <ExperimentsPage />
            </div>
          </section>
        )}

        {experiment && (
          <section id="compare" className="scroll-mt-12 border-t border-ink-700 pt-16">
            <ComparisonPage />
          </section>
        )}
      </div>
    </AppShell>
  );
}
