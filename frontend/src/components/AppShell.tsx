import { NavLink } from 'react-router-dom';
import type { ReactNode } from 'react';

import { USE_MOCKS } from '@/services/apiClient';
import { cn } from '@/utils/format';

/**
 * Navigation and page frame.
 *
 * The nav order is the product flow, not an alphabetical menu — someone opening
 * the app for the first time should be able to read it top to bottom and
 * understand what ReelLab does.
 */
const NAV = [
  { to: '/audience', label: 'Audience Setup' },
  { to: '/segments', label: 'Segments' },
  { to: '/upload', label: 'Reel Upload' },
  { to: '/simulate', label: 'Simulation' },
  { to: '/results', label: 'Results' },
  { to: '/personas', label: 'Persona Results' },
  { to: '/propagation', label: 'Propagation' },
  { to: '/experiments', label: 'Experiments' },
  { to: '/compare', label: 'Compare' },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-full">
      <aside className="hidden w-60 shrink-0 border-r border-ink-700 bg-ink-800 p-5 md:block">
        <div className="mb-8">
          <div className="text-lg font-semibold tracking-tight text-slate-50">ReelLab</div>
          <div className="mt-0.5 text-xs text-slate-500">Experiment Before You Publish.</div>
        </div>

        <nav className="space-y-0.5">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'block rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-ink-600 text-slate-50'
                    : 'text-slate-400 hover:bg-ink-700 hover:text-slate-200',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-8 rounded-lg border border-ink-600 px-3 py-2 text-xs text-slate-500">
          <div className="font-medium text-slate-400">
            {USE_MOCKS ? 'Mock mode' : 'Live API'}
          </div>
          <p className="mt-1 leading-relaxed">
            {USE_MOCKS
              ? 'Reading local fixtures. Set VITE_USE_MOCKS=false to call the backend.'
              : 'Calling the backend. Check the mock badge on each result.'}
          </p>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>
    </div>
  );
}
