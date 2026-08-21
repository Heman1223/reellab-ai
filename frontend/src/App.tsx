import { Navigate, Route, Routes } from 'react-router-dom';

import { AppShell } from '@/components/AppShell';
import AudienceSegmentsPage from '@/pages/AudienceSegmentsPage';
import AudienceSetupPage from '@/pages/AudienceSetupPage';
import ComparisonPage from '@/pages/ComparisonPage';
import ExperimentsPage from '@/pages/ExperimentsPage';
import PersonaResultsPage from '@/pages/PersonaResultsPage';
import PropagationPage from '@/pages/PropagationPage';
import ReelUploadPage from '@/pages/ReelUploadPage';
import ResultsDashboardPage from '@/pages/ResultsDashboardPage';
import SimulationProgressPage from '@/pages/SimulationProgressPage';

/**
 * Routes.
 *
 * One route per page, one page per file. Four people adding screens touch four
 * different files; this one changes only when a screen is added or removed.
 */
export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/audience" replace />} />
        <Route path="/audience" element={<AudienceSetupPage />} />
        <Route path="/segments" element={<AudienceSegmentsPage />} />
        <Route path="/upload" element={<ReelUploadPage />} />
        <Route path="/simulate" element={<SimulationProgressPage />} />
        <Route path="/results" element={<ResultsDashboardPage />} />
        <Route path="/personas" element={<PersonaResultsPage />} />
        <Route path="/propagation" element={<PropagationPage />} />
        <Route path="/experiments" element={<ExperimentsPage />} />
        <Route path="/compare" element={<ComparisonPage />} />
        <Route path="*" element={<Navigate to="/audience" replace />} />
      </Routes>
    </AppShell>
  );
}
