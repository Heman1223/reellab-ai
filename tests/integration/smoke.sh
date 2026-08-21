#!/usr/bin/env bash
#
# ReelLab — end-to-end smoke test.
#
#   bash tests/integration/smoke.sh
#
# Walks the whole product flow against a running backend, exactly as the
# frontend would. Run it after any change that crosses a service boundary.
#
# Prerequisites: backend on :4000. The AI service and MongoDB are optional —
# without them the backend serves fixtures, and this script still passes. That
# is the point.

set -uo pipefail

API="${API:-http://localhost:4000/api/v1}"
PASS=0
FAIL=0

green() { printf '\033[32m✓\033[0m %s\n' "$1"; }
red()   { printf '\033[31m✗\033[0m %s\n' "$1"; }

check() {
  local label="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    green "$label"
    PASS=$((PASS + 1))
  else
    red "$label (expected $expected, got $actual)"
    FAIL=$((FAIL + 1))
  fi
}

status_of() {
  curl -s -o /dev/null -w '%{http_code}' "$@"
}

printf '\nReelLab smoke test → %s\n\n' "$API"

# --- 1. health ---------------------------------------------------------------
check "health responds 200" 200 "$(status_of "$API/health")"

HEALTH=$(curl -s "$API/health")
if printf '%s' "$HEALTH" | grep -q '"status":"ok"'; then
  green "health reports ok"; PASS=$((PASS + 1))
else
  red "health did not report ok"; FAIL=$((FAIL + 1))
fi

if printf '%s' "$HEALTH" | grep -q '"mockMode":true'; then
  printf '  \033[33m!\033[0m mock mode is ON — responses come from fixtures.\n'
fi

# --- 2. audience discovery ---------------------------------------------------
check "audience/discover accepts a valid brief" 201 \
  "$(status_of -X POST "$API/audience/discover" \
      -H 'Content-Type: application/json' \
      -d @shared/examples/audience-request.example.json)"

check "audience/discover rejects an incomplete brief" 422 \
  "$(status_of -X POST "$API/audience/discover" \
      -H 'Content-Type: application/json' -d '{"niche":"fitness"}')"

# --- 3. reel analysis --------------------------------------------------------
check "reels/analyze returns Content DNA" 200 \
  "$(status_of -X POST "$API/reels/analyze" \
      -H 'Content-Type: application/json' \
      -d '{"videoPath":"data/sample_reels/sample.mp4"}')"

# --- 4. simulation -----------------------------------------------------------
SIM=$(curl -s -X POST "$API/simulation/run" \
  -H 'Content-Type: application/json' \
  -d '{"reelId":"reel_001","depth":"quick"}')

SIM_ID=$(printf '%s' "$SIM" | sed -n 's/.*"simulationId":"\([^"]*\)".*/\1/p')

if [ -n "$SIM_ID" ]; then
  green "simulation/run returned $SIM_ID"; PASS=$((PASS + 1))
else
  red "simulation/run did not return a simulationId"; FAIL=$((FAIL + 1))
fi

for field in overallScore audienceResults propagationWaves audienceSegmentResults bottlenecks; do
  if printf '%s' "$SIM" | grep -q "\"$field\""; then
    green "result contains $field"; PASS=$((PASS + 1))
  else
    red "result is missing $field"; FAIL=$((FAIL + 1))
  fi
done

check "simulation/run rejects an empty body" 422 \
  "$(status_of -X POST "$API/simulation/run" -H 'Content-Type: application/json' -d '{}')"

if [ -n "$SIM_ID" ]; then
  check "simulation/:id returns the run" 200 "$(status_of "$API/simulation/$SIM_ID")"
  check "results/:id resolves the run" 200 "$(status_of "$API/results/$SIM_ID")"
fi

check "simulation/:id 404s on an unknown id" 404 "$(status_of "$API/simulation/sim_nope")"

# --- 5. counterfactual -------------------------------------------------------
if [ -n "$SIM_ID" ]; then
  EXP=$(curl -s -X POST "$API/experiments" \
    -H 'Content-Type: application/json' \
    -d "{\"originalSimulationId\":\"$SIM_ID\",\"modificationType\":\"hook\",\"variantCount\":2}")

  if printf '%s' "$EXP" | grep -q '"variants"'; then
    green "experiments returned variants"; PASS=$((PASS + 1))
  else
    red "experiments did not return variants"; FAIL=$((FAIL + 1))
  fi

  if printf '%s' "$EXP" | grep -q '"recommendation"'; then
    green "experiments returned a recommendation"; PASS=$((PASS + 1))
  else
    red "experiments did not return a recommendation"; FAIL=$((FAIL + 1))
  fi
fi

check "experiments 404s on a missing baseline" 404 \
  "$(status_of -X POST "$API/experiments" \
      -H 'Content-Type: application/json' \
      -d '{"originalSimulationId":"sim_nope","modificationType":"hook"}')"

# --- summary -----------------------------------------------------------------
printf '\n%d passed, %d failed\n\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
