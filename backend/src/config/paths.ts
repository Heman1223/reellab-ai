import fs from 'node:fs';
import path from 'node:path';

/**
 * Walk up from this file until we find the repo root.
 *
 * We detect it by the presence of both `shared/` and `data/`, which exist in
 * the repo and nowhere else. Walking beats a fixed number of `..` hops because
 * the compiled output sits at a different depth (`dist/backend/src/config`)
 * than the source (`backend/src/config`).
 */
function findRepoRoot(startDir: string): string {
  let current = startDir;

  for (let i = 0; i < 10; i += 1) {
    const hasShared = fs.existsSync(path.join(current, 'shared', 'schemas'));
    const hasData = fs.existsSync(path.join(current, 'data'));
    if (hasShared && hasData) return current;

    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }

  // Fall back to the process working directory. Fixture loading will report a
  // clear error if this turns out to be wrong.
  return process.cwd();
}

export const REPO_ROOT = findRepoRoot(__dirname);
export const DATA_DIR = path.join(REPO_ROOT, 'data');
export const MOCK_DIR = path.join(DATA_DIR, 'mock_personas');
export const EVALUATION_DIR = path.join(DATA_DIR, 'evaluation');
