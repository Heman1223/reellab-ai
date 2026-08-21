import type { ReactNode } from 'react';

import { USE_MOCKS } from '@/services/apiClient';

/**
 * Page frame for the single page app.
 */

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-ink-900 font-sans text-slate-800">
      <header className="flex items-center justify-between border-b border-ink-700 bg-ink-800 px-6 py-4 lg:px-10">
        <div>
          <div className="text-xl font-semibold tracking-tight text-slate-900">ReelLab</div>
          <div className="text-xs text-slate-500 mt-0.5">Experiment Before You Publish.</div>
        </div>

        {/* Navigation hidden for single page scroll experience */}
        <div></div>

        <div className="text-right">
          <div className="text-xs font-medium text-slate-500">
            {USE_MOCKS ? 'Mock mode' : 'Live API'}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5 max-w-[150px]">
            {USE_MOCKS ? 'Local fixtures' : 'Calling backend'}
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto px-6 py-8 lg:px-10">
        <div className="mx-auto w-full max-w-screen-2xl">{children}</div>
      </main>
    </div>
  );
}
