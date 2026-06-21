#!/usr/bin/env bash
# Connect OrchestrateAI MCP to Poke.
#
# Option A — poke tunnel (local dev, requires one-time login):
#   npx poke@latest login          # once, in your terminal
#   ./scripts/connect-poke.sh tunnel
#
# Option B — ngrok / remote URL (no poke login):
#   ./scripts/connect-poke.sh remote
#   Then open the printed URL and add the MCP integration in Poke settings.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MCP_URL="${MCP_URL:-http://localhost:8000/mcp}"
NGROK_URL="${NGROK_URL:-https://stegosaur-setting-mammogram.ngrok-free.dev/mcp}"
NAME="${POKE_MCP_NAME:-OrchestrateAI}"

cmd="${1:-tunnel}"

health() {
  curl -sf "http://127.0.0.1:8000/health" >/dev/null \
    || { echo "Backend not running. Start: uvicorn app.main:app --host 127.0.0.1 --port 8000"; exit 1; }
}

case "$cmd" in
  tunnel)
    health
    echo "Starting Poke tunnel → $MCP_URL"
    echo "If you see 'Not logged in', run: npx poke@latest login"
    exec npx poke@latest tunnel "$MCP_URL" -n "$NAME"
    ;;
  remote)
    health
    echo "Register this MCP URL in Poke (no tunnel needed if ngrok is running):"
    echo "  $NGROK_URL"
    echo ""
    echo "1. Open https://poke.com/settings/connections/integrations/new"
    echo "2. Name: $NAME"
    echo "3. MCP Server URL: $NGROK_URL"
    echo "4. Transport: Streamable HTTP"
    echo ""
    echo "Smoke test (initialize):"
    curl -sL -X POST "$NGROK_URL" \
      -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"1.0"}}}' \
      | head -3
    echo ""
    ;;
  *)
    echo "Usage: $0 {tunnel|remote}"
    exit 1
    ;;
esac
