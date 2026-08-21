# ReelLab

**Experiment Before You Publish.**

---

## What is ReelLab?

A synthetic audience simulation and counterfactual experimentation platform for
short-form video creators.

You describe who you are making content for. The AI discovers the sub-niches
inside that audience and generates a synthetic viewer for each one. You upload a
reel. Multimodal AI works out what the reel actually *is*. Then every synthetic
viewer watches it and decides — keep watching, swipe, complete, like, save,
share, comment — and says why, in their own words.

From that you find out which segments it lands with, which it loses, where the
propagation cascade dies, and what the most likely cause is.

Then you ask *what if*: change the hook, shorten it, rewrite the CTA, aim it
somewhere else. The AI generates variants, the simulation runs again, and you
compare original against each variant — before publishing anything.

**ReelLab is not an "AI reel score".** The score is one output. The product is
the laboratory.

---

## Core Product Flow

```
Audience brief
      ↓  AI
Sub-niche discovery
      ↓  AI
Persona generation
      ↓
Reel upload
      ↓  AI
Multimodal understanding → Content DNA
      ↓  AI
Persona behaviour simulation
      ↓
Propagation simulation
      ↓  AI
Bottleneck analysis
      ↓  AI
Counterfactual generation
      ↓
Re-simulation
      ↓
Original vs Variant A vs Variant B
```

---

## Architecture

```
                        REACT FRONTEND  :5173
                               │
                               ▼
                     NODE + EXPRESS API  :4000
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
             MONGODB  :27017          PYTHON AI  :8000
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
              AUDIENCE AI             VIDEO AI             SIMULATION AI
                    │                      │                      │
                    └──────────────────────┼──────────────────────┘
                                           ▼
                                  COUNTERFACTUAL AI
```

Three processes, one database, HTTP and JSON between them.

**The AI / deterministic split** is the most important rule in the repo:

| AI decides | Code decides |
| --- | --- |
| Which sub-niches exist | How many personas run, and in what order |
| What each synthetic viewer is like | How probabilities average into a score |
| What the reel is | Where a share lands; whether the cascade survives |
| Whether a persona stays, and **why** | The deltas between two runs |
| What the bottleneck is | What is persisted, cached, retried, logged |

Remove the model and the product stops existing. That is the point.

Full detail in [`docs/architecture.md`](docs/architecture.md).

---

## Tech Stack

| Layer | Choice |
| --- | --- |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, React Router |
| Backend | Node 22, Express 4, TypeScript, Mongoose |
| Database | MongoDB 7 |
| AI service | Python 3.12+, FastAPI, Pydantic v2 |
| Video | FFmpeg (OpenCV only where it earns its place) |
| Tests | Jest + Supertest, pytest, `vite build` |
| Infra | Docker Compose, `.env` |

No Redis, no queue, no Kubernetes. Nothing needs them yet.

---

## Repository Structure

```
reellab-ai/
├── frontend/          React + Vite + TS + Tailwind        [Dev 3]
│   └── src/{components,pages,hooks,services,types,mock,utils}
├── backend/           Express + TS + Mongoose             [Dev 4]
│   ├── src/{config,controllers,routes,services,models,middleware,utils,types}
│   └── tests/
├── ai/                FastAPI service                     [Dev 1 + Dev 2]
│   ├── audience/{discovery,segmentation}                  [Dev 1]
│   ├── personas/{generation,profiles}                     [Dev 1]
│   ├── simulation/{agents,behavior,engine}                [Dev 1]
│   ├── propagation/engine                                 [Dev 1]
│   ├── evaluation/{datasets,metrics,harness}              [Dev 1]
│   ├── video_analysis/{preprocessing,transcription,multimodal}  [Dev 2]
│   ├── counterfactual/{generation,experiments}            [Dev 2]
│   ├── schemas/       Pydantic mirror of shared/schemas
│   ├── llm.py         the model boundary — every call goes through here
│   └── main.py
├── shared/schemas/    TypeScript contracts (source of truth)
├── data/              fixtures: personas, Content DNA, results, evaluation
├── docs/              architecture, API contract, workflow, failure log
├── scripts/           setup.sh, dev.sh
├── tests/integration/ smoke.sh
├── .env.example
└── docker-compose.yml
```

---

## Local Setup

```bash
git clone <repo-url> reellab-ai
cd reellab-ai
bash scripts/setup.sh
```

Installs all three apps and creates `.env` from the template. Then:

```bash
bash scripts/dev.sh          # all three services
```

**Windows without Git Bash?** Follow the three sections below manually — they
are the whole of what `setup.sh` does.

**Docker instead:**

```bash
docker compose up --build    # frontend :5173, backend :4000, ai :8000, mongo :27017
```

Docker is the fallback. Running natively is faster to iterate on.

### It runs before anything is implemented

No MongoDB, no AI API key, no AI service — all three apps still start and every
screen still works. Each layer falls back to the fixtures in `data/`, and
anything mock-backed is labelled `mock: true` with a banner in the UI.

That is what lets four people start at the same moment. It is also a trap at
demo time: **check the mock flag before believing a result.**

---

## Running Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
npm run build          # typecheck + production build
```

Mocks are on by default (`VITE_USE_MOCKS=true`). Set it to `false` in `.env` to
call the real backend.

---

## Running Backend

```bash
cd backend
npm install
npm run dev            # http://localhost:4000
npm test               # jest + supertest
```

Check it:

```bash
curl http://localhost:4000/api/v1/health
```

Starts whether or not MongoDB is reachable — a missing database degrades the
API, it does not stop it.

---

## Running AI Service

```bash
cd ai
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
python -m pytest                  # run from inside ai/
```

- http://localhost:8000/health — liveness and capabilities
- http://localhost:8000/docs — OpenAPI, generated from the Pydantic contracts

No API key needed. Every endpoint serves fixtures until
[`ai/llm.py`](ai/llm.py) is implemented.

---

## Environment Variables

Copy `.env.example` to `.env` at the repo root. All three services read it.

| Variable | Default | What it does |
| --- | --- | --- |
| `NODE_ENV` | `development` | |
| `PORT` | `4000` | Backend port |
| `MONGODB_URI` | `mongodb://localhost:27017/reellab` | |
| `AI_SERVICE_URL` | `http://localhost:8000` | Where the backend finds the AI service |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origin |
| `AI_PROVIDER` | `mock` | `mock` \| `anthropic` \| `openai` |
| `AI_API_KEY` | *(empty)* | Empty means mock mode regardless of provider |
| `MULTIMODAL_MODEL` | `claude-sonnet-5` | Video understanding |
| `REASONING_MODEL` | `claude-opus-5` | Personas, simulation, bottlenecks |
| `AI_MAX_PERSONAS` | `25` | Hard cost ceiling per run |
| `UPLOAD_DIR` | `uploads` | Gitignored |
| `MAX_UPLOAD_MB` | `100` | |
| `VITE_API_BASE_URL` | `http://localhost:4000/api/v1` | |
| `VITE_USE_MOCKS` | `true` | Frontend fixtures on/off |

**Never commit `.env`.** It is gitignored, along with `node_modules`,
`__pycache__`, `.venv`, `dist`, `build`, `uploads`, `logs` and video files.

---

## Team Ownership

| Developer | Owns | Responsible for |
| --- | --- | --- |
| **1 — AI / Simulation** | `ai/audience/`, `ai/personas/`, `ai/simulation/`, `ai/propagation/`, `ai/evaluation/` | Discovery, sub-niches, persona generation, viewer agents, propagation, scoring, evaluation harness, overall AI architecture |
| **2 — Multimodal AI** | `ai/video_analysis/`, `ai/counterfactual/` | Frame and audio extraction, transcription, Content DNA, hook/pacing/emotion analysis, hypothesis and variant generation |
| **3 — Frontend** | `frontend/` | Every screen: audience setup, segment graph, upload, progress, results, personas, propagation, experiments, comparison |
| **4 — Backend / Infra** | `backend/`, `scripts/`, `docker-compose.yml` | Express, REST API, Mongo, uploads, AI client, error handling, logging, deployment, cost and latency tracking |

Developer 2 generates variants; Developer 1 owns the simulation that judges
them. The generator should not also be the judge.

---

## Git Workflow

```
main
│
├── feature/audience-simulation     Developer 1
├── feature/video-analysis          Developer 2
├── feature/frontend                Developer 3
└── feature/backend                 Developer 4
```

1. Never push directly to `main`.
2. Work inside your ownership area.
3. Feature branches, always.
4. Merge through pull requests.
5. Keep PRs small.
6. Do not modify someone else's module without telling them.
7. Pull or rebase from `main` before an important merge.
8. Shared schemas are contracts — backward compatible, always.
9. No giant central files everybody edits.
10. No unnecessary abstractions.

Changing a shared schema? Edit `shared/schemas/`, mirror it in `ai/schemas/`,
update the fixture in `data/`, run both test suites, tell the team — all in one
PR. Full detail in
[`docs/development-workflow.md`](docs/development-workflow.md).

---

## Documentation

| Document | Contents |
| --- | --- |
| [`docs/architecture.md`](docs/architecture.md) | Services, pipeline, AI/deterministic boundary, failure policy, cost |
| [`docs/api-contract.md`](docs/api-contract.md) | Every endpoint with real request and response bodies |
| [`docs/development-workflow.md`](docs/development-workflow.md) | Branches, ownership, PRs, schema rules, conflict avoidance |
| [`docs/failure-log.md`](docs/failure-log.md) | Template plus the limitations we already know about |
| [`shared/README.md`](shared/README.md) | Contract rules |
| [`data/README.md`](data/README.md) | What each fixture is and why |

---

## Development Philosophy

**Mock First → Integrate Early → Specialize Later.**

Nobody waits for anybody. Dev 1 builds simulation against mock Content DNA;
Dev 2 builds analysis against a sample MP4; Dev 3 builds the UI against a mock
`SimulationResult`; Dev 4 builds the API against fixture AI responses.

The first end-to-end run should happen long before every AI feature is finished.
A pipeline that runs on fixtures at hour 4 is worth more than a perfect module
at hour 20.

---

## Licence

MIT — see [LICENSE](LICENSE).
