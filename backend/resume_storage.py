"""JSON-based storage for resume runs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import RESUME_DATA_DIR


def ensure_resume_dir() -> None:
    Path(RESUME_DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_resume_path(resume_id: str) -> str:
    return os.path.join(RESUME_DATA_DIR, f"{resume_id}.json")


def _safe_title_from_jd(job_description: str) -> str:
    text = (job_description or "").strip().splitlines()[0:3]
    joined = " ".join([t.strip() for t in text if t.strip()])
    joined = joined.strip()
    if not joined:
        return "Resume Run"
    if len(joined) > 60:
        return joined[:57] + "..."
    return joined


def create_resume_run(
    resume_id: str,
    job_description: str,
    master_profile: str,
    company_details: str,
    use_peer_ranking: Optional[bool],
    result_payload: Dict[str, Any],
) -> Dict[str, Any]:
    ensure_resume_dir()

    record = {
        "id": resume_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": _safe_title_from_jd(job_description),
        "inputs": {
            "job_description": job_description,
            # Store compact truth pack used for generation (not necessarily the full raw profile)
            "master_profile": master_profile,
            "company_details": company_details,
            "use_peer_ranking": use_peer_ranking,
        },
        "result": result_payload,
    }

    with open(get_resume_path(resume_id), "w") as f:
        json.dump(record, f, indent=2)

    return record


def get_resume_run(resume_id: str) -> Optional[Dict[str, Any]]:
    path = get_resume_path(resume_id)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def list_resume_runs() -> List[Dict[str, Any]]:
    ensure_resume_dir()
    items: List[Dict[str, Any]] = []

    for filename in os.listdir(RESUME_DATA_DIR):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(RESUME_DATA_DIR, filename)
        with open(path, "r") as f:
            data = json.load(f)
            result = data.get("result", {})
            stage1 = result.get("stage1")
            stage2 = result.get("stage2")
            stage3 = result.get("stage3")
            items.append(
                {
                    "id": data.get("id"),
                    "created_at": data.get("created_at"),
                    "title": data.get("title", "Resume Run"),
                    "has_stage1": bool(stage1),
                    "has_stage2": bool(stage2),
                    "has_stage3": bool(stage3),
                }
            )

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items
