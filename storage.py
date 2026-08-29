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

def check_premium(user_id: int) -> bool:
    '''Проверяет, есть ли у пользователя статус Premium'''
    db = _load_db()
    user_data = db.get(str(user_id), {})
    return user_data.get("is_premium", False)

def set_premium(user_id: int, status: bool = True):
    '''Устанавливает или снимает статус Premium'''
    db = _load_db()
    str_id = str(user_id)
    
    if str_id not in db:
        db[str_id] = {}
        
    db[str_id]["is_premium"] = status
    _save_db(db)
