# ReelLab — Development Workflow

24 hours, four people, one repository. Everything here exists to make that work.

## Branches

```
main
│
├── feature/audience-simulation     Developer 1
├── feature/video-analysis          Developer 2
├── feature/frontend                Developer 3
└── feature/backend                 Developer 4
```

Create your own after reviewing the foundation:

```bash
git checkout -b feature/frontend
```

## Rules

1. **Never push directly to `main`.**
2. Work inside your ownership area.
3. Feature branches, always.
4. Merge through pull requests.
5. Keep PRs small — a PR that touches forty files at hour 18 will not get
   reviewed, it will get rubber-stamped.
6. Do not modify another developer's module without telling them first.
7. Pull or rebase from `main` before an important merge.
8. Shared schemas are contracts. Backward compatible, always.
9. No giant central files everybody edits.
10. No unnecessary abstractions.

## Ownership

| Developer | Owns | Also touches |
| --- | --- | --- |
| **1 — AI / Simulation** | `ai/audience/`, `ai/personas/`, `ai/simulation/`, `ai/propagation/`, `ai/evaluation/`, `ai/llm.py` | `shared/schemas/{audience,persona,simulation,result}.ts`, `ai/schemas/` |
| **2 — Multimodal AI** | `ai/video_analysis/`, `ai/counterfactual/` | `shared/schemas/{content,experiment}.ts`, `ai/schemas/` |
| **3 — Frontend** | `frontend/` | `shared/schemas/` (read-only, mostly) |
| **4 — Backend / Infra** | `backend/`, `scripts/`, `docker-compose.yml`, `*/Dockerfile` | `shared/schemas/`, `.env.example` |

Shared and needing a heads-up before you change them: `shared/`, `data/`,
`docs/`, `.env.example`.

Each schema file names its owner in a header comment. Ping them.

## Mock-first

**Nobody waits for anybody.** That is the whole strategy.

| Developer | Works against |
| --- | --- |
| 1 | `data/mock_personas/content_dna.json` — build simulation without Dev 2 |
| 2 | A sample MP4 in `data/sample_reels/` — build analysis without anyone |
| 3 | `data/mock_personas/simulation_result.json` — build the UI without a backend |
| 4 | Fixture responses — build the API without a working AI service |

Every layer falls back to a fixture on its own:

- Frontend: `VITE_USE_MOCKS=true`
- Backend: `withFixtureFallback` in `backend/src/services/fallback.ts`
- AI service: `with_fixture_fallback` in `ai/llm.py`

All three read the same files. Anything mock-backed is labelled — `mock: true`
in the payload, `X-ReelLab-Mock: true` in the header, a `MOCK_DATA` warning in
the simulation result, and a yellow banner in the UI.

**Leave the labels in.** The failure mode we are guarding against is demoing a
fixture believing it came from a model.

## Changing a shared schema

The one thing that can break three people at once. Do all of it in one PR:

1. Edit `shared/schemas/<file>.ts` — **additive, optional fields only**.
2. Mirror it in `ai/schemas/<file>.py`.
3. Update the affected fixture in `data/`.
4. Run `cd backend && npm test` and `cd ai && python -m pytest`. The
   fixture-validation tests in both suites catch drift.
5. Say so in the team chat.

Never rename or repurpose a field mid-hackathon. Add a new one and mark the old
one deprecated in a comment.

## Avoiding conflicts

Files that four people would otherwise fight over, and how they are structured
to prevent it:

| File | Design |
| --- | --- |
| `backend/src/routes/index.ts` | One `use` line per feature area. Add routes to your own `*.routes.ts` instead. |
| `frontend/src/App.tsx` | One route line per page. Pages live in their own files. |
| `shared/schemas/index.ts` | Re-exports only. Never add types here. |
| `ai/main.py` | Router includes only. Logic lives in the module packages. |
| `frontend/src/components/ui.tsx` | Shared primitives only. Page-specific components stay in the page. |

General rule: if you are about to add fifty lines to a file someone else is also
editing, add a new file instead.

## Running things

```bash
bash scripts/setup.sh     # once
bash scripts/dev.sh       # all three services
```

Or individually:

```bash
cd backend  && npm run dev                              # :4000
cd frontend && npm run dev                              # :5173
cd ai       && uvicorn main:app --reload --port 8000    # :8000
```

None of them require the others to be running.

## Tests

```bash
cd backend  && npm test           # jest + supertest
cd ai       && python -m pytest   # from inside ai/
cd frontend && npm run build      # typecheck + build is the frontend's test
```

Run the relevant suite before opening a PR. The full set takes about a minute.

## Commits

```
feat: add persona caching by segment
fix: exclude failed personas from segment averages
chore: bump ai dependencies
docs: document the counterfactual endpoint
```

Say what changed. Nobody has time to read a diff to find out.

## When something breaks

Log it in [`failure-log.md`](failure-log.md) — especially model failures. At
hour 20 the difference between a good demo and a bad one is usually knowing
which limitations you already found and can talk about honestly.

## Integration checkpoints

Do not leave integration to the end. Suggested rhythm:

| Hour | Target |
| --- | --- |
| ~4 | Frontend on mocks, backend serving fixtures, AI service up |
| ~8 | Backend calling the real AI service; `AI_PROVIDER` flipped |
| ~12 | One real reel through video analysis into a real simulation |
| ~16 | End-to-end with a real counterfactual |
| ~20 | Feature freeze. Fix, log limitations, rehearse |

The first end-to-end run should happen long before every AI feature is finished.
A pipeline that runs on fixtures at hour 4 is worth more than a perfect module
at hour 20.
