# HW5 Harness — Campus Customs

## Data files

- `data/campus_customs.db` — the original. Never written to.
- `data/campus_customs_new.db` — the working copy every agent, MCP tool, and the backend read and write. Made with a plain file copy of the original (same SHA-1 checksum at copy time). Reset it to the original before the full three-ticket run.

Shop "today" is **2026-08-31** (from `desk.date_today`), not the computer's clock.

## Tables

### `desk` (1 row)
Fields: `date_today`, `notes`
Why it matters: gives agents the shop's "today" so due dates and lateness are judged against 2026-08-31.

### `inventory` (10 rows)
Fields: `sku`, `name`, `size`, `qty`, `location` — key is (`sku`, `size`)
Why it matters: the Inventory agent checks stock per size here before anything is promised to a customer.

### `pricing` (4 rows)
Fields: `sku` (key), `unit_cost`, `list_price`
Why it matters: tells agents the normal price and the floor (cost) a discount must never go below.

### `vendors` (3 rows)
Fields: `id` (key), `name`, `specialty`, `lead_days`
Why it matters: tells agents who supplies what and how many days a reprint or delivery takes. Agents never contact them for real.

### `leases` (1 row)
Fields: `id` (key), `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`
Why it matters: the Facilities agent finds the rent amount and due date here.

### `cash_accounts` (1 row)
Fields: `name` (key), `balance`, `date`
Why it matters: the Accounting agent checks this before any payment. The balance can never go below 0, and it only goes down in this homework.

### `payments` (0 rows)
Fields: `id` (key), `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`
Why it matters: the record of every payment. A row is written only after a human approves (`approved_by`).

### `invoices` (1 row)
Fields: `id` (key), `vendor_id` → `vendors.id`, `amount`, `due_date`, `status`, `description`
Why it matters: bills the shop owes vendors; Accounting pays them, after human approval, if there is enough cash.

### `tickets` (3 rows, all `open`)
Fields: `id` (key), `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id` → `leases.id`, `invoice_id` → `invoices.id`, `status`, `notes`, `created_at`
Why it matters: the work queue. The Boss agent reads a ticket and delegates using its links to the other tables.

## Starting values (original DB)

| What | Value |
|---|---|
| Cash (`checking`) | $3,400.00 on 2026-08-31 |
| Invoice 501 | $840.00 to Bulldog Print Co, due 2026-08-28 (already 3 days late), open — "Rush reprint CC-TEE-WHITE S" |
| Lease 1 rent | $2,400.00 to Elm City Properties, due 2026-09-02 |
| Payments | none yet |

## The three open tickets

| Ticket | Type | Ask | Related tables |
|---|---|---|---|
| 101 | `customer_order` | Tauhid Zaman wants 1 Classic Bulldog Tee (`CC-TEE-WHITE`), size S | `inventory` (S = **0** in stock), `pricing` ($28 list), `invoices` 501 ($840 overdue reprint of that tee), `vendors` 1 (Bulldog Print Co, 5 lead days), `cash_accounts`, `payments` |
| 102 | `rent_notice` | Elm City Properties: rent due in 2 days | `leases` 1 ($2,400, due 2026-09-02), `desk` (today), `cash_accounts`, `payments` |
| 103 | `price_override` | Yale AI Club wants 20 Basic Hoodies (`CC-HOOD-NAVY`), size M, at a bulk discount | `inventory` (M = **8** in stock), `pricing` ($22 cost, $58 list), `vendors` 1 (reprint, 5 lead days) |

How the links work: `lease_id` and `invoice_id` are real foreign keys; `sku`/`size` are plain text that match `inventory` (`sku` + `size`) and `pricing` (`sku`) by value, so tools must look them up by those values.

Cash check: paying both invoice 501 ($840) and rent ($2,400) costs $3,240 and leaves $160 — enough, but just barely.

## MCP server (Problem 3)

Code: `mcp_server/server.py` (FastMCP, server name `campus-customs`). It opens `data/campus_customs_new.db` **read-only** and returns rows exactly as stored; if nothing matches it returns `found: false` instead of guessing.

| Tool | Table it reads | Unlocks ticket | Why it is useful |
|---|---|---|---|
| `check_stock(sku, size)` | `inventory` | 101 | Shows the tee in size S has 0 on the shelf, so the order cannot ship from stock today. |
| `get_lease(lease_id)` | `leases` | 102 | Gives the exact rent ($2,400), landlord, and due date (2026-09-02) to check the landlord's email against. |
| `get_pricing(sku)` | `pricing` | 103 | Gives the $22 cost and $58 list price, so any bulk discount stays above cost. |

## MCP connection in Claude Code (Problem 4)

- Config: `HW5/.mcp.json` (and the same `campus-customs` entry in `YALE/.mcp.json` for sessions started at the YALE root) runs `.venv/bin/python mcp_server/server.py` over stdio. No API key is involved.
- Smoke test: each original tool was called live from Claude Code with the ticket 101–103 questions; all three outputs match `data/campus_customs_new.db` → `output/mcp_smoke.json`.
- Date check: `data/campus_customs.db` is byte-identical to the one in `data.zip`; lease 1 is due 2026-09-02, which is 2 days after `desk.date_today` (2026-08-31) — on time, not overdue.

## Agent team (Problem 5)

Code: `backend/agents.py` (PydanticAI), types in `backend/models.py`, prompts in `backend/prompts/`, audit in `backend/audit.py`, command line runner `backend/run_tickets.py`.

```bash
.venv/bin/python backend/run_tickets.py 101 102 103
```

Every agent uses **gpt-6-luna through Portkey** (`https://api.portkey.ai/v1`, `PORTKEY_API_KEY` from the root `.env`). The model name is a constant, not an env setting, so nothing can swap it.

### Agents

| Agent | Prompt | Job | MCP tools it can see | Output |
|---|---|---|---|---|
| boss | `boss.md` | Reads the ticket, picks only the teammates it needs, writes the decision for the human; **makes the final discount decision** on a price override | `get_ticket`, `list_open_tickets`, `get_pricing` (ticket + shop date are handed to it up front) | `BossDecision` (summary, status, next steps, `discount` for price overrides) |
| inventory | `inventory.md` | Stock per size, shortfall, right vendor, lead days, whether the vendor will ship; a reorder (purchase) request only if its task asks | `get_desk`, `check_stock`, `get_stock_all_sizes`, `list_vendors`, `vendor_shipping_status`, `get_pricing` | `AgentReport` |
| accounting | `accounting.md` | Invoices, cash, dry-run payment checks, payment **requests**, price floor; **reprint purchase check** (cash first, then a purchase request or `refused_not_enough_cash`) | `get_desk`, `get_invoice`, `list_open_invoices`, `get_cash_balance`, `check_payment`, `list_payments`, `get_lease`, `get_pricing`, `vendor_shipping_status` | `AgentReport` with `payment_requests` |
| facilities | `facilities.md` | Checks the landlord's notice against the lease; hands the payment check to accounting | `get_desk`, `get_lease`, `get_cash_balance` | `AgentReport` (optional `landlord_note` draft) |
| customer_service | `customer_service.md` | Writes one customer reply draft (stock, timing, price above cost) | `get_desk`, `get_ticket`, `check_stock`, `get_stock_all_sizes`, `get_pricing` | `AgentReport` with one `customer_reply` draft |

Delegation: every agent has a `delegate(agent, task)` tool. The boss chooses who works on a ticket; a specialist may ask one other specialist (e.g. facilities → accounting). Payment requests and drafts from every report are collected onto the ticket by code, so nothing gets lost or invented when the boss summarises. Specialists never delegate back up to the boss (the boss started the run, so that would be a loop). Prompts contain only rules and placeholders like `<invoice id>` — no real shop numbers — so every fact has to come from an MCP call.

### MCP tools and tables

| Tool | Table(s) | Agents |
|---|---|---|
| `get_desk` | `desk` | all specialists |
| `get_ticket`, `list_open_tickets` | `tickets` | boss, customer service |
| `check_stock`, `get_stock_all_sizes` | `inventory` | inventory, customer service |
| `get_pricing` | `pricing` | boss, inventory, accounting, customer service |
| `list_vendors` | `vendors` | inventory |
| `vendor_shipping_status` | `vendors`, `invoices`, `desk` | inventory, accounting |
| `get_invoice`, `list_open_invoices` | `invoices`, `vendors` (+ `desk` for days overdue) | accounting |
| `get_lease` | `leases` | facilities, accounting |
| `get_cash_balance` | `cash_accounts` | accounting, facilities |
| `check_payment` | `cash_accounts` (dry run) | accounting |
| `list_payments` | `payments` | accounting |
| `list_tickets` | `tickets` | **no agent** — backend `GET /api/tickets` |
| `set_ticket_status` | writes `tickets.status` | **no agent** — backend marks a ticket resolved |
| `record_payment` | writes `payments`, `cash_accounts`, and `invoices` (invoice → paid) / `leases` (rent → next_due +1 month); purchases also read `pricing`, `vendors` | **no agent** — only `POST /api/approvals` after a human approves |

### Test run (2026-10-03, working DB unchanged afterwards)

| Ticket | Agents called | Result | Tokens |
|---|---|---|---|
| 101 tee S | boss → inventory → accounting → customer service | 0 in stock; Bulldog Print Co blocked by open invoice 501; **payment request $840** (cash 3,400 → 2,560) waiting for a human; customer draft, earliest arrival 2026-09-05 | ~19.7k |
| 102 rent | boss → facilities → accounting | Notice matches lease 1 ($2,400, Elm City Properties, due 2026-09-02, 2 days); **payment request $2,400** (3,400 → 1,000) waiting for a human; inventory and customer service not called | ~9.5k |
| 103 hoodies | boss → inventory → accounting → customer service | 8 of 20 in size M; 12 need a reprint blocked by invoice 501; draft offers $52.20 each ($1,044), above the $22 cost, pending the owner's OK (rules changed later; see the ticket 103 redo below) | ~21.3k |

If both waiting payments are approved, cash goes 3,400 → 160 (the server checks cash again at approval time, so it can never go negative).

### Safety

- **Payments:** agents can only *request* payments. `record_payment` is filtered out of every agent's toolset (asserted in code and re-checked on every tool call). It needs a human's name, the exact bill amount, and enough cash; it refuses everything else. Cash only goes out and never goes negative.
- **No outside contact:** there is no email, phone, or vendor tool anywhere. Customer, vendor, and landlord messages are `Draft` objects with `status: "draft"` that stay on the board (`output/board.json`).
- **Facts only from MCP:** agents have no SQL or file access; every number comes from an MCP tool on `campus_customs_new.db`. The original DB is never opened (the server refuses it).
- **Shop date:** `desk.date_today` is passed to every agent; prompts forbid using any other date.
- **Allowlists:** each agent sees only its own MCP tools; an off-list call is refused and logged as `tool_refused`.
- **Audit trail:** `output/audit_trail.json` is append-only. It records run start, every MCP tool call (agent, args, result), every delegation, every specialist report, and run end with token usage. Old runs are never wiped; an unreadable file is moved aside, not deleted. Key-like fields are hidden.
- **Secrets:** `PORTKEY_API_KEY` is read from `.env` only, never logged or saved; `.env` is git-ignored.

### Token limits / avoiding unnecessary agent calls

- One budget per ticket, shared by every agent in it: at most 18 model requests, 30 tool calls, 90,000 tokens (`UsageLimits`).
- Each model reply is capped at 1,500 output tokens and uses low reasoning effort.
- The boss's prompt maps each ticket type to the smallest team (rent → facilities only, no customer service; price override → inventory, accounting only if a reprint is needed, then customer service). The boss is told not to call anyone twice.
- At most 5 agent calls per ticket and delegation depth 2 (boss → specialist → specialist). Depth-2 agents don't even see the `delegate` tool, and loops (A → B → A) or self-calls are refused.
- The ticket and shop date are fetched once and handed to the boss; the date is passed along in every delegated task, so agents don't spend calls on it.
- Specialists send back a short report (answer, facts, blockers, one-line payment/draft summaries), not their whole conversation.

## Backend routes (Problem 7)

Code: `backend/main.py` (FastAPI). Start from `backend/` with the venv active: `uvicorn main:app --reload --port 8000`. Every route reads or changes shop data only through the campus-customs MCP server.

- `GET /api/tickets` — the three tickets with `open`/`resolved` status (from `tickets` via MCP `list_tickets`), plus what the team last left on the board for each (summary, agents called, payments waiting, drafts).
- `POST /api/tickets/{ticket_id}/run` — runs the agent team on one ticket; returns the decision, agent calls, payment requests, and drafts (saved to `output/board.json`). The ticket becomes `resolved` only if nothing is waiting for approval, nothing was refused for cash, the boss did not report it `blocked`, and (price override) the boss made a final discount decision between unit cost and list price. Otherwise it stays `open`, and the reasons are logged as a `ticket_status` event.
- `POST /api/tickets/{ticket_id}/reopen?reason=` — a human decided a resolved ticket was not really finished. It sets the ticket back to `open` and logs `ticket_reopened` with the reason (used once, for ticket 103).
- `GET /api/events?limit=50&ticket_id=` — newest agent events from `output/audit_trail.json` (read only; the file stays append-only).
- `GET /api/approvals` — payment and purchase requests on the board that are still waiting for a human.
- `POST /api/approvals` — a human clicked Approve (`ticket_id`, `kind`, `ref_id`, `approved_by`). **The only route that moves cash**: it pays a request an agent prepared via MCP `record_payment`, which re-checks the exact amount, not already paid, vendor can ship (for purchases), and enough cash in one transaction. Then it writes `payments`, lowers `cash_accounts`, marks the invoice `paid` / moves the lease's `next_due` on a month, logs `payment_approved` (or `payment_refused`) to the audit trail, and resolves the ticket only if the same check passes (nothing waiting, nothing refused, not blocked).
- `GET /api/cash` — current `checking` balance from `cash_accounts` (MCP `get_cash_balance`).
- `POST /api/reset` — copies `campus_customs.db` (only read, never written) over `campus_customs_new.db` atomically, sets paid board requests back to waiting so the board matches the database, and appends a `reset` event (the audit trail is never wiped).
- `GET /api/health` — quick check; shows the model in use (`gpt-6-luna`).

Route test (2026-10-03): ticket 102 run via the API (boss → facilities → accounting, ~11.6k tokens) → approve rent $2,400 (3,400 → 1,000, lease next_due → 2026-10-02, ticket resolved) → approve again refused → approve invoice 501 $840 (→ 160) → $264 purchase refused for not enough cash → reset (back to 3,400) → purchase refused because invoice 501 is open again → pay 501, purchase ok (→ 2,296) → reset. Afterwards the working DB matched the original again, `output/board.json` was put back to its pre-test state, and the audit trail kept every earlier entry (85 → 104).

## Dashboard (Problem 8)

`frontend/` (React + Vite + TypeScript, `npm run dev` → http://localhost:5173) uses only the routes above at http://localhost:8000. The backend's CORS allows `http://localhost:5173` / `http://127.0.0.1:5173`. While a run is going, the dashboard polls only `GET /api/events` (it reads a file and costs no tokens). Approvals need a typed name plus a second "Confirm" click. Design notes: `output/design.md`.

## Full run — resolving the tickets (Problem 9)

Done on 2026-10-03 through the real backend routes (`POST /api/reset`, `POST /api/tickets/{id}/run`, `POST /api/approvals`), one ticket at a time, gpt-6-luna through Portkey. The team stopped at every payment, and each one was paid only after I replied "approve".

1. **Reset:** `POST /api/reset` copied `campus_customs.db` over `campus_customs_new.db`. Checked: the files were byte-identical, 3 open tickets, 0 payments, invoice 501 open, lease 1 due 2026-09-02. **Starting checking: $3,400.00.**
2. **Runs and approvals:**

| Ticket | Agents (delegations) | Tools used | Outcome | Human approval | Cash |
|---|---|---|---|---|---|
| 101 | Boss → Inventory, Boss → Accounting, Boss → Customer Service | Inventory: `check_stock`, `list_vendors`, `get_stock_all_sizes`, `vendor_shipping_status` · Accounting: `get_invoice`, `get_cash_balance`, `check_payment`, `list_payments` · CS: `get_ticket`, `check_stock`, `get_stock_all_sizes` | S = 0. Vendor blocked by invoice 501, so an $840 payment request. Customer draft with earliest arrival 2026-09-05. | Invoice 501, $840, approved by Soyoun Park (payment #1). Invoice → `paid`. | 3,400 → **2,560** |
| 102 | Boss → Facilities → Accounting | Facilities: `get_lease` · Accounting: `get_lease`, `get_cash_balance`, `list_payments`, `check_payment` | Lease 1 matches the notice timing. $2,400 rent request. | Rent lease 1, $2,400, approved by Soyoun Park (payment #2). Next due → 2026-10-02. | 2,560 → **160** |
| 103 (final run `03ee63f294`) | Boss → Inventory, Boss → Accounting (reprint purchase check), Boss → Customer Service | Boss: `get_pricing` · Inventory: `check_stock`, `get_pricing`, `list_vendors`, `get_desk`, `vendor_shipping_status` · Accounting: `get_cash_balance`, `get_pricing`, `vendor_shipping_status`, `check_payment` · CS: `get_ticket`, `check_stock`, `get_pricing` | 8 of 20 M in stock. **Boss's final price $50 each: 8 × $50 = $400** (corrected from 20 × $50). Reprint of 12 = $264 vs $160 cash → `refused_not_enough_cash`. Draft offers only the 8 in stock ($400). Boss: `blocked` → ticket stays **open**. | None. The purchase was refused for cash before it reached me. | 160 → **160** |

The boss gets the ticket and shop date from the backend (`get_ticket`, `get_desk` via MCP) before it starts. In the final 103 run, it also read `get_pricing` to decide the discount.

**Ticket 103 redo.** The first 103 run (`cc1a7c1812`, 16,466 tokens) left the discount "pending the owner's OK", never checked cash for the 12-hoodie reprint, and was marked resolved because nothing was waiting for payment. After my review I reopened it (`POST /api/tickets/103/reopen`, logged as `ticket_reopened`) and fixed the rules:
- the boss makes the final discount decision (`BossDecision.discount`);
- Accounting checks cash first for any reprint and returns a purchase request for a human or `refused_not_enough_cash`;
- the backend resolves a ticket only when it's really finished.

Then I re-ran only ticket 103 (`03ee63f294`). Tickets 101 and 102 were not touched.

The re-run's boss decision said 20 × $50 = $1,000, but the real offer is the 8 in-stock hoodies. I kept the $50 price and corrected the decision to **8 × $50 = $400**: `output/board.json` was updated and a `decision_corrected` event was appended (the original `run_end` stays in the audit trail). To stop it happening again, `DiscountDecision.qty` now means the units really offered, the model checks `total = unit_price × qty`, the boss prompt says so, and the backend keeps a discount ticket open if the total doesn't add up.

Tokens: 21,691 (101) + 11,774 (102) + 26,873 (103 final) = **60,338** for the final runs, or **76,804** including the reopened first 103 run.

3. **Final checks** (from the database, not from the agents):
   - 101 `resolved` and 102 `resolved` (by the approval route after my approval). 103 is `open`: the boss reported it `blocked` and the reprint purchase was refused for not enough cash ($264 needed, $160 available).
   - No blocked ticket is marked resolved. 103 is the only blocked ticket, and it is open.
   - `payments` has exactly 2 rows, both `approved_by = Soyoun Park`. No payment or purchase happened without me.
   - The lowest balance was $160. Cash never went negative and only went out.
   - $3,400 − $840 − $2,400 = **$160.00** = `cash_accounts.checking` ✓
   - Audit trail: 104 entries before → 178 after. It appended the reset, the three runs, two `payment_approved` events, the `ticket_reopened` event, the 103 re-run, its `ticket_status`, and the `decision_corrected` event. The first 103 run is still there too. Nothing earlier was wiped.

Outputs: `output/desk_tickets.html` (Actual, Cash, and Reflection tabs), `output/resolved_tickets.json` (built from the audit trail, the board, and the DB, with the checks above), `output/resolved_board.html` (one card per ticket), `output/board.json` (latest result and drafts per ticket).

Known quirk: `backend/audit.py` hides any field with "token" in its name, so the token counts in `run_end` show as `[hidden]` in the audit trail. The real counts are in `output/board.json` and `output/resolved_tickets.json`.

## What the harness gives the team (summary)

- **Data:** one working SQLite DB, reset from the untouched original before the real run.
- **Tools:** 17 MCP tools. 15 are read-only, plus `record_payment` and `set_ticket_status`, which only the backend calls.
- **Agents:** 5 PydanticAI agents on gpt-6-luna through Portkey. Each sees only its own tools, can delegate (depth ≤ 2, ≤ 5 agent calls per ticket), and shares one token budget per ticket.
- **Humans:** approve every payment or purchase (backend route plus dashboard), and can reopen a ticket that is not really finished. Drafts are never sent.
- **Finished means finished:** a ticket is resolved only when nothing waits for approval, nothing was refused for cash, it isn't blocked, and a discount ticket has the boss's final price.
- **Records:** append-only `audit_trail.json`, latest results in `board.json`, and the dashboard in `frontend/`.
