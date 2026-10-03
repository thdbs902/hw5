# Campus Customs MCP server

## What it is for

This server is the agents' only window into the shop. Instead of guessing, an agent calls a tool here and gets the real answer from the database. There is no other shop-tools layer: the backend agents use these MCP tools directly.

## Database

`data/campus_customs_new.db` — the working copy. Read tools open it **read-only**. The server refuses to start if pointed at the original `data/campus_customs.db`. (`CC_DB_PATH` can point it at a scratch copy for testing.)

The shop's "today" is `desk.date_today` (2026-08-31), never the computer clock.

## Tools

### Read-only (given to agents)

| Tool | Reads | Used by | What it returns |
|---|---|---|---|
| `get_desk()` | `desk` | all (only if the date was not handed over) | Shop's today and desk notes |
| `get_ticket(ticket_id)` | `tickets` | boss, customer service | One ticket: type, requester, sku/size/qty, lease/invoice links, notes |
| `list_open_tickets()` | `tickets` | boss | Every open ticket (id, type, requester, subject) |
| `check_stock(sku, size)` | `inventory` | inventory, customer service | Quantity and shelf location of one product in one size (ticket 101) |
| `get_stock_all_sizes(sku)` | `inventory` | inventory, customer service | Every size of one product plus the total |
| `get_pricing(sku)` | `pricing` | boss (discount decision), inventory, accounting, customer service | Unit cost (price floor) and list price (ticket 103) |
| `list_vendors()` | `vendors` | inventory | Vendors, specialty, lead days |
| `vendor_shipping_status(vendor_id)` | `vendors`, `invoices`, `desk` | inventory, accounting | Open unpaid invoices, `can_ship` (false while any invoice is open), earliest arrival = today + lead days |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | accounting | One invoice with vendor name and days overdue |
| `list_open_invoices()` | `invoices`, `vendors` | accounting | Every unpaid invoice and the total owed |
| `get_lease(lease_id)` | `leases` | facilities, accounting | Landlord, monthly rent, next due date (ticket 102) |
| `get_cash_balance(account)` | `cash_accounts` | accounting, facilities | Balance and date of one cash account |
| `check_payment(amount, account)` | `cash_accounts` | accounting | Dry run: enough cash? balance after? Changes nothing |
| `list_payments()` | `payments` | accounting | Payments already recorded (stops double payment) |

### Backend-only (never given to any agent)

| Tool | Table(s) | What it does |
|---|---|---|
| `list_tickets()` | reads `tickets` | Every ticket with `open`/`resolved` status (for the backend's ticket list). |
| `set_ticket_status(ticket_id, status)` | `tickets.status` | Backend marks a ticket `open` or `resolved`. |
| `record_payment(kind, ref_id, amount, approved_by, account, sku, qty)` | `payments`, `cash_accounts`, `invoices` (→ `paid`), `leases` (`next_due` + 1 month) | Called only by `POST /api/approvals` after a human clicks Approve. Pays an invoice, rent (`ref_id` = lease id), or a reprint purchase (`ref_id` = vendor id, `amount` = qty × unit_cost). Refuses: empty approver, amount ≤ 0, amount ≠ the bill, invoice already paid, rent not yet due, vendor with an open invoice (won't ship), not enough cash. Cash only goes out and never goes negative. One transaction. |

If nothing matches, a tool returns `{"found": false, ...}` (with a hint for a bad sku) instead of making something up.

## Run

```bash
.venv/bin/python mcp_server/server.py          # stdio (Claude Code uses this via .mcp.json)
.venv/bin/python mcp_server/server.py --http   # http://127.0.0.1:8001/mcp
```
