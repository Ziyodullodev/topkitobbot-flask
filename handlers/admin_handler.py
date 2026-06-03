import os
import sqlite3
from datetime import datetime, timedelta

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_USERS_DB = os.path.join(_BASE_DIR, "..", "users.db")


def get_statistics() -> dict:
    try:
        conn = sqlite3.connect(_USERS_DB)
        now = datetime.now()

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end   = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        week_start  = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
        week_end    = (week_start + timedelta(days=6)).replace(
            hour=23, minute=59, second=59, microsecond=999999)

        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end   = (
            (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        )

        last_month_start = (month_start - timedelta(days=1)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end   = month_start - timedelta(seconds=1)

        def q(sql, params=()):
            row = conn.execute(sql, params).fetchone()
            return row[0] if row else 0

        result = {
            "bugun_kirganlar":          q("SELECT COUNT(*) FROM users WHERE created_at BETWEEN ? AND ?", (today_start, today_end)),
            "bu_hafta_qoshilganlar":    q("SELECT COUNT(*) FROM users WHERE created_at BETWEEN ? AND ?", (week_start, week_end)),
            "bu_oy_qoshilganlar":       q("SELECT COUNT(*) FROM users WHERE created_at BETWEEN ? AND ?", (month_start, month_end)),
            "otkan_oy_qoshilganlar":    q("SELECT COUNT(*) FROM users WHERE created_at BETWEEN ? AND ?", (last_month_start, last_month_end)),
            "bugun_botni_ishlatganlar": q("SELECT COUNT(*) FROM users WHERE updated_at BETWEEN ? AND ?", (today_start, today_end)),
            "umumiy_azolar":            q("SELECT COUNT(*) FROM users"),
        }
        conn.close()
        return result

    except Exception as e:
        print(f"AdminHandler xatolik: {e}")
        return {}
