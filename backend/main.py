"""Campus Customs backend (FastAPI). Start from backend/:

    uvicorn main:app --reload --port 8000

Shop facts and every database change go through the campus-customs MCP server.
Agents only PREPARE payments; POST /api/approvals (a human clicked Approve) is the only thing that moves cash.
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
load_dotenv(ROOT / ".env")  # HW5/.env if present
load_dotenv(ROOT.parent / ".env")  # YALE/.env (PORTKEY_API_KEY)
sys.path.insert(0, str(HERE))

import audit  # noqa: E402
import board  # noqa: E402
from agents import MODEL_NAME, build_mcp_client, run_ticket  # noqa: E402
from models import TicketResult  # noqa: E402

ORIGINAL_DB = ROOT / "data" / "campus_customs.db"  # read-only source for reset; never written
WORKING_DB = ROOT / "data" / "campus_customs_new.db"

app = FastAPI(title="Campus Customs desk", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # the React dashboard (Vite)
    allow_methods=["*"],
    allow_headers=["*"],
)


async def mcp(tool: str, args: dict[str, Any] | None = None) -> dict:
    """Call one campus-customs MCP tool (the only way this backend reads or changes shop data)."""
    async with build_mcp_client() as client:
        result = await client.call_tool(tool, args or {})
    return result.data


def _waiting(requests: list[dict]) -> list[dict]:
    return [p for p in requests if p.get("status") == "needs_human_approval"]


async def _open_reasons(ticket: dict, decision: dict, requests: list[dict]) -> list[str]:
    """Why a ticket must stay open. Empty list = the ticket is really finished and can be resolved."""
    reasons = []
    if _waiting(requests):
        reasons.append("a payment or purchase is waiting for human approval")
    if any(p.get("status") == "refused_not_enough_cash" for p in requests):
        reasons.append("a needed payment or purchase was refused: not enough cash")
    if decision.get("status") == "blocked":
        reasons.append("the Boss reported the ticket as blocked")
    if ticket.get("type") == "price_override":
        d = decision.get("discount")
        if not d:
            reasons.append("the Boss did not make a final discount decision")
        else:
            price = await mcp("get_pricing", {"sku": ticket["sku"]})
            if not price.get("found") or not (price["unit_cost"] < d["unit_price"] <= price["list_price"]):
                reasons.append(f"the Boss's price ${d['unit_price']} is not between unit cost and list price")
            if abs(d["total"] - round(d["unit_price"] * d["qty"], 2)) > 0.005:
                reasons.append(f"the Boss's total ${d['total']} is not unit price x qty")
    return reasons


# ---------- tickets ----------


@app.get("/api/tickets")
async def list_tickets() -> list[dict]:
    """The tickets with open/resolved status, plus what the team last left on the board for each."""
    tickets = (await mcp("list_tickets"))["tickets"]
    b = board.load()
    out = []
    for t in tickets:
        entry = b.get(str(t["id"]))
        out.append({
            **t,
            "last_run": None if entry is None else {
                "run_id": entry["run_id"],
                "decision_status": entry["decision"]["status"],
                "summary": entry["decision"]["summary"],
                "agents": [c["agent"] for c in entry["agent_calls"]],
                "payments_waiting": len(_waiting(entry["payment_requests"])),
                "drafts": len(entry["drafts"]),
            },
        })
    return out


@app.post("/api/tickets/{ticket_id}/run", response_model=TicketResult)
async def run_team(ticket_id: int) -> TicketResult:
    """Run the agent team on one ticket. Payments come back as requests; drafts stay on the board."""
    ticket = await mcp("get_ticket", {"ticket_id": ticket_id})
    if not ticket.get("found"):
        raise HTTPException(404, f"Ticket {ticket_id} not found")
    try:
        result = await run_ticket(ticket_id)
    except Exception as err:  # usage limit, model/gateway error, ...
        raise HTTPException(502, f"Agent run failed: {type(err).__name__}: {err}") from err
    # Resolved only when the team is really finished: nothing waiting for a human, nothing refused for cash,
    # not blocked, and (price_override) the Boss made a valid final discount decision.
    reasons = await _open_reasons(ticket, result.decision.model_dump(), [p.model_dump() for p in result.payment_requests])
    status = "open" if reasons else "resolved"
    await mcp("set_ticket_status", {"ticket_id": ticket_id, "status": status})
    audit.log("ticket_status", run_id=result.run_id, ticket_id=ticket_id, agent=None, status=status, reasons=reasons)
    result.ticket_status, result.status_reasons = status, reasons
    return result


@app.post("/api/tickets/{ticket_id}/reopen")
async def reopen(ticket_id: int, reason: str = Query(..., min_length=3)) -> dict:
    """Put a resolved ticket back to open (a human decided it was not really finished). Logged to the audit trail."""
    ticket = await mcp("get_ticket", {"ticket_id": ticket_id})
    if not ticket.get("found"):
        raise HTTPException(404, f"Ticket {ticket_id} not found")
    await mcp("set_ticket_status", {"ticket_id": ticket_id, "status": "open"})
    audit.log("ticket_reopened", run_id="reopen", ticket_id=ticket_id, agent=None, was=ticket["status"], reason=reason)
    return {"ticket_id": ticket_id, "was": ticket["status"], "status": "open"}


# ---------- agent events ----------


@app.get("/api/events")
def recent_events(limit: int = Query(50, ge=1, le=500), ticket_id: int | None = None) -> list[dict]:
    """Newest agent events from output/audit_trail.json (read only; the file is append-only)."""
    import json

    if not audit.AUDIT_PATH.exists():
        return []
    trail = json.loads(audit.AUDIT_PATH.read_text(encoding="utf-8"))
    if ticket_id is not None:
        trail = [e for e in trail if e.get("ticket_id") == ticket_id]
    return list(reversed(trail[-limit:]))


# ---------- approvals (the only route that moves cash) ----------


class ApprovalIn(BaseModel):
    ticket_id: int
    kind: Literal["invoice", "rent", "purchase"]
    ref_id: int
    approved_by: str = Field(min_length=1, description="name of the human who clicked Approve")


@app.get("/api/approvals")
def pending_approvals() -> list[dict]:
    """Every payment/purchase request on the board that is still waiting for a human."""
    return [
        {"ticket_id": int(tid), **p}
        for tid, entry in board.load().items()
        for p in _waiting(entry["payment_requests"])
    ]


@app.post("/api/approvals")
async def approve(body: ApprovalIn) -> dict:
    """A human clicked Approve: pay one request that an agent prepared.
    The MCP tool re-checks everything (exact amount, not already paid, enough cash, vendor can ship)
    inside one database transaction, so cash can never go negative."""
    approver = body.approved_by.strip()
    if not approver:
        raise HTTPException(422, "approved_by is required — a human must approve.")
    with board.lock:
        b = board.load()
        entry = b.get(str(body.ticket_id))
        req = next(
            (p for p in (entry or {}).get("payment_requests", [])
             if p["kind"] == body.kind and p["ref_id"] == body.ref_id and p["status"] == "needs_human_approval"),
            None,
        )
        if req is None:
            raise HTTPException(404, "No waiting request like that on the board — agents must prepare it first.")

        args = {"kind": req["kind"], "ref_id": req["ref_id"], "amount": req["amount"],
                "approved_by": approver, "account": req.get("account") or "checking"}
        if req["kind"] == "purchase":
            args |= {"sku": req.get("sku"), "qty": req.get("qty")}
        paid = await mcp("record_payment", args)
        ids = dict(run_id=entry["run_id"], ticket_id=body.ticket_id, agent=None)
        if not paid.get("paid"):
            audit.log("payment_refused", **ids, request=req, approved_by=approver, reason=paid.get("reason"))
            raise HTTPException(409, paid.get("reason", "Payment refused"))

        req.update(status="paid", payment_id=paid["payment_id"], approved_by=approver, balance_after=paid["balance_after"])
        board.save(b)
    audit.log("payment_approved", **ids, request=req, approved_by=approver, result=paid)

    ticket = await mcp("get_ticket", {"ticket_id": body.ticket_id})
    reasons = await _open_reasons(ticket, entry["decision"], entry["payment_requests"])
    ticket_status = "open" if reasons else "resolved"
    if not reasons:
        await mcp("set_ticket_status", {"ticket_id": body.ticket_id, "status": "resolved"})
    audit.log("ticket_status", **ids, status=ticket_status, reasons=reasons)
    return {**paid, "ticket_id": body.ticket_id, "ticket_status": ticket_status, "status_reasons": reasons}


# ---------- cash ----------


@app.get("/api/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts."""
    data = await mcp("get_cash_balance", {"account": "checking"})
    if not data.get("found"):
        raise HTTPException(404, "checking account not found")
    return data


# ---------- reset ----------


@app.post("/api/reset")
async def reset() -> dict:
    """Put campus_customs_new.db back to the original values (copy of campus_customs.db, which is only read).
    Paid requests on the board go back to 'needs_human_approval' so the board matches the database.
    The audit trail is NOT wiped — the reset is appended to it."""
    if ORIGINAL_DB.resolve() == WORKING_DB.resolve():
        raise HTTPException(500, "Working DB path must differ from the original.")
    tmp = WORKING_DB.with_suffix(".resetting")
    shutil.copyfile(ORIGINAL_DB, tmp)  # read original -> temp file
    os.chmod(tmp, 0o644)
    os.replace(tmp, WORKING_DB)  # atomic swap; nobody sees a half-copied DB

    with board.lock:
        b = board.load()
        reopened = 0
        for entry in b.values():
            for p in entry["payment_requests"]:
                if p["status"] == "paid":
                    p.update(status="needs_human_approval", payment_id=None, approved_by=None)
                    reopened += 1
        board.save(b)

    balance = (await mcp("get_cash_balance", {"account": "checking"}))["balance"]
    open_tickets = sum(t["status"] == "open" for t in (await mcp("list_tickets"))["tickets"])
    audit.log("reset", run_id="reset", ticket_id=None, agent=None, checking=balance, board_requests_reopened=reopened)
    return {"reset": True, "checking": balance, "open_tickets": open_tickets, "board_requests_reopened": reopened}


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": MODEL_NAME}
