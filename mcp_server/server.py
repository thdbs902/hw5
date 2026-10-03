"""Campus Customs MCP server — shop facts for the HW5 agent team.

Reads ONLY the working copy data/campus_customs_new.db (never campus_customs.db).
Every tool returns rows straight from the database; nothing is made up.
Only two tools write, and agents are never given either: record_payment (needs a human
approver's name; called by POST /api/approvals) and set_ticket_status (backend marks tickets resolved).

Run (stdio):  python mcp_server/server.py
Run (HTTP):   python mcp_server/server.py --http   ->  http://127.0.0.1:8001/mcp
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("CC_DB_PATH", ROOT / "data" / "campus_customs_new.db")).resolve()
if DB_PATH.name == "campus_customs.db":
    raise SystemExit("Refusing to open the original campus_customs.db; use the working copy.")

mcp = FastMCP("campus-customs")


def _query(sql: str, params: tuple = ()) -> list[dict]:
    """Run a read-only query on the working DB and return rows as dicts."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, params)]
    finally:
        con.close()


def _sku(raw: str) -> str:
    """Accept 'cc-hood-navy', ' CC-HOOD-NAVY ', or 'CC-HOOD-NAVY size M' -> 'CC-HOOD-NAVY'."""
    parts = raw.strip().upper().split()
    return parts[0] if parts else ""


SKU_HINT = "Pass only the sku code, e.g. CC-HOOD-NAVY (size is a separate argument)."


def _today() -> str:
    """Shop 'today' comes from desk.date_today, never the computer clock."""
    return _query("SELECT date_today FROM desk LIMIT 1")[0]["date_today"]


def _add_month(iso: str) -> str:
    d = date.fromisoformat(iso)
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day).isoformat()
        except ValueError:
            continue
    raise ValueError(iso)


# ---------- desk & tickets ----------


@mcp.tool
def get_desk() -> dict:
    """The shop's 'today' (desk.date_today) and desk notes. Use this date for every due-date or lateness check."""
    return {"found": True, **_query("SELECT date_today, notes FROM desk LIMIT 1")[0]}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """One ticket from the work queue: type, requester, subject, sku/size/qty, linked lease_id/invoice_id, status, notes."""
    rows = _query("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not rows:
        return {"found": False, "ticket_id": ticket_id}
    return {"found": True, **rows[0]}


@mcp.tool
def list_open_tickets() -> dict:
    """All tickets whose status is 'open' (id, type, requester, subject)."""
    rows = _query("SELECT id, type, requester, subject FROM tickets WHERE status = 'open' ORDER BY id")
    return {"found": bool(rows), "tickets": rows}


@mcp.tool
def list_tickets() -> dict:
    """Every ticket with its status ('open' or 'resolved')."""
    rows = _query("SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at FROM tickets ORDER BY id")
    return {"found": bool(rows), "tickets": rows}


@mcp.tool
def set_ticket_status(ticket_id: int, status: str) -> dict:
    """BACKEND ONLY (never given to agents). Mark a ticket 'open' or 'resolved'."""
    if status not in ("open", "resolved"):
        return {"updated": False, "reason": "status must be 'open' or 'resolved'."}
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        con.commit()
        return {"updated": cur.rowcount == 1, "ticket_id": ticket_id, "status": status}
    finally:
        con.close()


# ---------- inventory & pricing ----------


@mcp.tool
def check_stock(sku: str, size: str) -> dict:
    """Ticket 101: how many of one product (sku) are on the shelf in one size."""
    rows = _query(
        "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
        (_sku(sku), size.strip().upper()),
    )
    if not rows:
        return {"found": False, "sku": sku, "size": size, "hint": SKU_HINT}
    return {"found": True, **rows[0]}


@mcp.tool
def get_stock_all_sizes(sku: str) -> dict:
    """Stock of one product in every size, plus the total — useful when the asked size is short."""
    rows = _query(
        "SELECT size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid",
        (_sku(sku),),
    )
    if not rows:
        return {"found": False, "sku": sku, "hint": SKU_HINT}
    name = _query("SELECT name FROM inventory WHERE sku = ? LIMIT 1", (_sku(sku),))[0]["name"]
    return {"found": True, "sku": _sku(sku), "name": name, "sizes": rows, "total_qty": sum(r["qty"] for r in rows)}


@mcp.tool
def get_pricing(sku: str) -> dict:
    """Ticket 103: unit cost and list price for one product, so a discount never drops below cost."""
    rows = _query(
        "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?",
        (_sku(sku),),
    )
    if not rows:
        return {"found": False, "sku": sku, "hint": SKU_HINT}
    return {"found": True, **rows[0]}


# ---------- vendors & invoices ----------


@mcp.tool
def list_vendors() -> dict:
    """Every vendor with its specialty and lead_days (days from order to delivery)."""
    return {"found": True, "vendors": _query("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id")}


@mcp.tool
def vendor_shipping_status(vendor_id: int) -> dict:
    """Can this vendor ship? A vendor will NOT ship while it has an open unpaid invoice.
    Returns lead_days, open invoices, can_ship, and the earliest arrival date if the vendor ships today (desk date + lead_days)."""
    vendor = _query("SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,))
    if not vendor:
        return {"found": False, "vendor_id": vendor_id}
    today = _today()
    open_invoices = _query(
        "SELECT id, amount, due_date, status, description FROM invoices WHERE vendor_id = ? AND status = 'open'",
        (vendor_id,),
    )
    v = vendor[0]
    arrival = (date.fromisoformat(today) + timedelta(days=v["lead_days"])).isoformat()
    return {
        "found": True,
        **v,
        "today": today,
        "open_invoices": open_invoices,
        "can_ship": not open_invoices,
        "earliest_arrival_if_shipped_today": arrival,
    }


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """One vendor invoice with the vendor's name, plus days_overdue measured from desk.date_today."""
    rows = _query(
        "SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, i.status, i.description "
        "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
        (invoice_id,),
    )
    if not rows:
        return {"found": False, "invoice_id": invoice_id}
    inv = rows[0]
    days = (date.fromisoformat(_today()) - date.fromisoformat(inv["due_date"])).days
    return {"found": True, **inv, "days_overdue": max(days, 0)}


@mcp.tool
def list_open_invoices() -> dict:
    """Every invoice that is still open (unpaid), with vendor names."""
    rows = _query(
        "SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, i.description "
        "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open' ORDER BY i.due_date"
    )
    return {"found": bool(rows), "invoices": rows, "total_open": sum(r["amount"] for r in rows)}


# ---------- leases ----------


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Ticket 102: the rent amount, landlord, and next due date for one lease."""
    rows = _query(
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
        (lease_id,),
    )
    if not rows:
        return {"found": False, "lease_id": lease_id}
    return {"found": True, **rows[0]}


# ---------- cash & payments ----------


@mcp.tool
def get_cash_balance(account: str = "checking") -> dict:
    """Current balance of one cash account and the date it was last updated."""
    rows = _query("SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,))
    if not rows:
        return {"found": False, "account": account}
    return {"found": True, **rows[0]}


@mcp.tool
def check_payment(amount: float, account: str = "checking") -> dict:
    """Dry run, changes nothing: is there enough cash to pay `amount`, and what balance would be left?
    Payments still need human approval before anything is paid."""
    rows = _query("SELECT balance FROM cash_accounts WHERE name = ?", (account,))
    if not rows:
        return {"found": False, "account": account}
    if amount <= 0:
        return {"found": True, "allowed": False, "reason": "Amount must be positive; cash only goes out."}
    balance = rows[0]["balance"]
    ok = amount <= balance
    return {
        "found": True,
        "account": account,
        "balance": balance,
        "amount": amount,
        "allowed": ok,
        "balance_after": round(balance - amount, 2) if ok else None,
        "reason": "Enough cash; still needs human approval." if ok else "Not enough cash; payment refused.",
    }


@mcp.tool
def list_payments() -> dict:
    """Payments already recorded (each one was approved by a human)."""
    rows = _query("SELECT * FROM payments ORDER BY id")
    return {"found": bool(rows), "payments": rows}


@mcp.tool
def record_payment(
    kind: str,
    ref_id: int,
    amount: float,
    approved_by: str,
    account: str = "checking",
    sku: str | None = None,
    qty: int | None = None,
) -> dict:
    """HUMAN-APPROVED ONLY. Pays an invoice (kind='invoice'), rent (kind='rent', ref_id = lease id),
    or a reprint purchase (kind='purchase', ref_id = vendor id, sku + qty; amount must be qty x unit_cost
    and the vendor must have no open unpaid invoice, because it will not ship).
    Refuses with no approver, a non-positive amount, a wrong amount, an already-paid invoice, rent not yet due, or not enough cash.
    Paying rent moves that lease's next_due one month on.
    Cash only goes out and never goes negative."""
    if not approved_by or not approved_by.strip():
        return {"paid": False, "reason": "Human approval is required (approved_by is empty)."}
    if kind not in ("invoice", "rent", "purchase"):
        return {"paid": False, "reason": "kind must be 'invoice', 'rent', or 'purchase'."}
    if amount <= 0:
        return {"paid": False, "reason": "Amount must be positive; cash only goes out."}

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.execute("BEGIN IMMEDIATE")
        if kind == "invoice":
            inv = con.execute("SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)).fetchone()
            if inv is None:
                return {"paid": False, "reason": f"Invoice {ref_id} not found."}
            if inv["status"] != "open":
                return {"paid": False, "reason": f"Invoice {ref_id} is already {inv['status']}."}
            expected = inv["amount"]
        elif kind == "purchase":
            if not sku or not qty or qty <= 0:
                return {"paid": False, "reason": "A purchase needs a sku and a positive qty."}
            vendor = con.execute("SELECT id FROM vendors WHERE id = ?", (ref_id,)).fetchone()
            if vendor is None:
                return {"paid": False, "reason": f"Vendor {ref_id} not found."}
            blocking = con.execute(
                "SELECT id FROM invoices WHERE vendor_id = ? AND status = 'open'", (ref_id,)
            ).fetchall()
            if blocking:
                ids = ", ".join(str(r["id"]) for r in blocking)
                return {"paid": False, "reason": f"Vendor {ref_id} will not ship while invoice(s) {ids} are open; pay those first."}
            price = con.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (_sku(sku),)).fetchone()
            if price is None:
                return {"paid": False, "reason": f"No pricing for {sku}."}
            expected = round(price["unit_cost"] * qty, 2)
        else:
            lease = con.execute("SELECT monthly_rent, next_due FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if lease is None:
                return {"paid": False, "reason": f"Lease {ref_id} not found."}
            today = con.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]
            if (date.fromisoformat(lease["next_due"]) - date.fromisoformat(today)).days > 31:
                return {"paid": False, "reason": f"Rent for lease {ref_id} is not due yet (next due {lease['next_due']})."}
            expected = lease["monthly_rent"]
        if abs(amount - expected) > 0.005:
            return {"paid": False, "reason": f"Amount {amount} does not match the {kind} amount {expected}."}

        acct = con.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if acct is None:
            return {"paid": False, "reason": f"Cash account {account} not found."}
        if amount > acct["balance"]:
            return {"paid": False, "reason": f"Not enough cash: balance {acct['balance']}, need {amount}."}

        today = con.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]
        new_balance = round(acct["balance"] - amount, 2)
        con.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?", (new_balance, today, account))
        cur = con.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, account, today, approved_by.strip()),
        )
        if kind == "invoice":
            con.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        elif kind == "rent":  # rent for this due date is settled -> the lease's next due date moves one month on
            con.execute("UPDATE leases SET next_due = ? WHERE id = ?", (_add_month(lease["next_due"]), ref_id))
        con.commit()
        return {"paid": True, "payment_id": cur.lastrowid, "kind": kind, "ref_id": ref_id, "amount": amount,
                "balance_after": new_balance, "paid_at": today}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="serve over HTTP on port 8001")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=8001, show_banner=False)
    else:
        mcp.run(show_banner=False)
