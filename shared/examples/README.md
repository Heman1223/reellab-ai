# `shared/examples/`

Canonical **request** payloads for the ReelLab API. These are what a client
sends; they are referenced verbatim by [`docs/api-contract.md`](../../docs/api-contract.md)
and used by the backend smoke tests.

Response-side fixtures (segments, personas, Content DNA, simulation results,
experiments) live in [`data/`](../../data) so the Python AI service and the
Node backend can load the same files at runtime.

| File | Contract |
| --- | --- |
| `audience-request.example.json` | `AudienceRequest` |
| `simulation-request.example.json` | `SimulationRequest` |
| `experiment-request.example.json` | `ExperimentRequest` |
