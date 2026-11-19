"""本地排行榜。"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path


def path() -> Path:
    override = os.environ.get("LUG_SHELL_SCORES")
    if override:
        return Path(override).expanduser()
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "lug-shell" / "scores.json"


def load() -> list[dict]:
    score_path = path()
    try:
        data = json.loads(score_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            rows = [r for r in data if isinstance(r, dict) and "score" in r]
            rows.sort(key=lambda r: int(r.get("score", 0)), reverse=True)
            return rows[:10]
    except (OSError, ValueError):
        pass
    return []


def save(name: str, score: int, combo: int) -> list[dict]:
    rows = load()
    rows.append({
        "name": (name or "YOU")[:3].upper(),
        "score": int(score),
        "combo": int(combo),
        "date": date.today().isoformat(),
    })
    rows.sort(key=lambda r: int(r.get("score", 0)), reverse=True)
    rows = rows[:10]
    score_path = path()
    try:
        score_path.parent.mkdir(parents=True, exist_ok=True)
        score_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return rows


def qualifies(score: int) -> bool:
    if score <= 0:
        return False
    rows = load()
    return len(rows) < 10 or score > int(rows[-1].get("score", 0))


def reset() -> Path:
    """清空排行榜，返回文件路径。"""
    path_ = path()
    try:
        path_.unlink()
    except FileNotFoundError:
        pass
    return path_
