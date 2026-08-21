/** Small formatting helpers. Presentation only — no logic lives here. */

/** `0.384` → `"38%"` */
export function percent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

/** `0.384` → `"0.38"` */
export function score(value: number): string {
  return value.toFixed(2);
}

/** `+0.23` / `-0.09`, always signed so a delta reads as a delta. */
export function delta(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
}

/** `4.2` → `"4.2s"`, `null` → `"—"` */
export function seconds(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return `${value.toFixed(1)}s`;
}

/** `38100` → `"38.1k"` */
export function compactNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return Math.round(value).toString();
}

/** `1048576` → `"1.0 MB"` */
export function fileSize(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) return `${mb.toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

/** Conditional class names. Keeps JSX readable without pulling in `clsx`. */
export function cn(...values: (string | false | null | undefined)[]): string {
  return values.filter(Boolean).join(' ');
}
