"""
Settings jadvali uchun 5-daqiqalik TTL cache (sync, Flask uchun).
Bot matnlarni DB dan o'qiydi; restart talab etmasdan yangilanadi.
"""
import os
import sqlite3
import time

_TTL = 300  # sekund

_defaults: dict[str, str] = {
    "start_text_uz":     "👋 Assalomu alaykum {name}\n\nKitob nomini yuboring!",
    "main_text_uz":      "🔍 Kitob qidirish uchun shunchaki nomini yuborish kerak!",
    "result_text_uz":    "📖 Natija: {start}-{end} | jami: {total} ta\n",
    "file_caption_text": "📔 {name}\n💾 {size}\n\n➡️ @{botname}",
    "not_found_text":    "Topilmadi.",
    "min_chars_text":    "Kamida 3 ta belgi kiriting!",
}

_cache: dict[str, str] = {}
_loaded_at: float = 0.0

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_USERS_DB = os.path.join(_BASE_DIR, "..", "..", "users.db")


def get(key: str) -> str:
    global _loaded_at
    if time.time() - _loaded_at > _TTL:
        _refresh()
    return _cache.get(key, _defaults.get(key, ""))


def _refresh() -> None:
    global _cache, _loaded_at
    try:
        conn = sqlite3.connect(_USERS_DB)
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        conn.close()
        _cache = {**_defaults, **dict(rows)}
    except Exception:
        _cache = dict(_defaults)
    _loaded_at = time.time()


def force_refresh() -> None:
    global _loaded_at
    _loaded_at = 0.0
    _refresh()
