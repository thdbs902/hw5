# Campus Customs — HW5 multi-agent ticket desk

Campus Customs is a small Yale merch shop. This project handles its three open desk tickets with a team of five AI agents:

- **MCP server** (`mcp_server/`, FastMCP): the agents' only window into the shop database.
- **FastAPI backend** (`backend/`): runs the PydanticAI agent team (boss, inventory, accounting, facilities, customer service) and the human-approval routes.
- **React board** (`frontend/`, React + Vite + TypeScript): pick a ticket, watch the agents work, approve payments, and see the checking balance.

Every agent uses **gpt-6-luna** through the **Portkey** gateway (`PORTKEY_API_KEY`). No other model is used. Agents only *prepare* payments. A human approves every payment or purchase, cash never goes negative, and customer, vendor, and landlord messages stay as drafts.

## What's in the repo

| Path | What |
|---|---|
| `data/campus_customs.db` | The original shop database. **Never written to.** |
| `data/campus_customs_new.db` | The working copy that the MCP server, agents, and backend use. It holds the state after my Problem 9 run. |
| `mcp_server/` | `server.py` (17 tools) + `README.md` |
| `backend/` | `main.py` (routes), `agents.py` (team), `models.py`, `prompts/*.md`, `audit.py`, `board.py`, `run_tickets.py` |
| `frontend/` | The React board |
| `output/` | `harness.md`, `desk_tickets.html` (Expected / Actual / Cash / Reflection), `resolved_tickets.json`, `resolved_board.html`, `design.md`, `audit_trail.json` (append-only), `board.json`, `mcp_smoke.json`, `github_url.txt` |
| `AI_prompts.md` | The prompts I gave my vibe coder, problem by problem |
| `.mcp.json` | Connects the MCP server to Claude Code |
| `.env.example` | Template for your own `.env` |

## Setup (once)

You need Python 3.12+ and Node 20+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then put your own PORTKEY_API_KEY in .env
cd frontend && npm install && cd ..
```

`.env` is git-ignored, so never commit a real key. The backend reads `.env` from this folder (or from the parent folder).

## Reset the working database

This puts `data/campus_customs_new.db` back to the original values. The original file is only read, never changed. Any of these works:

```bash
curl -X POST http://localhost:8000/api/reset     # while the backend is running (also logs a reset event to output/audit_trail.json)
```

- or click **↺ Reset working database** on the React board
- or, with the backend stopped: `cp data/campus_customs.db data/campus_customs_new.db`

> **Always reset before a full three-ticket run** (101 → 102 → 103). Otherwise earlier payments, like the paid invoice 501 or the paid rent, change what the agents find, and the cash math won't start from $3,400.

## Start the MCP server

The MCP server talks over stdio, so you don't need to keep it running in a terminal:

- **Backend:** each agent run starts its own copy (`backend/agents.py` → `mcp_server/server.py`).
- **Claude Code:** `.mcp.json` registers it as `campus-customs`. Open Claude Code in this folder and approve the server when asked. If you cloned the repo somewhere else, change the two absolute paths in `.mcp.json` to your own `.venv/bin/python` and `mcp_server/server.py`.
- **By hand** (for a quick check):

```bash
.venv/bin/python mcp_server/server.py
```

It uses `data/campus_customs_new.db` and refuses to start on the original database.

## Start the FastAPI backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

| Route | What it does |
|---|---|
| `GET /api/tickets` | Tickets 101–103 with open/resolved status and the last run's summary |
| `POST /api/tickets/{id}/run` | Run the agent team on one ticket |
| `POST /api/tickets/{id}/reopen?reason=` | A human reopens a ticket that wasn't really finished |
| `GET /api/events` | Recent agent events from `output/audit_trail.json` |
| `GET /api/approvals` / `POST /api/approvals` | Payments waiting for a human, and approve one. **This is the only thing that moves cash.** |
| `GET /api/cash` | Checking balance from `cash_accounts` |
| `POST /api/reset` | Reset the working database |

## Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. The board talks to the backend at http://localhost:8000, and the backend allows the Vite origin.

## A full three-ticket run

1. Reset the working database (see above). Checking should show **$3,400**.
2. On the board, run **101**, then **102**, then **103**, one at a time. Or from the command line: `.venv/bin/python backend/run_tickets.py 101 102 103`.
3. When the team asks, approve or skip each payment or purchase in **Needs your signature**.

My real run is written up in `output/desk_tickets.html` and `output/resolved_board.html`:
- 101 resolved (invoice 501, $840)
- 102 resolved (rent, $2,400)
- 103 left **open / blocked**: the Boss's price was 8 × $50 = $400, and the $264 reprint was refused because only $160 was left

Checking went $3,400 → $160.
