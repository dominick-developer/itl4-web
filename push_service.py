# push_service.py — Web Push Notifications
import os
import json
from pywebpush import webpush, WebPushException
from database import get_connection

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS = {"sub": "mailto:noreply@smartbizsenseapp.com"}


def init_push_table():
    conn = get_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS push_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        endpoint TEXT NOT NULL UNIQUE,
        p256dh TEXT NOT NULL,
        auth TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS push_notification_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        notif_key TEXT NOT NULL,
        sent_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(user_id, notif_key)
    )""")
    conn.commit()
    conn.close()


def save_subscription(user_id, subscription):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO push_subscriptions (user_id, endpoint, p256dh, auth) "
            "VALUES (?, ?, ?, ?)",
            (user_id, subscription["endpoint"],
             subscription["keys"]["p256dh"], subscription["keys"]["auth"]))
        conn.commit()
    finally:
        conn.close()


def remove_subscription(user_id, endpoint):
    conn = get_connection()
    conn.execute(
        "DELETE FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
        (user_id, endpoint))
    conn.commit()
    conn.close()


def send_push(user_id, title, body, url="/timetable", tag="timetable"):
    if not VAPID_PRIVATE_KEY:
        return {"ok": False, "error": "VAPID not configured"}
    conn = get_connection()
    subs = conn.execute(
        "SELECT * FROM push_subscriptions WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    if not subs:
        return {"ok": False, "error": "No subscriptions"}

    sent = 0
    for sub in subs:
        payload = json.dumps({
            "title": title, "body": body, "url": url, "tag": tag,
        })
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
            )
            sent += 1
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                conn = get_connection()
                conn.execute("DELETE FROM push_subscriptions WHERE id = ?", (sub["id"],))
                conn.commit()
                conn.close()
    return {"ok": True, "sent": sent}


def was_sent(user_id, notif_key):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM push_notification_log WHERE user_id = ? AND notif_key = ?",
        (user_id, notif_key)).fetchone()
    conn.close()
    return row is not None


def mark_sent(user_id, notif_key):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO push_notification_log (user_id, notif_key) "
            "VALUES (?, ?)", (user_id, notif_key))
        conn.commit()
    finally:
        conn.close()