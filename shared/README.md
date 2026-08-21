# `shared/` — Cross-service contracts

This folder is the **single source of truth** for the data that moves between
the frontend, the backend and the Python AI service. Nothing here is
application logic.

## Layout

| Path | What it is |
| --- | --- |
| `schemas/*.ts` | TypeScript interfaces. Consumed by `frontend/` and `backend/`. |
| `schemas/index.ts` | Barrel re-export. Add `export *` lines only. |
| `examples/*.json` | Canonical **request** payloads used in docs and smoke tests. |

The Python mirror of these types lives in [`ai/schemas/`](../ai/schemas) as
Pydantic models. **The two must stay field-for-field compatible.** If you change
one, change the other in the same pull request.

Runtime **fixtures** (personas, Content DNA, simulation results) live in
[`data/`](../data), not here — see [`data/README.md`](../data/README.md).

## Why these files contain no runtime code

Every file in `schemas/` exports types only. That means consumers can use
`import type { ... }`, TypeScript erases the import entirely, and no bundler,
build step or `rootDir` juggling is needed in either app. Adding a `const`,
`enum` or function here would break that — use a string-literal union instead
of a TypeScript `enum`.

## Contract rules

These matter more than usual because four people are working in parallel for
24 hours.

1. **Additive only.** New fields must be optional (`field?: T`).
2. **Never rename or repurpose** an existing field mid-hackathon. Add a new one
   and deprecate the old one with a comment.
3. **One owner per file** (see the header comment in each file). Ping the owner
   before editing.
4. **Change the Pydantic mirror in the same PR.** A drifted contract is the
   single most expensive bug this architecture can produce.
5. **Fixtures are part of the contract.** If you add a required field, update
   the JSON in `data/` too, or you break everyone else's mock-first workflow.

## How each app consumes this folder

**Backend** (`backend/tsconfig.json`) maps `@shared/*` → `../shared/*` and
includes `../shared/schemas` in the compilation. Because the imports are
type-only they vanish at runtime.

**Frontend** (`frontend/tsconfig.json` + `vite.config.ts`) maps the same alias.
Vite's `server.fs.allow` is widened to the repo root so the dev server can read
outside `frontend/`.
