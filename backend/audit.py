"""Append-only audit trail: output/audit_trail.json (a JSON list; never wiped between runs)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
_lock = threading.Lock()
_SECRET_WORDS = ("api_key", "apikey", "authorization", "portkey", "password", "secret", "token")


def _clean(value: Any, limit: int = 600) -> Any:
    """Keep entries short and never let anything key-like into the file."""
    if isinstance(value, dict):
        return {k: ("[hidden]" if any(w in k.lower() for w in _SECRET_WORDS) else _clean(v, limit)) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v, limit) for v in value]
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "…"
    return value


def log(event: str, *, run_id: str, ticket_id: int | None, agent: str | None, **data: Any) -> None:
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id,
        "ticket_id": ticket_id,
        "agent": agent,
        "event": event,
        **_clean(data),
    }
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            trail = json.loads(AUDIT_PATH.read_text(encoding="utf-8")) if AUDIT_PATH.exists() else []
            if not isinstance(trail, list):
                trail = [trail]
        except json.JSONDecodeError:
            # never lose old history: keep the unreadable file aside and start a new list
            AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".broken-{datetime.now():%Y%m%d%H%M%S}.json"))
            trail = []
        trail.append(entry)
        tmp = AUDIT_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(trail, indent=2, default=str), encoding="utf-8")
        tmp.replace(AUDIT_PATH)
