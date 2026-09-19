from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import List, Optional

from .models import Location, Monitor


APP_DIR = Path.home() / ".weather_notify"
SETTINGS_PATH = APP_DIR / "settings.json"


def load_settings() -> tuple[Optional[Location], List[Monitor]]:
    if not SETTINGS_PATH.exists():
        return None, []

    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        current_data = data.get("current_location")
        current_location = Location(**current_data) if current_data else None
        monitors = [Monitor.from_dict(x) for x in data.get("monitors", [])]
        return current_location, monitors
    except Exception:
        # Keep the application usable even if settings.json is damaged.
        return None, []


def save_settings(current_location: Optional[Location], monitors: List[Monitor]) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "current_location": asdict(current_location) if current_location else None,
        "monitors": [m.to_dict() for m in monitors],
    }
    SETTINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
