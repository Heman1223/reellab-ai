# ReelLab — Frontend

React + Vite + TypeScript + Tailwind. Owned by **Developer 3**.

## Run it

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # typecheck + production build
```

## It works with nothing else running

`VITE_USE_MOCKS=true` (the default) means every call in
[`src/services/reellabApi.ts`](src/services/reellabApi.ts) returns a local
fixture after a short artificial delay. No backend, no AI service, no database.

Flip it in the root `.env`:

```
VITE_USE_MOCKS=false
VITE_API_BASE_URL=http://localhost:4000/api/v1
```

The mocks import the *same JSON files* the backend and the AI service read
(`data/`, via the `@data` alias), so there is one fixture and three consumers
rather than three copies that drift.

Anything mock-backed renders a `MockBanner`. Leave it in — the failure mode
we are guarding against is demoing a fixture believing it came from a model.

## Layout

```
src/
├── components/   AppShell (nav) + ui.tsx (all shared primitives)
├── pages/        one file per screen, one screen per route
├── hooks/        useAsync (fetch state), useLabState (session context)
├── services/     apiClient (HTTP boundary) + reellabApi (typed endpoints)
├── mock/         fixtures re-exported from data/
├── types/        re-exports shared/schemas + UI-only types
├── utils/        formatting helpers
├── App.tsx       routes
└── main.tsx      entry
```

Pages, in product order: Audience Setup → Segments → Reel Upload → Simulation →
Results → Persona Results → Propagation → Experiments → Compare.

## Path aliases

| Alias | Points at |
| --- | --- |
| `@/*` | `src/*` |
| `@shared/*` | `../shared/*` — the contracts |
| `@data/*` | `../data/*` — the fixtures |

Configured in both `tsconfig.json` and `vite.config.ts`; change them together.
`server.fs.allow` is widened to the repo root so the dev server can read the two
folders above `frontend/`.

## Conventions

- **Never define an API shape here.** Types come from `@shared/schemas`. If you
  need a field the backend does not send, that is a contract change.
- **Never call `fetch` from a component.** Go through `services/`.
- One page per file, so two people adding screens do not collide.
- `ui.tsx` holds the shared primitives in one file on purpose. Split it when it
  outgrows a screen or two, not before.
- Layout over polish. Every hour spent on animation is an hour not spent making
  the simulation legible.

## What is deliberately missing

No data-fetching library, no state manager, no chart library. `useAsync` is
thirty lines, `useLabState` is one context, and the propagation view is CSS
bars. Add one of these only when something genuinely needs it.

Session state is in memory — a refresh restarts the flow. Every page falls back
to a fixture so it stays useful on a cold load. Persisting projects is a backend
change first.
