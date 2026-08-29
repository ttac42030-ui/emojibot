"""
Простое хранилище на JSON-файле. Для нагрузки в проде лучше заменить
на SQLite/Postgres, но для одного бота на VPS этого достаточно.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict

_LOCK = threading.Lock()
_PATH = os.path.join(os.path.dirname(__file__), "db.json")


def _load() -> Dict[str, Any]:
    if not os.path.exists(_PATH):
        return {"users": {}}
    with open(_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"users": {}}


def _save(data: Dict[str, Any]) -> None:
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _PATH)


def get_user(user_id: int) -> Dict[str, Any]:
    with _LOCK:
        data = _load()
        return data["users"].get(str(user_id), {
            "nickname": None,
            "sticker_set_name": None,
            "free_used": False,
            "emoji_count": 0,
        })


def update_user(user_id: int, **fields: Any) -> None:
    with _LOCK:
        data = _load()
        user = data["users"].setdefault(str(user_id), {
            "nickname": None,
            "sticker_set_name": None,
            "free_used": False,
            "emoji_count": 0,
        })
        user.update(fields)
        _save(data)
