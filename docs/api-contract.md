# ReelLab — API Contract

Base URL: `http://localhost:4000/api/v1`

Types are defined in [`shared/schemas/`](../shared/schemas). This document shows
the wire format; the schemas are authoritative.

## Envelopes

Every 2xx response:

```json
{
  "data": { },
  "mock": false,
  "requestId": "0f3c8e1a-…"
}
```

Every 4xx/5xx response:

```json
{
  "error": { "code": "VALIDATION_FAILED", "message": "…", "details": { } },
  "requestId": "0f3c8e1a-…"
}
```

`mock: true` (and the `X-ReelLab-Mock: true` header) means the payload came from
a development fixture, not a model. It is set whenever `AI_PROVIDER=mock` or the
AI service could not be reached.

### Error codes

| Code | Status | Meaning |
| --- | --- | --- |
| `BAD_REQUEST` | 400 | Malformed request |
| `VALIDATION_FAILED` | 422 | Missing or invalid fields; `details.missing` lists them |
| `NOT_FOUND` | 404 | No such simulation / experiment / reel |
| `UPLOAD_FAILED` | 400 | No file, or the file exceeded `MAX_UPLOAD_MB` |
| `UNSUPPORTED_VIDEO` | 415 | Not a video format we accept |
| `EMPTY_TRANSCRIPT` | 422 | Speech was expected but extraction produced nothing |
| `AI_SERVICE_UNAVAILABLE` | 503 | Python service unreachable |
| `AI_TIMEOUT` | 504 | Model call exceeded the timeout |
| `AI_MALFORMED_OUTPUT` | 502 | Model returned something that did not validate |
| `PERSONA_GENERATION_FAILED` | 502 | Could not generate personas for a segment |
| `SIMULATION_PARTIAL` | 207 | Some personas failed; the run is still usable |
| `DATABASE_UNAVAILABLE` | 503 | Mongo down and the operation needs it |
| `INTERNAL` | 500 | A bug |

---

## `GET /health`

No body. Always 200 while the process is alive — a degraded dependency is
reported in the payload, not by failing the probe.

```json
{
  "status": "ok",
  "service": "reellab-backend",
  "version": "0.1.0",
  "env": "development",
  "uptimeSeconds": 42,
  "dependencies": {
    "mongodb": { "status": "unavailable", "connected": false },
    "aiService": { "url": "http://localhost:8000", "reachable": true }
  },
  "ai": {
    "provider": "mock",
    "multimodalModel": "claude-sonnet-5",
    "reasoningModel": "claude-opus-5",
    "mockMode": true
  },
  "timestamp": "2026-08-21T09:12:04.000Z"
}
```

---

## `POST /audience/discover`

Turn the creator's brief into a graph of sub-niches. → **201**

Request — `AudienceRequest`:

```json
{
  "niche": "fitness",
  "targetAudience": "natural bodybuilding beginners",
  "secondaryAudience": "college students interested in fitness",
  "location": "India",
  "language": "English",
  "creatorGoal": "increase reach among beginners"
}
```

`secondaryAudience` is optional; every other field is required and non-empty.

Response — `data` is an `AudienceGraph`:

```json
{
  "graphId": "graph_fitness_in_001",
  "request": { },
  "segments": [
    {
      "id": "seg_beginner_lifters",
      "name": "Beginner Natural Lifters",
      "description": "0–12 months of consistent training, drug-free by conviction…",
      "parentSegment": "seg_fitness_in",
      "characteristics": ["0-12 months training age", "distrusts supplement pitches"],
      "relevanceScore": 0.94,
      "estimatedShare": 0.34,
      "rationale": "Direct match for the creator's stated primary audience."
    }
  ],
  "adjacency": [
    {
      "fromSegmentId": "seg_college_gym_starters",
      "toSegmentId": "seg_beginner_lifters",
      "spilloverProbability": 0.46
    }
  ]
}
```

`segments` is flat. A segment with `parentSegment: null` is a root niche and is
not simulated directly; the leaves are where behaviour differs.

---

## `POST /reels/upload`

`multipart/form-data`, field name **`reel`**. → **201**

```bash
curl -X POST http://localhost:4000/api/v1/reels/upload \
  -F 'reel=@data/sample_reels/sample_15s.mp4'
```

Response — `data` is a `Reel`:

```json
{
  "id": "reel_a1b2c3d4",
  "filename": "sample_15s.mp4",
  "storagePath": "uploads/1755766324_a1b2c3d4.mp4",
  "sizeBytes": 2418112,
  "uploadedAt": "2026-08-21T09:12:04.000Z",
  "status": "uploaded"
}
```

The backend never opens the video. It hands a **path** to the AI service, which
keeps a 100 MB payload off the hop between the two services.

---

## `POST /reels/analyze`

Multimodal analysis → Content DNA. → **200**

Request — one of:

```json
{ "reelId": "reel_a1b2c3d4" }
{ "videoPath": "data/sample_reels/sample_15s.mp4" }
```

Response — `data` is a `ContentDNA`. Abridged:

```json
{
  "videoId": "reel_001",
  "durationSeconds": 34,
  "transcript": "So today I want to talk about something…",
  "topic": "Three common beginner training mistakes",
  "hook": {
    "text": "So today I want to talk about something that I think a lot of people get wrong.",
    "durationSeconds": 4.2,
    "type": "soft intro",
    "strength": 0.31
  },
  "tone": "instructional",
  "emotion": "reflective",
  "scenes": [
    { "index": 0, "startSeconds": 0, "endSeconds": 4.2, "description": "Static mid-shot…", "shotType": "talking head", "energy": 0.22 }
  ],
  "visualFeatures": {
    "cutsPerSecond": 0.12,
    "hasOnScreenText": true,
    "facePresence": 0.79,
    "dominantColors": ["#2b2b30"],
    "productionQuality": 0.66
  },
  "audioFeatures": { "hasSpeech": true, "hasMusic": false, "wordsPerMinute": 158, "energy": 0.41, "language": "English" },
  "cta": { "present": true, "text": "Follow for more", "atSecond": 31, "type": "follow" },
  "warnings": ["Hook occupies 4.2s, longer than the 3s window most viewers allow."]
}
```

Content DNA describes what the reel **is**, not how good it is. Scoring happens
in simulation.

---

## `POST /simulation/run`

→ **201**, or **207** when `status` is `partial`.

Request — `SimulationRequest`:

```json
{
  "reelId": "reel_001",
  "graphId": "graph_fitness_in_001",
  "depth": "standard"
}
```

`reelId` **or** `contentDna` is required. `depth` is `quick` | `standard` |
`deep` and controls personas per segment (2 / 4 / 8) — the main cost lever.

Response — `data` is a `SimulationResult`. Abridged:

```json
{
  "simulationId": "sim_001",
  "status": "completed",
  "reelId": "reel_001",
  "graphId": "graph_fitness_in_001",
  "overallScore": 0.38,
  "confidence": 0.64,

  "audienceResults": [
    {
      "personaId": "persona_003",
      "watchProbability": 0.18,
      "completionProbability": 0.05,
      "likeProbability": 0.06,
      "saveProbability": 0.02,
      "shareProbability": 0.03,
      "commentProbability": 0.02,
      "swipeTime": 2.6,
      "action": "swipe",
      "reason": "Static shot, slow voice, and the first sentence is just throat-clearing.",
      "confidence": 0.86
    }
  ],

  "propagationWaves": [
    { "wave": 0, "segmentIds": ["seg_beginner_lifters"], "reach": 1000, "passThroughRate": 0.08, "terminated": false, "note": "Seed audience." },
    { "wave": 2, "segmentIds": [], "reach": 3, "passThroughRate": 0, "terminated": true, "note": "Cascade dies." }
  ],

  "audienceSegmentResults": [
    {
      "segmentId": "seg_college_gym_starters",
      "segmentName": "College Gym Starters",
      "score": 0.24,
      "averageWatchProbability": 0.3,
      "averageCompletionProbability": 0.12,
      "shareRate": 0.06,
      "saveRate": 0.12,
      "personaCount": 2,
      "confidence": 0.78,
      "verdict": "weak"
    }
  ],

  "bottlenecks": [
    {
      "id": "bn_001",
      "stage": "hook",
      "segmentIds": ["seg_college_gym_starters"],
      "description": "Four of five personas decided before the first point was named.",
      "likelyCause": "The opening states a category, not a stake.",
      "severity": 0.82,
      "confidence": 0.79
    }
  ],

  "warnings": [{ "code": "LOW_PERSONA_COUNT", "message": "Only 5 personas…", "severity": "warning" }],
  "createdAt": "2026-08-21T09:12:04.000Z",
  "completedAt": "2026-08-21T09:12:51.000Z",
  "metadata": { "model": "fixture", "personaCount": 5, "simulationDurationMs": 47000, "mock": true }
}
```

`action` is one of `swipe`, `watch`, `complete`, `like`, `save`, `share`,
`comment`. `verdict` is `strong` | `mixed` | `weak`. `stage` is `hook`,
`retention`, `payoff`, `cta` or `propagation`.

The probabilities are independent estimates, **not** a distribution — they do
not sum to 1.

> Runs are synchronous today. If they grow past a few seconds this becomes
> `{ simulationId, status: "queued" }` and clients poll `GET /simulation/:id`.
> The frontend already polls, so nothing else changes.

---

## `GET /simulation/:id`

→ **200**, `data` is a `SimulationResult`. **404** if unknown.

`sim_001` always resolves — it is the fixture, so a frontend developer can hit
this on a cold server.

---

## `POST /experiments`

Generate counterfactual variants and re-simulate them. → **201**

Request — `ExperimentRequest`:

```json
{
  "originalSimulationId": "sim_001",
  "modificationType": "hook",
  "instruction": "Try a question-led hook that names the beginner's frustration",
  "variantCount": 2
}
```

`modificationType` is `hook` | `duration` | `cta` | `tone` | `pacing` |
`audience`. `variantCount` is 1–5, default 2. **404** if the baseline simulation
does not exist — comparing against nothing is worse than not comparing.

Response — `data` is a `CounterfactualExperiment`. Abridged:

```json
{
  "experimentId": "exp_001",
  "originalSimulationId": "sim_001",
  "hypothesis": "The reel is lost in the first 3 seconds, not in its content.",
  "modificationType": "hook",
  "variants": [
    {
      "id": "var_b",
      "label": "Variant B — arguable claim hook",
      "changeSummary": "Open on a contestable claim, burn in captions from frame one.",
      "proposedChange": "Changing your split every two weeks is why you look the same as last year.",
      "simulationId": "sim_003",
      "score": 0.68
    }
  ],
  "comparison": [
    {
      "variantId": "var_b",
      "scoreDelta": 0.3,
      "segmentDeltas": { "seg_college_gym_starters": 0.52, "seg_budget_home_trainees": -0.09 },
      "biggestGainSegmentId": "seg_college_gym_starters",
      "biggestLossSegmentId": "seg_budget_home_trainees",
      "confidence": 0.58
    }
  ],
  "recommendation": {
    "winningVariantId": "var_b",
    "reasoning": "Variant B clears the 3-second window and gives the college segment something to forward.",
    "confidence": 0.58,
    "caveats": ["Confidence is below 0.6; the gap is within the noise of a 5-persona run."]
  },
  "status": "completed",
  "createdAt": "2026-08-21T09:20:11.000Z"
}
```

`winningVariantId` is `null` when no variant beat the original. That is a real
result, not a failure.

---

## `GET /experiments/:id`

→ **200**, `data` is a `CounterfactualExperiment`. **404** if unknown.

---

## `GET /results/:id`

Convenience lookup for the results dashboard, which has an id from a URL and
does not always know what kind it is. Resolves either, tagged with `kind`:

```json
{ "data": { "kind": "simulation", "simulation": { } }, "mock": true }
{ "data": { "kind": "experiment", "experiment": { } }, "mock": true }
```

**404** if neither matches. `GET /simulation/:id` and `GET /experiments/:id`
remain the precise routes.

---

## AI service (internal)

The Node backend is the only client. Base URL `http://localhost:8000`.

| Method | Path | In → Out |
| --- | --- | --- |
| GET | `/health` | — → liveness + capabilities |
| POST | `/ai/audience/discover` | `AudienceRequest` → `AudienceGraph` |
| POST | `/ai/personas/generate` | `PersonaGenerationRequest` → `Persona[]` |
| POST | `/ai/video/analyze` | `VideoAnalysisRequest` → `ContentDNA` |
| POST | `/ai/simulation/run` | `SimulationRequest` → `SimulationResult` |
| POST | `/ai/counterfactual/generate` | `ExperimentRequest` → `CounterfactualExperiment` |
| POST | `/ai/evaluation/run` | `EvaluationRequest` → `EvaluationMetrics` |

Every AI response is wrapped:

```json
{ "data": { }, "mock": true, "metadata": { "model": "fixture", "latencyMs": 0, "mock": true } }
```

`aiClient.ts` unwraps `data` and forwards `metadata` to the observability log.
Live OpenAPI docs at http://localhost:8000/docs.
