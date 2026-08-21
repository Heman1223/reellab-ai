/**
 * Structured JSON logging.
 *
 * Deliberately dependency-free and about forty lines long. The point is not a
 * logging framework — it is that every AI call, simulation run and request
 * emits one machine-readable line carrying the fields we care about (model,
 * prompt version, latency, tokens, cost). See docs/architecture.md#observability.
 *
 * Reads `process.env` directly rather than importing `config`, so it is safe to
 * use from inside configuration code.
 */

type Level = 'debug' | 'info' | 'warn' | 'error';

const LEVEL_WEIGHT: Record<Level, number> = { debug: 10, info: 20, warn: 30, error: 40 };

function currentThreshold(): number {
  const configured = (process.env.LOG_LEVEL ?? 'info').toLowerCase() as Level;
  return LEVEL_WEIGHT[configured] ?? LEVEL_WEIGHT.info;
}

export type LogFields = Record<string, unknown>;

function emit(level: Level, message: string, fields: LogFields = {}): void {
  if (LEVEL_WEIGHT[level] < currentThreshold()) return;
  if (process.env.NODE_ENV === 'test' && level !== 'error') return;

  const line = JSON.stringify({
    ts: new Date().toISOString(),
    level,
    service: 'backend',
    msg: message,
    ...fields,
  });

  if (level === 'error' || level === 'warn') process.stderr.write(`${line}\n`);
  else process.stdout.write(`${line}\n`);
}

export interface Logger {
  debug(message: string, fields?: LogFields): void;
  info(message: string, fields?: LogFields): void;
  warn(message: string, fields?: LogFields): void;
  error(message: string, fields?: LogFields): void;
  /** Returns a logger that stamps `bound` onto every line. */
  child(bound: LogFields): Logger;
}

function createLogger(bound: LogFields = {}): Logger {
  return {
    debug: (message, fields) => emit('debug', message, { ...bound, ...fields }),
    info: (message, fields) => emit('info', message, { ...bound, ...fields }),
    warn: (message, fields) => emit('warn', message, { ...bound, ...fields }),
    error: (message, fields) => emit('error', message, { ...bound, ...fields }),
    child: (extra) => createLogger({ ...bound, ...extra }),
  };
}

export const logger = createLogger();
