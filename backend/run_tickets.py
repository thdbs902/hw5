"""Run the agent team on tickets from the command line.

    .venv/bin/python backend/run_tickets.py 101 102 103

Results go on the board (output/board.json); every step is appended to output/audit_trail.json.
Nothing is paid and nothing is sent: payment requests and drafts wait for a human.
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")  # HW5/.env if present
load_dotenv(HERE.parent.parent / ".env")  # YALE/.env (PORTKEY_API_KEY)
sys.path.insert(0, str(HERE))

from agents import run_ticket  # noqa: E402


async def main(ids: list[int]) -> None:
    for tid in ids:
        r = await run_ticket(tid)
        print(f"\n=== Ticket {tid} [{r.decision.status}] run {r.run_id}")
        print(r.decision.summary)
        print("agents:", " -> ".join(f"{c.called_by or 'desk'}>{c.agent}" for c in r.agent_calls))
        for p in r.payment_requests:
            print(f"  payment request: {p.kind} {p.ref_id} ${p.amount:,.2f} to {p.payee} [{p.status}] after=${p.balance_after}")
        for d in r.drafts:
            print(f"  draft ({d.kind}) to {d.to}: {d.subject}")
        for s in r.decision.next_steps:
            print("  -", s)
        print("usage:", r.usage)


if __name__ == "__main__":
    asyncio.run(main([int(a) for a in sys.argv[1:]] or [101, 102, 103]))
