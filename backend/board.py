"""The board: output/board.json holds the latest team result per ticket (drafts + payment requests).
Nothing on the board is ever sent; humans review drafts and approve payments from here."""

from __future__ import annotations

import json
import threading
from pathlib import Path

BOARD_PATH = Path(__file__).resolve().parent.parent / "output" / "board.json"
lock = threading.RLock()


def load() -> dict:
    with lock:
        return json.loads(BOARD_PATH.read_text(encoding="utf-8")) if BOARD_PATH.exists() else {}


def save(data: dict) -> None:
    with lock:
        BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = BOARD_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(BOARD_PATH)
