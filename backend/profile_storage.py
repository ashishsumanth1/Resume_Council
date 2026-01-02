"""JSON-based storage for master profiles.

This reduces repeated copy/paste and enables building compact "profile packs" that
can be reused across many resume runs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import PROFILES_DATA_DIR


def ensure_profiles_dir() -> None:
    Path(PROFILES_DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_profile_path(profile_id: str) -> str:
    return os.path.join(PROFILES_DATA_DIR, f"{profile_id}.json")


def create_profile(profile_id: str, name: str, raw_text: str, compact_text: str) -> Dict[str, Any]:
    ensure_profiles_dir()

    record: Dict[str, Any] = {
        "id": profile_id,
        "created_at": datetime.utcnow().isoformat(),
        "name": (name or "Master Profile").strip() or "Master Profile",
        "raw_text": raw_text,
        "compact_text": compact_text,
    }

    with open(get_profile_path(profile_id), "w") as f:
        json.dump(record, f, indent=2)

    return record


def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    path = get_profile_path(profile_id)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def list_profiles() -> List[Dict[str, Any]]:
    ensure_profiles_dir()

    items: List[Dict[str, Any]] = []
    for filename in os.listdir(PROFILES_DATA_DIR):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(PROFILES_DATA_DIR, filename), "r") as f:
            data = json.load(f)
            items.append(
                {
                    "id": data.get("id"),
                    "created_at": data.get("created_at"),
                    "name": data.get("name", "Master Profile"),
                }
            )

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items
