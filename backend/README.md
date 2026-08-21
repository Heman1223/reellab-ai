# ReelLab — Backend

Express + TypeScript + MongoDB. Owned by **Developer 4**.

The backend is deliberately not clever. It validates input, moves data, keeps
state, and logs what things cost. Every decision that requires judgement lives
in the Python AI service.

## Run it

```bash
cd backend
npm install
npm run dev          # tsx watch, http://localhost:4000
```

Other scripts:

| Command | What it does |
| --- | --- |
| `npm run dev` | Watch mode. No build step. |
| `npm run build` | `tsc` → `dist/` |
| `npm start` | Run the build: `node dist/backend/src/server.js` |
| `npm run typecheck` | Types only, no emit |
| `npm test` | Jest + Supertest |

> **Why `dist/backend/src/server.js` and not `dist/server.js`?**
> The type-only contracts in `../shared/schemas` are part of this compilation,
> so `rootDir` is the repo root and the output mirrors that layout. The imports
> are all `import type`, so nothing from `shared/` exists at runtime.

## It runs with nothing else running

No MongoDB, no AI service, no API key — the server still boots and every route
still answers:

- **MongoDB down** → logged as `db_unavailable`, state goes to an in-process
  store (`src/services/store.ts`). Restarting loses it. That is fine for now.
- **AI service down** → `withFixtureFallback` serves the fixtures in `data/`.
- **`AI_PROVIDER=mock`** (the default) → fixtures without even attempting a call.

Anything served from a fixture is marked `"mock": true` in the body **and**
`X-ReelLab-Mock: true` in the headers. Do not demo a fixture believing it came
from a model.

## Layout

```
src/
├── config/       env parsing, Mongo connection, repo-root resolution
├── controllers/  HTTP in, HTTP out — no business logic
├── routes/       one file per feature area, mounted in routes/index.ts
├── services/     orchestration, AI calls, fallbacks, state
├── models/       Mongoose schemas (thin — payloads stay Mixed)
├── middleware/   request logging, error handling, upload
├── utils/        logger, ApiError, fixtures, observability, respond
├── types/        backend-internal types + Express augmentation
├── app.ts        builds the Express app (importable by tests)
└── server.ts     listens, connects the DB, handles shutdown
```

Routes never contain logic. A route wires a path to a controller; a controller
parses the request and calls a service; a service does the work.

## Response shapes

Success — every 2xx body:

```json
{ "data": { }, "mock": false, "requestId": "0f3c…" }
```

Failure — every 4xx/5xx body:

```json
{ "error": { "code": "VALIDATION_FAILED", "message": "…", "details": { } }, "requestId": "0f3c…" }
```

The codes are defined in [`src/utils/ApiError.ts`](src/utils/ApiError.ts) and
cover the failure modes the product has to survive: AI timeouts, an unreachable
AI service, malformed model output, unsupported video, empty transcripts,
partial simulations.

## Routes

See [`docs/api-contract.md`](../docs/api-contract.md) for full request and
response examples.

| Method | Path |
| --- | --- |
| GET | `/api/v1/health` |
| POST | `/api/v1/audience/discover` |
| POST | `/api/v1/reels/upload` |
| POST | `/api/v1/reels/analyze` |
| POST | `/api/v1/simulation/run` |
| GET | `/api/v1/simulation/:id` |
| POST | `/api/v1/experiments` |
| GET | `/api/v1/experiments/:id` |
| GET | `/api/v1/results/:id` |

## Adding a route without a merge conflict

1. Add the handler to an existing file in `controllers/`.
2. Add the path to the matching `routes/*.routes.ts`.
3. Only touch `routes/index.ts` if you are adding a whole new feature area.

## Uploads

`POST /api/v1/reels/upload`, multipart, field name `reel`. Files land in
`UPLOAD_DIR` (default `uploads/` at the repo root, gitignored) under a
generated name. The backend never opens the video — it hands a **path** to the
AI service, which keeps large payloads off the HTTP hop.

## Tests

```bash
npm test
```

`tests/setup.ts` forces `MONGODB_ENABLED=false`, `AI_PROVIDER=mock` and points
`AI_SERVICE_URL` at a dead port, so the suite can never reach a real dependency
or spend a token.

The fixture-consistency tests in `tests/config.test.ts` are the ones that catch
schema drift: if you add a field to `shared/schemas/` and forget the fixture in
`data/`, they go red before the frontend does.
