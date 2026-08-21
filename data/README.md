# `data/` — Development fixtures

Everything here is a **development fixture**, not AI output and not product
logic. Fixtures exist so that no developer has to wait for another developer.

Both the Node backend and the Python AI service load these files at runtime, so
they are the one place a mock value lives. Do not copy them into application
code.

| File | Contract | Loaded by |
| --- | --- | --- |
| `mock_personas/audience_graph.json` | `AudienceGraph` (4 segments + adjacency) | backend mock service, AI audience module |
| `mock_personas/personas.json` | `Persona[]` (5 personas) | backend mock service, AI persona module |
| `mock_personas/content_dna.json` | `ContentDNA` | AI simulation module (Dev 1 works against this) |
| `mock_personas/simulation_result.json` | `SimulationResult` | backend mock service, frontend mocks (Dev 3 works against this) |
| `mock_personas/counterfactual_experiment.json` | `CounterfactualExperiment` | backend mock service, frontend mocks |
| `evaluation/historical_reels.json` | Evaluation ground truth | `ai/evaluation/` harness |
| `sample_reels/` | Small local video samples (gitignored) | Dev 2's video pipeline |

## Rules

1. **Fixtures are part of the contract.** If you add a required field to a
   schema in `shared/schemas/` or `ai/schemas/`, update the fixture in the same
   pull request or you break three other people's local setup.
2. **Every fixture is internally consistent.** Persona ids in
   `simulation_result.json` match `personas.json`; segment ids match
   `audience_graph.json`. Keep it that way — the frontend joins on those ids.
3. **Mock output is always labelled.** Anything the API serves from here is
   marked `"mock": true` in its `RunMetadata`, and the backend sets an
   `X-ReelLab-Mock: true` response header. Nobody should ever demo a fixture
   believing it came from a model.
4. **No real videos, no real creator data** in Git.

## The story these fixtures tell

They are not random. The fixture reel is a genuinely mediocre one: a 34-second
explainer with a 4.2-second soft intro. Four of the five personas bail before
the content starts, the cascade dies at wave 2, and the counterfactual shows a
claim-first hook recovering the college segment. That gives the frontend a
realistic-looking failure to render and gives the simulation team a target
behaviour to reproduce with real models.
