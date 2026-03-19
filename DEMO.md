# Concurrent Agent Demo

This demo shows two AI agents running simultaneously, each modifying different files with zero conflict.

**What happens:**
- **API Agent** adds a new `GET /categories` endpoint → writes to `app/main.py`
- **Core Agent** adds a new `networking` category → writes to `app/rules/keyword.py`
- Both run at the same time. Neither touches the other's file.

---

## Prerequisites

```bash
pip install -r requirements.txt
```

Make sure `claude` CLI is installed and authenticated:
```bash
claude --version
```

---

## Run the Demo

### Step 1 — Reset to clean state
```bash
python demo/reset.py
```

### Step 2 — Confirm baseline (nothing exists yet)
```bash
python demo/verify_before.py
```
Expected: `/categories` route does NOT exist, `networking` category does NOT exist.

### Step 3 — Run both agents concurrently
```bash
bash run_agents.sh
```
Watch both agents work simultaneously in the terminal output.

### Step 4 — Verify both agents delivered
```bash
python demo/verify_after.py
```
Expected: `/categories` route EXISTS, `networking` category EXISTS, determinism holds.

### Step 5 — Full test suite still passes
```bash
pytest
```
Expected: 26 passed, 0 failed.

---

## What to Look For

**In Step 3 output** — both agents print progress interleaved. They finish independently.

**In Step 4 output:**
```
[PASS] /categories route EXISTS
[PASS] networking category EXISTS
[PASS] GET /categories returns 200
[PASS] Networking ticket returns 200
[PASS] Determinism still holds after changes
```

**Why no conflicts?**
- API Agent owns `app/main.py` only
- Core Agent owns `app/rules/keyword.py` only
- Shared contracts (`models.py`, `base.py`) are read-only — neither agent touches them

---

## Reset and Repeat

```bash
python demo/reset.py && bash run_agents.sh
```

---

## Alternative — Run Agents in Separate Terminals

If you prefer to watch each agent's output independently, open two terminal windows and run simultaneously:

**Terminal 1 — API Agent**
```bash
cd /path/to/repo
claude "Read agents/agent_api.md and prompts/add_endpoint.md. Add a GET /categories endpoint that returns the list of supported ticket category keys from the engine. Run verification."
```

**Terminal 2 — Core Agent** (start at the same time)
```bash
cd /path/to/repo
claude "Read agents/agent_core.md and prompts/add_strategy.md. Add a 'networking' category to KeywordStrategy with keywords: dns, network, firewall, vpn, proxy, ssl, certificate, timeout, connection, socket, port, ip. Preserve determinism. Run verification."
```

Then verify once both finish:
```bash
python demo/verify_after.py
pytest
```
