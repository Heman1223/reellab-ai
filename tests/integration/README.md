# Integration tests

Cross-service checks. Unit tests live with their app
([`backend/tests/`](../../backend/tests), [`ai/tests/`](../../ai/tests)).

## `smoke.sh`

Walks the full product flow against a running backend, the same way the frontend
would: health → audience discovery → reel analysis → simulation → fetch by id →
counterfactual experiment.

```bash
# from the repo root, with the backend running on :4000
bash tests/integration/smoke.sh

# against a different host
API=http://staging.example.com/api/v1 bash tests/integration/smoke.sh
```

Needs only `curl` and `bash` — no test framework, no install step.

**MongoDB and the AI service are optional.** Without them the backend serves
fixtures and this still passes. That is deliberate: it verifies the mock-first
guarantee holds, which is what four people are depending on.

To check the *integrated* path, start the AI service, set `AI_PROVIDER` to a
real provider in `.env`, and confirm `mockMode` is `false` in the health output
the script prints.

## Adding a check

Follow the existing shape:

```bash
check "<what it proves>" <expected-status> "$(status_of "$API/<path>")"
```

Assert on the contract — status codes and the presence of required fields — not
on specific scores. Score values change every time someone touches a prompt, and
a test that fails on that is a test people learn to ignore.
