# notification_service.py — Scheduled timetable notifications
import os
from datetime import datetime, timedelta
from database import get_connection
import push_service

DAILY_HOUR = int(os.getenv("DAILY_SCHEDULE_HOUR", "20"))  # 20 = 8 PM


def _get_all_active_users():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, role FROM users WHERE id IN "
        "(SELECT user_id FROM push_subscriptions)").fetchall()
    conn.close()
    return rows


def _get_entries_for_day(day):
    conn = get_connection()
    rows = conn.execute(
        "SELECT t.*, COALESCE(t.session_name, m.name, 'Session') AS title "
        "FROM timetable t LEFT JOIN modules m ON t.module_id = m.id "
        "WHERE t.day = ? ORDER BY t.start_time", (day,)).fetchall()
    conn.close()
    return rows


def process_due_notifications():
    """Called every minute. Checks and sends due notifications."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    today_weekday = now.strftime("%A")
    results = {"daily": 0, "reminder_30": 0, "reminder_10": 0, "errors": []}

    # ========== 1. DAILY "TOMORROW'S SCHEDULE" at configured hour ==========
    if now.hour == DAILY_HOUR and now.minute <= 1:
        tomorrow_weekday = (now + timedelta(days=1)).strftime("%A")
        tomorrow_entries = _get_entries_for_day(tomorrow_weekday)
        if tomorrow_entries:
            body = "Kesho (" + tomorrow_weekday + "):\n"
            for e in tomorrow_entries:
                body += f"• {e['start_time']}-{e['end_time'] or '?'} {e['title']}"
                if e["venue"]:
                    body += f" @ {e['venue']}"
                body += "\n"
            notif_key = f"daily_{today}"
            for user in _get_all_active_users():
                uid = user["id"]
                if push_service.was_sent(uid, notif_key):
                    continue
                try:
                    push_service.send_push(uid, "📅 Ratiba ya Kesho", body.strip(), "/timetable", tag="daily")
                    push_service.mark_sent(uid, notif_key)
                    results["daily"] += 1
                except Exception as e:
                    results["errors"].append(str(e))

    # ========== 2 & 3. 30-MIN AND 10-MIN REMINDERS ==========
    today_entries = _get_entries_for_day(today_weekday)
    for entry in today_entries:
        if not entry["start_time"]:
            continue
        try:
            start_dt = datetime.strptime(f"{today} {entry['start_time']}", "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        diff = (start_dt - now).total_seconds() / 60

        for minutes, key_suffix, title, body_tpl, results_key in [
            (30, "rem30", "⏰ Kipindi Kinaanza Dakika 30",
             f"'{entry['title']}' kinaanza saa {entry['start_time']}. Jiandae, kusanya vifaa vyako.",
             "reminder_30"),
            (10, "rem10", "🚀 Kipindi Kinaanza Dakika 10",
             f"Hope you're almost near or at the class — jipange, jiandae kwa '{entry['title']}' inayokuja!",
             "reminder_10"),
        ]:
            if minutes - 2 <= diff <= minutes + 2:
                notif_key = f"{key_suffix}_{today}_{entry['id']}"
                for user in _get_all_active_users():
                    uid = user["id"]
                    if push_service.was_sent(uid, notif_key):
                        continue
                    try:
                        push_service.send_push(uid, title, body_tpl, "/timetable", tag=key_suffix)
                        push_service.mark_sent(uid, notif_key)
                        results[results_key] += 1
                    except Exception as e:
                        results["errors"].append(str(e))

    return results