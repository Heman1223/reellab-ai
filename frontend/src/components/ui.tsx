import type { ReactNode } from 'react';

import { cn, percent } from '@/utils/format';

/**
 * The shared UI primitives.
 *
 * Kept in one file on purpose: nine pages built by one developer in a day do
 * not need nine component files, and a single import line is easier to work
 * with than a folder of five-line modules. Split it when it stops fitting on a
 * screen or two.
 */

// --- layout -----------------------------------------------------------------

export function Card({
  title,
  subtitle,
  action,
  children,
  className,
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('card', className)}>
      {(title || action) && (
        <header className="mb-4 flex items-start justify-between gap-4">
          <div>
            {title && <h2 className="text-sm font-semibold text-slate-100">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-50">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-slate-400">{description}</p>}
      </div>
      {action}
    </header>
  );
}

// --- controls ---------------------------------------------------------------

export function Button({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  disabled,
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit';
  variant?: 'primary' | 'ghost';
  disabled?: boolean;
  className?: string;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40',
        variant === 'primary'
          ? 'bg-accent text-ink-900 hover:bg-accent-soft'
          : 'border border-ink-600 text-slate-300 hover:border-ink-500 hover:text-slate-100',
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Field({
  label,
  value,
  onChange,
  placeholder,
  hint,
  required,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  hint?: string;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="label">
        {label}
        {required && <span className="ml-1 text-signal-weak">*</span>}
      </span>
      <input
        className="input"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

// --- status -----------------------------------------------------------------

export type Verdict = 'strong' | 'mixed' | 'weak';

const VERDICT_STYLES: Record<Verdict, string> = {
  strong: 'bg-signal-strong/15 text-signal-strong border-signal-strong/30',
  mixed: 'bg-signal-mixed/15 text-signal-mixed border-signal-mixed/30',
  weak: 'bg-signal-weak/15 text-signal-weak border-signal-weak/30',
};

export function Badge({
  children,
  verdict,
  className,
}: {
  children: ReactNode;
  verdict?: Verdict;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium',
        verdict ? VERDICT_STYLES[verdict] : 'border-ink-500 bg-ink-700 text-slate-300',
        className,
      )}
    >
      {children}
    </span>
  );
}

/**
 * Marks output that came from a fixture rather than a model.
 *
 * This is not decoration. During the hackathon most of the UI will be showing
 * mock data most of the time, and the failure mode we are guarding against is
 * demoing a fixture believing it came from the AI.
 */
export function MockBanner({ mock }: { mock: boolean }) {
  if (!mock) return null;

  return (
    <div className="mb-4 rounded-lg border border-signal-mixed/30 bg-signal-mixed/10 px-3 py-2 text-xs text-signal-mixed">
      Mock data — this came from a development fixture, not a model.
    </div>
  );
}

export function ScoreBar({
  value,
  verdict,
  label,
}: {
  value: number;
  verdict?: Verdict;
  label?: string;
}) {
  const colour =
    verdict === 'strong'
      ? 'bg-signal-strong'
      : verdict === 'weak'
        ? 'bg-signal-weak'
        : verdict === 'mixed'
          ? 'bg-signal-mixed'
          : 'bg-accent';

  return (
    <div>
      {label && (
        <div className="mb-1 flex justify-between text-xs text-slate-400">
          <span>{label}</span>
          <span className="font-mono text-slate-300">{percent(value)}</span>
        </div>
      )}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-600">
        <div
          className={cn('h-full rounded-full transition-all', colour)}
          style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}
        />
      </div>
    </div>
  );
}

export function StatTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-lg border border-ink-600 bg-ink-700/50 px-4 py-3">
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 font-mono text-xl text-slate-100">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

// --- states -----------------------------------------------------------------

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-sm text-slate-400">
      <span className="h-3 w-3 animate-pulse rounded-full bg-accent" />
      {label}
    </div>
  );
}

export function ErrorNote({ message, code }: { message: string; code?: string | null }) {
  return (
    <div className="rounded-lg border border-signal-weak/30 bg-signal-weak/10 px-4 py-3 text-sm text-signal-weak">
      {code && <span className="mr-2 font-mono text-xs opacity-70">{code}</span>}
      {message}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-ink-600 px-6 py-10 text-center">
      <p className="text-sm text-slate-300">{title}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
