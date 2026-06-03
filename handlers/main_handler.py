import os
import sqlite3
from datetime import datetime

from lang import settings_cache

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_USERS_DB = os.path.join(_BASE_DIR, "..", "..", "users.db")


def start_handler(message: dict) -> str:
    user = message.get("from", {})
    user_id = str(user.get("id", ""))

    conn = sqlite3.connect(_USERS_DB)
    try:
        row = conn.execute("SELECT id FROM users WHERE chat_id = ?", (user_id,)).fetchone()
        if row:
            return settings_cache.get("main_text_uz")

        conn.execute(
            """INSERT OR IGNORE INTO users
               (chat_id, username, first_name, last_name, language_code,
                search_text, search_start, search_total, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, '', 0, 0, ?, ?)""",
            (
                user_id,
                user.get("username"),
                user.get("first_name"),
                user.get("last_name"),
                user.get("language_code", "uz"),
                datetime.now(),
                datetime.now(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    text = settings_cache.get("start_text_uz")
    return text.replace("{name}", user.get("first_name") or "Foydalanuvchi")


def main_handler() -> str:
    return settings_cache.get("main_text_uz")
