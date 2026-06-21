#!/usr/bin/env bash
# Verify Slack credentials loaded by the backend.
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"

echo "== Slack auth.test via backend =="
curl -sS "$BASE/admin/slack/test" | python3 -m json.tool

if [[ "${2:-}" == "--provision" ]]; then
  echo ""
  echo "== Creating demo Slack channels =="
  curl -sS "$BASE/admin/slack/test?provision=true" | python3 -m json.tool
fi
