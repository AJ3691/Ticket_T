#!/usr/bin/env bash

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "▶ Starting concurrent agents..."

# --- Agent 1: API ---
(
  cd "$PROJECT_DIR"
  echo "→ [API Agent] Adding /categories endpoint..."
  claude --print --dangerously-skip-permissions "Read agents/agent_api.md and prompts/add_endpoint.md. Add a GET /categories endpoint that returns the list of supported ticket category keys from the engine. Run verification."
  echo "✓ [API Agent] Done"
) &

PID_API=$!

# --- Agent 2: Core ---
(
  cd "$PROJECT_DIR"
  echo "→ [Core Agent] Adding networking category..."
  claude --print --dangerously-skip-permissions "Read agents/agent_core.md and prompts/add_strategy.md. Add a 'networking' category to KeywordStrategy with keywords: dns, network, firewall, vpn, proxy, ssl, certificate, timeout, connection, socket, port, ip. Preserve determinism. Run verification."
  echo "✓ [Core Agent] Done"
) &

PID_CORE=$!

# --- Wait for both ---
echo "⏳ Waiting for agents to complete..."

wait $PID_API
STATUS_API=$?

wait $PID_CORE
STATUS_CORE=$?

# --- Summary ---
echo ""
echo "===== AGENT RUN SUMMARY ====="

if [ $STATUS_API -eq 0 ]; then
  echo "✓ API Agent succeeded"
else
  echo "✗ API Agent failed"
fi

if [ $STATUS_CORE -eq 0 ]; then
  echo "✓ Core Agent succeeded"
else
  echo "✗ Core Agent failed"
fi

# --- Final verification ---
echo ""
echo "▶ Running full test suite..."
cd "$PROJECT_DIR"
pytest -v

echo "✓ All done"