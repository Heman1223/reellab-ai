# ReelLab — AI Service

FastAPI + Pydantic. **Developer 1** owns audience, personas, simulation,
propagation and evaluation. **Developer 2** owns video analysis and
counterfactuals.

This is where the product's intelligence lives. The Node backend moves data
around; this service decides things.

## Run it

```bash
cd ai
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Then:

- http://localhost:8000/health — liveness plus an honest capability report
- http://localhost:8000/docs — interactive OpenAPI, generated from the Pydantic
  contracts

Run pytest from inside `ai/` (that is where `pytest.ini` sets `pythonpath`):

```bash
cd ai
python -m pytest
```

## It runs with no API key

`AI_PROVIDER=mock` (the default) means no model is ever called and every
endpoint serves the fixtures in `data/`. Everything so served is marked
`"mock": true` in the response envelope and logged as `serving_fixture`.

That is what lets four people start at once. It is also a trap at demo time:
**check `mockMode` on `/health` before believing a result.**

## Layout

```
ai/
├── main.py               FastAPI app: routes in, envelopes out. No logic.
├── config.py             Settings, read from the root .env
├── llm.py                THE model boundary — every model call goes through here
├── fixtures.py           Loads data/ fixtures (same files the backend reads)
├── errors.py             Typed failure modes
├── logging_utils.py      Structured JSON logs, matching the backend's format
├── schemas/              Pydantic mirror of shared/schemas/*.ts
│
├── audience/             ┐
│   ├── discovery/        │ AI: niche → sub-niches that behave differently
│   └── segmentation/     │ deterministic: graph shaping and validation
├── personas/             │
│   ├── generation/       │ AI: segment → synthetic viewers
│   └── profiles/         │ deterministic: caching keys, budget selection
├── simulation/           │ Developer 1
│   ├── agents/           │ AI: one persona watching one reel
│   ├── behavior/         │ deterministic aggregation + AI bottleneck reflection
│   └── engine/           │ orchestration
├── propagation/engine/   │ deterministic: the cascade
├── evaluation/           ┘ does any of this predict reality?
│
├── video_analysis/       ┐
│   ├── preprocessing/    │ FFmpeg frame + audio extraction
│   ├── transcription/    │ speech to text
│   └── multimodal/       │ AI: frames + audio → Content DNA
├── counterfactual/       │ Developer 2
│   ├── generation/       │ AI: bottleneck → specific proposed changes
│   └── experiments/      ┘ deterministic comparison + AI recommendation
│
└── tests/
```

## The AI / deterministic split

This is the most important design rule in the repo, and it is what stops
ReelLab from being a hard-coded score wearing an AI costume.

**AI decides:** which sub-niches exist, what each persona is like, what the reel
actually is, whether a given persona keeps watching and why, what the bottleneck
is, what to change.

**Code decides:** how many personas to run, in what order, with what
concurrency; how per-persona probabilities average into a segment score; where a
share lands and whether the cascade survives; what the deltas between two runs
are; what gets persisted.

The test: if you swapped the model for a coin flip, `overall_score` would still
compute — it would just be meaningless. That is the correct dependency
direction.

## Endpoints

| Method | Path | Function |
| --- | --- | --- |
| GET | `/health` | liveness + capabilities |
| POST | `/ai/audience/discover` | `discover_audience(request) -> AudienceGraph` |
| POST | `/ai/personas/generate` | `generate_personas(segment, count) -> list[Persona]` |
| POST | `/ai/video/analyze` | `analyze_video(video_path) -> ContentDNA` |
| POST | `/ai/simulation/run` | `run_simulation(request) -> SimulationResult` |
| POST | `/ai/counterfactual/generate` | `run_experiment(request) -> CounterfactualExperiment` |
| POST | `/ai/evaluation/run` | `evaluate_predictions(predictions, dataset) -> EvaluationMetrics` |

Every response is wrapped:

```json
{ "data": { }, "mock": true, "metadata": { "model": "fixture", "mock": true } }
```

`backend/src/services/aiClient.ts` unwraps `data` and forwards `metadata` to the
observability log.

## Wiring up a real model

1. `pip install anthropic` (uncomment it in `requirements.txt`).
2. Implement `LLMClient.complete_json` in [`llm.py`](llm.py). The `TODO` there
   spells out the steps.
3. Set `AI_PROVIDER=anthropic` and `AI_API_KEY=...` in the root `.env`.

Until step 2 is done, `complete_json` raises `NotImplementedError` and
`with_fixture_fallback` catches it, so setting the key early degrades to
fixtures rather than breaking. Nothing else in the codebase needs to change —
that is the whole reason the boundary exists.

## Failure policy

| Failure | What happens |
| --- | --- |
| No API key | Fixture, marked `mock` |
| Provider not implemented | Fixture, marked `mock`, logged |
| One persona's call fails | Recorded with `error`, excluded from averages, run continues as `partial` |
| Persona generation fails for a segment | Warning, that segment gets no personas, run continues |
| Bottleneck analysis fails | Warning, empty `bottlenecks`, run still returned |
| Model returns invalid JSON | `MalformedModelOutputError` **propagates** — a broken prompt must not be hidden behind a plausible fixture |
| No personas at all | 422. There is genuinely nothing to simulate |
| Video missing or wrong format | `UnsupportedVideoError` (415) |
| Silent reel | Empty transcript, **not** an error — analyse the frames |

## Cost

Persona count is the main driver of what a run costs: `depth` maps to personas
per segment (`quick` 2, `standard` 4, `deep` 8), `AI_MAX_PERSONAS` is a hard
ceiling, and `MAX_CONCURRENCY` in the engine caps parallel calls.

None of the real optimisations are built — persona caching, batched inference,
a cheap model for low-uncertainty personas escalating to a stronger one. The
interfaces are shaped so each is a contained change: `profiles.cache_key()`
exists for the first, `llm.model_for(tier)` for the third.
