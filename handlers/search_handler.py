import os
import sqlite3
from datetime import datetime

from lang import settings_cache, buttons

_BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
_USERS_DB  = os.path.join(_BASE_DIR, "..", "..", "users.db")
_BOOKS_DB  = os.path.join(_BASE_DIR, "..", "..", "kitoblar.db")


def update_updated_at(user_id: int) -> None:
    conn = sqlite3.connect(_USERS_DB)
    try:
        conn.execute(
            "UPDATE users SET updated_at = ? WHERE chat_id = ?",
            (datetime.now(), str(user_id)),
        )
        conn.commit()
    finally:
        conn.close()


def search_handler(query: str) -> tuple[str, dict | None]:
    query = query.strip()

    conn = sqlite3.connect(_BOOKS_DB)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM books WHERE name LIKE ?", (f"%{query}%",)
        ).fetchone()
        total = row[0] if row else 0

        if total == 0:
            conn.close()
            return settings_cache.get("not_found_text"), None

        results = conn.execute(
            "SELECT id, name FROM books WHERE name LIKE ? LIMIT 10", (f"%{query}%",)
        ).fetchall()
    finally:
        conn.close()

    result_text = settings_cache.get("result_text_uz")
    text = (
        result_text
        .replace("{start}", "1")
        .replace("{end}", str(min(10, total)))
        .replace("{total}", str(total))
    )

    keyboard_rows = []
    row_buf = []
    for i, (book_id, book_name) in enumerate(results):
        if i == 5:
            keyboard_rows.append(row_buf)
            row_buf = []
        row_buf.append({"text": str(i + 1), "callback_data": str(book_id)})
        text += f"\n{i + 1}. {book_name}"

    if row_buf:
        keyboard_rows.append(row_buf)
    keyboard_rows.append(
        [{"text": buttons.remove_button_text, "callback_data": "delete"}]
    )

    return text, {"inline_keyboard": keyboard_rows}


def download_handler(book_id: int):
    conn = sqlite3.connect(_BOOKS_DB)
    try:
        return conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    finally:
        conn.close()
