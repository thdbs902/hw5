# Campus Customs Front Desk — dashboard design (Problem 8)

Code: `frontend/` (React + Vite + TypeScript). Start with `npm run dev` inside `frontend/` → http://localhost:5173.
It talks only to the FastAPI backend from Problem 7 at http://localhost:8000 (the backend allows the Vite origin `http://localhost:5173` through CORS).

The look: **black lacquer and gold leaf, under stage lights.** A small campus shop's front desk, dressed for a headline show. It should feel bold and confident, but you can still read it while the team works.

## Dashboard layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [CC] CAMPUS CUSTOMS   shop date · tickets resolved · waiting on you · $ CHECKING │  masthead
├──────────────┬───────────────────────────────────────────┬───────────────────┤
│ TICKET RAIL  │ HERO: ticket #, subject, SKU/size/qty,     │ THE VAULT         │
│  #101 card   │ customer note, [START THE AGENT TEAM]      │  big gold balance │
│  #102 card   ├───────────────────────────────────────────┤  recent payments  │
│  #103 card   │ THE FLOOR: 👑 Boss (full width)            │  / refusals/reset │
│              │  📦 Inventory   💵 Accounting               ├───────────────────┤
│ ↺ reset DB   │  🏛️ Facilities  💬 Customer Service         │ NEEDS YOUR        │
│              ├─────────────────────┬─────────────────────┤ SIGNATURE         │
│              │ LIVE WIRE (feed)    │ RUN SUMMARY          │  "Approving as"   │
│              │ newest first: tools,│ decision, boss       │  approval cards   │
│              │ hand-offs, reports, │ summary, next steps, │  [Approve] →      │
│              │ approvals           │ who did what, drafts │  [Confirm: pay $] │
└──────────────┴─────────────────────┴─────────────────────┴───────────────────┘
```

- **Left, the ticket rail:** tickets 101, 102, and 103 as desk tickets, each with a perforated stub edge. Each card shows the number, type, requester, note, an open/resolved pill, and "N to approve" if a payment is waiting. Click a card to select it.
- **Centre, the floor:** the selected ticket's hero card with one big gold **Start the agent team** button. It says "Run the team again" if the ticket already has a run. Below it are the five agent cards, then the live feed and the run summary side by side.
- **Right, the money:** the vault (checking balance) on top, with approvals underneath. Money gets its own column so it is always on screen and never hidden by a scroll.
- **Masthead:** the shop date (`desk.date_today`), a resolved count, a "waiting on you" count that glows gold when it isn't zero, and the checking balance as a gold chip.
- Under 1250 px wide, the three columns stack into one.

### How it works with the backend

| UI piece | Route |
|---|---|
| Ticket rail, open/resolved | `GET /api/tickets` |
| Start the agent team | `POST /api/tickets/{id}/run` |
| Floor, live feed, who-did-what | `GET /api/events?ticket_id=…`, polled every 1.2 s **only while a run is going** |
| Approval cards | `GET /api/approvals` |
| Approve → Confirm | `POST /api/approvals` with `approved_by` = the name typed in "Approving as" |
| Vault balance | `GET /api/cash` |
| Vault ledger | `GET /api/events` (payment_approved / payment_refused / reset) |
| ↺ Reset working database | `POST /api/reset`, after a browser confirm box |

The events route only reads a file, so it is cheap to poll. Tickets, cash, and approvals each open an MCP connection, so they reload only after an action (run finished, approval, reset), never on a timer.

## How the agents look different

Each agent has its own colour and emblem. The same colour follows the agent onto its floor card, its feed rows, its tool chips, and its line in "who did what". That way you can follow one agent through a whole run.

| Agent | Emblem | Colour | Why |
|---|---|---|---|
| The Boss | 👑 | gold `#f5c542` | The headliner. Its card spans the whole floor and has a bigger avatar. |
| Inventory | 📦 | teal `#2ed3b7` | The stockroom: cool and practical. |
| Accounting | 💵 | violet `#a78bfa` | The ledger. Violet is kept apart from the cash gold, so "accounting is thinking" never looks like "money moved". |
| Facilities | 🏛️ | coral `#ff7a59` | The building, the lease, the landlord. |
| Customer Service | 💬 | hot pink `#ff4fa3` | Front of house. The warmest colour. |

**States on a card** (worked out from the audit events):
- **idle:** faded and desaturated, "Off the floor". The boss didn't need this agent, so idle agents also show that the team stayed small.
- **working:** a solid glowing ring in the agent's colour that slowly "breathes", plus a filled status pill.
- **waiting:** a dashed border. This agent handed work to someone and is waiting for the report.
- **done:** a steady coloured border.
- **error:** a red border.

Each card also shows **what the agent is doing right now** (for example "Using check_stock(sku=CC-TEE-WHITE, size=S)", "Handed a task to Accounting", or "Reported back to The Boss"), **who called it**, and **every MCP tool it used** as mono-font chips, with ×N when a tool was used more than once.

**The run summary** also shows the Boss's final price on a discount ticket (a gold box: price each, list price, cost floor, reason), plus a status line that says whether the ticket was resolved or *why it stays open* (for example “a needed payment or purchase was refused: not enough cash”).

**The live wire** is a newest-first feed of every step. Each row has a time, the agent's colour bar, and the action: tool call (with args and an expandable raw result), hand-off (the task text), report, sign-off, or human approval.

## How resolved tickets look

- On the rail, the card's stub edge turns from Yale blue to gold, and its background warms to gold. A double-bordered **RESOLVED** stamp slams on at an angle, like a rubber stamp on a paper ticket.
- The open/resolved pill turns from blue "● Open" to gold "✓ Resolved".
- If you select a resolved ticket, the hero card gets a gold outline and halo, plus a "✦ Resolved ✦" badge above the button.
- When a ticket flips from open to resolved during your session (a run with nothing to approve, or your last approval for it), its card glows three times and gold sparkles rain over the floor. A toast also says "Ticket #N resolved."
- The run summary has a decision pill: gold for **Needs your approval**, green for **Ready for review**, blue for **Waiting on vendor**, red for **Blocked**.

## How cash and approvals look

- **The vault:** the checking balance from `cash_accounts`, in big shimmering gold serif numerals. The same number also sits in the masthead chip. When a payment lands, the number **counts down** from the old balance to the new one, so you see the money leave. Below $500 it turns amber as a warning. A short ledger lists recent approvals (amount, payee, who approved, balance after), refusals with the backend's reason, and resets.
- **Needs your signature:**
  - "Approving as" is a signature-style italic field. A name is required because the backend records `approved_by`, and the app won't approve without one. The name is remembered in the browser.
  - Each approval card shows the kind (invoice violet, rent coral, purchase teal), the amount in big numerals, the payee, the agent's reason, and **"Checking after: $X"**, calculated from the live balance.
  - Approving takes **two clicks:** *Approve* → *Confirm: pay $840.00* (the second one pulses gold), with a cancel link. So a real human makes a deliberate choice; one stray click can't pay anything.
  - If the payment would make cash negative, the card turns red and the button says **Not enough cash** and is disabled. The backend's `record_payment` checks again anyway.
  - Requests for the selected ticket move to the top and get a gold halo. Approve buttons are locked while a team run is going.
  - After an approval, the vault, the approvals, the ticket rail, and the feed all reload, and the feed shows "✍️ *name* approved $… to …".
- Agents only ever *prepare* payments; this panel is the only place cash moves.

## Creative choices and why

1. **Black and gold, "Beyoncé-style":** my project rule is bold, polished, glamorous, high-impact. Gold also means money, so it is saved for the Boss, the cash, and anything waiting on me. That makes "where should I look?" obvious.
2. **Desk tickets with a perforated stub and a rubber stamp:** "resolved" should feel like a physical act at a real shop counter, not just a checkbox.
3. **A "floor" instead of a log table:** you see who is working, who is waiting on whom, and who never got called. That shows the boss used the smallest team, which is a big point of the assignment.
4. **One colour per agent everywhere:** you can scan the feed and the summary without reading names.
5. **Two-click approval with a signature name and "cash after":** human approval is the main safety rule, so the UI makes approving deliberate and shows the result before money moves. Approving into a negative balance can't even be attempted.
6. **Counting-down balance:** the cash change after a payment is the moment that matters, so it's animated where you're already looking.
7. **Cheap on tokens and processes:** only the free events file is polled, and only during a run. The UI never starts an agent run unless you press the button, and the button reminds you it uses tokens.
8. **Built with code only:** the crest, emblems, stamp, and sparkles are CSS, text, and emoji, with no generated images. `prefers-reduced-motion` turns the animations off.
