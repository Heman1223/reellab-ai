"""Test environment guard rails for the AI service.

**Tests must never reach a real model.** `ai/config.py` loads the repo-root
`.env` at import time, so once a real `AI_API_KEY` is present every test that
exercises a module would start making billable calls — and on a free Gemini key
would exhaust the entire daily quota in one `pytest` run.

This file forces mock mode before anything else imports `config`. pytest loads
`conftest.py` ahead of the test modules, and `python-dotenv` does not override
variables that are already set, so these win over `.env`.

Mirrors `backend/tests/setup.ts`, which does the same job for the Node suite.

If you are deliberately testing a live provider, do it in a scratch script
outside `tests/` — not by weakening this file.
"""

from __future__ import annotations

import os

os.environ["AI_PROVIDER"] = "mock"
os.environ["AI_API_KEY"] = ""
os.environ["AI_LOG_LEVEL"] = "error"
# Point at a port nothing listens on, so an accidental HTTP call fails fast
# rather than hanging the suite.
os.environ["AI_SERVICE_URL"] = "http://127.0.0.1:59998"
