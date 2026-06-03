import json
import logging
import os
import sys

import requests
from dotenv import load_dotenv
from flask import Flask, request

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from handlers.main_handler import start_handler, main_handler
from handlers.search_handler import search_handler, download_handler, update_updated_at
from handlers.admin_handler import get_statistics
from lang import settings_cache

TOKEN    = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("CHAT_ID", "848796050"))

app      = Flask(__name__)
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

_bot_username: str | None = None


def get_bot_username() -> str:
    global _bot_username
    if _bot_username is None:
        resp = requests.get(f"{BASE_URL}/getMe", timeout=10)
        _bot_username = resp.json()["result"]["username"]
    return _bot_username


# ── Telegram API wrappers ─────────────────────────────────────────────────────

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML",
                 disable_web_page_preview=False):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if disable_web_page_preview:
        payload["disable_web_page_preview"] = True
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)


def send_document(chat_id, document, caption, reply_markup=None):
    payload = {
        "chat_id":    chat_id,
        "document":   document,
        "caption":    caption,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{BASE_URL}/sendDocument", json=payload, timeout=30)


def answer_callback_query(callback_query_id, text, show_alert=False):
    requests.post(f"{BASE_URL}/answerCallbackQuery", json={
        "callback_query_id": callback_query_id,
        "text":              text,
        "show_alert":        show_alert,
    }, timeout=10)


def delete_message(chat_id, message_id):
    requests.post(f"{BASE_URL}/deleteMessage", json={
        "chat_id":    chat_id,
        "message_id": message_id,
    }, timeout=10)


def edit_message_reply_markup(chat_id, message_id, reply_markup):
    requests.post(f"{BASE_URL}/editMessageReplyMarkup", json={
        "chat_id":      chat_id,
        "message_id":   message_id,
        "reply_markup": json.dumps(reply_markup),
    }, timeout=10)


# ── Webhook ───────────────────────────────────────────────────────────────────

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.json

    if "message" in data:
        _handle_message(data["message"])
    elif "callback_query" in data:
        _handle_callback(data["callback_query"])

    return "OK", 200


def _handle_message(message: dict) -> None:
    chat_id = message["chat"]["id"]

    if chat_id < 0 or "text" not in message:
        return

    text = message["text"]

    if text.startswith("/start"):
        send_message(chat_id, start_handler(message))

    elif text.startswith("/search"):
        send_message(chat_id, main_handler())

    elif text.startswith("/allusers"):
        if chat_id == ADMIN_ID:
            stats = get_statistics()
            send_message(
                chat_id,
                "📊 Statistika\n\n"
                f"📆 Bugun kirganlar: {stats.get('bugun_kirganlar', 0)} ta\n"
                f"📆 Bugun botni ishlatganlar: {stats.get('bugun_botni_ishlatganlar', 0)} ta\n\n"
                f"📅 Bu hafta qo'shilganlar: {stats.get('bu_hafta_qoshilganlar', 0)} ta\n"
                f"📆 Bu oy qo'shilganlar: {stats.get('bu_oy_qoshilganlar', 0)} ta\n"
                f"📅 O'tkan oy qo'shilganlar: {stats.get('otkan_oy_qoshilganlar', 0)} ta\n"
                f"👥 Umumiy a'zolar: {stats.get('umumiy_azolar', 0)} ta",
            )
        else:
            result_text, keyboard = search_handler(text)
            send_message(chat_id, result_text, reply_markup=keyboard,
                         disable_web_page_preview=True)
            update_updated_at(chat_id)

    elif text.startswith("/reload"):
        if chat_id == ADMIN_ID:
            settings_cache.force_refresh()
            send_message(chat_id, "✅ Sozlamalar qayta yuklandi.")

    elif text.startswith("/"):
        send_message(chat_id, main_handler())

    else:
        if len(text) < 3:
            send_message(chat_id, settings_cache.get("min_chars_text"))
            return
        result_text, keyboard = search_handler(text)
        send_message(chat_id, result_text, reply_markup=keyboard,
                     disable_web_page_preview=True)
        update_updated_at(chat_id)


def _handle_callback(query: dict) -> None:
    callback_id   = query["id"]
    callback_data = query["data"]
    message       = query["message"]
    chat_id       = message["chat"]["id"]
    message_id    = message["message_id"]

    if callback_data == "delete":
        delete_message(chat_id, message_id)

    elif callback_data == "like":
        answer_callback_query(
            callback_id,
            "Bot yoqqan bo'lsa do'stlaringizga ham ulashing!",
            show_alert=True,
        )
        old_keyboard = message.get("reply_markup", {}).get("inline_keyboard", [])
        new_keyboard = [
            [btn for btn in row if btn.get("callback_data") != "like"]
            for row in old_keyboard
        ]
        new_keyboard = [row for row in new_keyboard if row]
        edit_message_reply_markup(chat_id, message_id, {"inline_keyboard": new_keyboard})

        caption    = message.get("caption", "")
        first_name = message["chat"].get("first_name", "")
        send_message(ADMIN_ID, f"Bu fayl yoqdi!\n{caption}\nuser: {first_name}")

    else:
        try:
            book_id = int(callback_data)
        except (ValueError, TypeError):
            answer_callback_query(callback_id, "Noto'g'ri so'rov!", show_alert=True)
            return

        result = download_handler(book_id)
        if not result:
            answer_callback_query(callback_id, "Kitob topilmadi!", show_alert=True)
            return

        size_mb   = round(int(result[3]) / 1024 / 1024, 2)
        size_str  = str(size_mb).replace(".", ",")
        book_name = (
            result[1]
            .replace("@", "#")
            .replace("https://t.me/", "")
            .replace("https://", "")
            .replace("t.me/", "")
        )
        caption_tpl = settings_cache.get("file_caption_text")
        caption = caption_tpl.format(
            name=book_name,
            size=size_str,
            botname=get_bot_username(),
        )
        try:
            send_document(
                chat_id=chat_id,
                document=result[2],
                caption=caption,
                reply_markup={"inline_keyboard": [[
                    {"text": "❤️", "callback_data": "like"},
                    {"text": "❌", "callback_data": "delete"},
                ]]},
            )
        except Exception:
            answer_callback_query(callback_id, "Bu faylni yuklab bo'lmadi!", show_alert=True)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    get_bot_username()
    settings_cache.force_refresh()
    app.run(host="0.0.0.0", port=5000)
