# ReelLab — Failure Log

Where model failures and system limitations get written down.

**Why this file exists.** A simulation that is wrong in a way we understand is
far more valuable than one that is wrong in a way we do not. At hour 20 the
difference between a good demo and a bad one is usually being able to say "yes,
it breaks there, here is why, here is what we would do about it."

Log a failure when the system produced something wrong, not merely something you
did not like. Add new entries at the top.

## Template

Copy this block for each failure.

```markdown
### FAIL-00X — <one-line summary>

**Date:**

**Scenario:**
What was being run, with what input.

**Expected:**
What should have happened.

**Actual:**
What actually happened. Paste the output.

**Root Cause:**
Why. "The model was wrong" is not a root cause — say what about the prompt,
the input, or the aggregation produced the wrong answer.

**Model / Component:**
e.g. `claude-opus-5`, prompt `viewer-agent-v0`, `ai/simulation/agents/`

**Fix:**
What was changed. "Not fixed" is a valid answer.

**Remaining Limitation:**
What is still wrong after the fix. Be honest — this is the field that makes the
log worth keeping.
```

---

## Entries

### FAIL-000 — Example entry (delete once real ones exist)

**Date:** 2026-08-21

**Scenario:**
Ran a `standard` simulation against `data/mock_personas/content_dna.json` with
the fixture audience graph, with `AI_PROVIDER=mock`.

**Expected:**
A `SimulationResult` clearly marked as fixture-backed.

**Actual:**
Exactly that — `metadata.mock = true` and a `MOCK_DATA` warning. Working as
intended; this entry exists to show the format.

**Root Cause:**
n/a.

**Model / Component:**
`ai/simulation/engine/engine.py`, fixture path.

**Fix:**
n/a.

**Remaining Limitation:**
Nothing in the repository has yet been validated against a real model. Every
prompt in `ai/` is a first draft written without a single response to look at.
Expect the first real run to expose schema mismatches and over-confident
personas.

---

## Known limitations at setup time

Not failures — things we already know are not built. Kept here so nobody
rediscovers them at hour 15.

| Area | Limitation |
| --- | --- |
| Models | `LLMClient.complete_json` is not implemented. Every AI path falls back to fixtures. |
| Video | FFmpeg extraction and transcription are `NotImplementedError`. |
| Propagation | `AMPLIFICATION = 12.0` and `SEED_REACH = 1000` are invented numbers with no empirical basis. |
| Aggregation | The segment-score weights (0.35 / 0.40 / 0.15 / 0.10) are a guess, not a finding. |
| Verdict thresholds | `STRONG_THRESHOLD = 0.6`, `WEAK_THRESHOLD = 0.35` — also a guess. |
| Evaluation | `false_positives` / `false_negatives` are unimplemented and return `null`, not `0`. |
| Evaluation data | `data/evaluation/historical_reels.json` is placeholder, not real analytics. |
| Persistence | Mongoose models exist but nothing writes to them yet — state is in-process and lost on restart. |
| Confidence | Sample-size discounting is a heuristic; it has never been checked against anything. |
| Cost | No caching, no batching, no model-tier escalation. A `deep` run makes one model call per persona. |

Every one of these is a legitimate thing to say out loud in a demo. Pretending
otherwise is how a good project loses credibility in the Q&A.
