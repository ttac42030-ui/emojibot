import json
import os

DB_FILE = "users_db.json"

def _load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_db(data: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def has_free_attempt(user_id: int) -> bool:
    '''Возвращает True, если юзер еще НЕ использовал бесплатную попытку'''
    db = _load_db()
    return not db.get(str(user_id), {}).get("free_used", False)

def use_free_attempt(user_id: int):
    '''Отмечает, что юзер потратил бесплатную попытку'''
    db = _load_db()
    str_id = str(user_id)
    if str_id not in db:
        db[str_id] = {}
    db[str_id]["free_used"] = True
    _save_db(db)
