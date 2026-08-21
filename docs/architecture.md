# ReelLab — Architecture

## What the system is

A synthetic audience laboratory. A creator describes their audience, uploads a
reel, and finds out how a population of AI-generated viewers would react to it —
segment by segment — before publishing. Then they change one thing and run it
again.

The virality score is one number this produces. It is not the product.

## Services

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

Three processes, one database. No message broker, no job queue, no service mesh.
Everything talks over HTTP with JSON.

**Why two backends?** The Node service handles what Node is good at — HTTP,
uploads, Mongo, orchestration. The Python service handles what Python is good at
— model SDKs, FFmpeg, numerical work. Splitting them also means Developer 4 and
Developers 1–2 can deploy and restart independently, which matters more than
architectural purity when four people share 24 hours.

## The product pipeline

```
Creator brief (niche, audience, location, language, goal)
        ↓  Audience Discovery AI
Sub-niche graph  ── segments + spillover adjacency
        ↓  Persona Generation AI
Synthetic viewers ── one behavioural profile each
        ↓
Reel upload  ── backend stores the file, hands over a path
        ↓  Multimodal AI
Content DNA  ── hook, scenes, tone, pacing, CTA
        ↓  Viewer agents (one model call per persona)
Per-persona reactions ── action + first-person reason + confidence
        ↓  Aggregation (deterministic)
Segment results
        ↓  Propagation engine (deterministic)
Cascade waves ── where it spreads, where it dies
        ↓  Reflection AI
Bottlenecks ── what breaks, and the likely cause
        ↓  Counterfactual AI
Variants ── specific proposed changes with predicted Content DNA
        ↓  Re-simulation
Comparison ── original vs variant A vs variant B
```

## The AI / deterministic boundary

The single most important design rule in this repo.

| AI decides | Code decides |
| --- | --- |
| Which sub-niches exist and how they differ | How many personas run, in what order, at what concurrency |
| What each synthetic viewer is like | How per-persona probabilities average into a segment score |
| What the reel actually is (Content DNA) | Where a share lands and whether the cascade survives another hop |
| Whether a persona keeps watching, and **why** | The deltas between two runs |
| What the bottleneck is and what caused it | What is persisted, cached, retried, logged |
| What to change and whether it would help | What a request is allowed to cost |

The test: **remove the model and the product stops existing.** `overallScore`
would still compute — it would just be an average of numbers nobody thought
about. The intelligence is inside the simulation, not wrapped around it.

The inverse also matters. Propagation mechanics, score aggregation and variant
comparison are deliberately *not* AI. We want those reproducible and
inspectable: when a cascade dies, we point at the arithmetic that killed it, not
at a model's opinion.

## Module ownership

| Path | Owner | Responsibility |
| --- | --- | --- |
| `ai/audience/`, `ai/personas/`, `ai/simulation/`, `ai/propagation/`, `ai/evaluation/` | Dev 1 | Discovery, personas, viewer agents, cascade, evaluation |
| `ai/video_analysis/`, `ai/counterfactual/` | Dev 2 | FFmpeg, transcription, Content DNA, variant generation |
| `frontend/` | Dev 3 | Every screen |
| `backend/`, `scripts/`, `docker-compose.yml` | Dev 4 | API, Mongo, uploads, AI client, deployment |
| `shared/`, `data/`, `docs/` | Shared | Change with a heads-up; see the contract rules |

The two AI developers meet at exactly one place: Developer 2 generates variants,
Developer 1 simulates them. That split is intentional — the generator should not
also be the judge.

## Contracts

`shared/schemas/*.ts` is the source of truth; `ai/schemas/*.py` is its Pydantic
mirror. TypeScript is `camelCase` on the wire and the Pydantic models use a
camelCase alias generator, so both spellings validate and only camelCase is
serialised.

Both sides are validated against the same fixtures on every test run
(`backend/tests/config.test.ts`, `ai/tests/test_schemas.py`), so drift shows up
in CI rather than in a browser.

Rules: additive only, new fields optional, never rename mid-hackathon, update
the Pydantic mirror and the fixtures in the same PR.

## Mock-first

Every layer degrades to a fixture instead of failing:

| Layer | Mechanism | Trigger |
| --- | --- | --- |
| Frontend | `VITE_USE_MOCKS=true` | default |
| Backend | `withFixtureFallback` | `AI_PROVIDER=mock`, or the AI service is unreachable / times out |
| AI service | `with_fixture_fallback` | mock mode, no key, or an unimplemented provider |

All three read the same JSON in `data/`. Anything served from a fixture is
marked `mock: true` in the payload, `X-ReelLab-Mock: true` in the headers, and
`MOCK_DATA` in the simulation warnings. **Check that flag before believing a
demo.**

This is what makes four-way parallel work real rather than aspirational: nobody
is blocked on anybody.

## Failure handling

One failed persona must never invalidate a run. The engine catches per-persona
exceptions, records the persona with `error` set, excludes it from the averages,
and finishes with `status: 'partial'` (HTTP 207).

| Failure | Behaviour |
| --- | --- |
| Video upload fails | 400 `UPLOAD_FAILED` |
| Unsupported video | 415 `UNSUPPORTED_VIDEO` |
| Empty transcript | Not an error — analyse the frames |
| AI service unreachable | Fixture, marked mock |
| AI timeout | Fixture, marked mock, logged |
| Malformed model output | **Propagates** — a broken prompt must not hide behind a plausible fixture |
| Persona generation fails for a segment | Warning; that segment gets no personas |
| Bottleneck analysis fails | Warning; run still returned without a diagnosis |
| MongoDB down | In-process store; server still boots |

## Observability

Both services emit one structured JSON line per event, with the same field
names. `RunMetadata` — model, model version, prompt version, latency, input and
output tokens, estimated cost, persona count, simulation duration, `mock` — is
attached to anything an AI produced and persisted alongside the result.

That is the whole of it. No dashboards, no tracing backend. When someone wants
graphs, they parse the logs.

## Cost-aware architecture

Persona count is what a run costs. `depth` maps to personas per segment (quick 2,
standard 4, deep 8), `AI_MAX_PERSONAS` is a hard ceiling, and `MAX_CONCURRENCY`
caps parallel calls.

None of the real optimisations are built. The point is that none of them are
blocked:

| Optimisation | Where it goes |
| --- | --- |
| Persona caching | `profiles.cache_key()` + the `Persona` Mongo model |
| Batched inference | Inside `LLMClient` — callers never see it |
| Cheap model for easy personas | `llm.model_for(tier)`, escalate on low confidence |
| Configurable depth | Already there |

Every model call goes through `ai/llm.py`. That is one file to change, not eight.

## Deliberately not here

Kubernetes, Kafka, Redis, event sourcing, auth, RBAC, a repository layer, a
dependency-injection container, microservices beyond these three. This is a
24-hour build. Anything that does not make the demo better is cost.

Redis in particular: nothing needs a job queue yet. If simulation runs grow past
what a request can hold, the first move is to make `POST /simulation/run` return
`{ simulationId, status: 'queued' }` immediately — the frontend already polls
`GET /simulation/:id`, so the change is contained to one service.
