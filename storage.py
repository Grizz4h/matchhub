from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dateutil import tz

BERLIN = tz.gettz("Europe/Berlin")


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def save_submission(base_dir: Path, payload: Dict[str, Any]) -> Path:
    """
    Speichert eine Abgabe als einzelne JSON-Datei.
    Dateiname: YYYY-MM-DD__HOME-vs-AWAY__user.json
    """
    ensure_dir(base_dir)

    user = (payload.get("user") or "unknown").strip().lower()
    game = payload.get("game") or {}
    d = (game.get("date") or "unknown-date").replace(":", "-")
    home = (game.get("home") or "home").replace(" ", "_")
    away = (game.get("away") or "away").replace(" ", "_")

    fname = f"{d}__{home}-vs-{away}__{user}.json"
    path = base_dir / fname

    payload["submitted_at"] = datetime.now(tz=BERLIN).isoformat(timespec="seconds")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_submissions(base_dir: Path) -> List[Path]:
    if not base_dir.exists():
        return []
    return sorted(base_dir.glob("*.json"), reverse=True)


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
