# notification_service.py - Scheduled timetable notifications (EAT)
# Uses fixed UTC+3 offset (Tanzania has no DST - no tzdata needed)
import os
from datetime import datetime, timezone, timedelta
from database import get_connection
import push_service

# EAT = UTC+3 fixed offset (Africa/Dar_es_Salaam)
EAT = timezone(timedelta(hours=3), name="EAT")
DAILY_HOUR = int(os.getenv("DAILY_SCHEDULE_HOUR", "20"))


def now_eat():
    """Return current East Africa Time (UTC+3)."""
    return datetime.now(EAT)


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
        "WHERE t.day = ? AND (t.status IS NULL OR t.status = 'scheduled') "
        "ORDER BY t.start_time", (day,)).fetchall()
    conn.close()
    return rows


def process_due_notifications():
    """Called every minute by cron. Uses EAT timezone."""
    now = now_eat()
    today = now.strftime("%Y-%m-%d")
    today_weekday = now.strftime("%A")
    results = {
        "eat_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "daily": 0, "reminder_30": 0, "reminder_10": 0, "errors": []
    }

    # 1. DAILY "TOMORROW'S SCHEDULE" at configured hour
    if now.hour == DAILY_HOUR and now.minute <= 1:
        tomorrow_weekday = (now + timedelta(days=1)).strftime("%A")
        tomorrow_entries = _get_entries_for_day(tomorrow_weekday)
        if tomorrow_entries:
            lines = ["Kesho (" + tomorrow_weekday + "):"]
            for e in tomorrow_entries:
                line = "- " + str(e["start_time"]) + "-" + str(e["end_time"] or "?") + " " + str(e["title"])
                if e["venue"]:
                    line += " @ " + str(e["venue"])
                lines.append(line)
            body = chr(10).join(lines)
            notif_key = "daily_" + today
            for user in _get_all_active_users():
                uid = user["id"]
                if push_service.was_sent(uid, notif_key):
                    continue
                try:
                    title = "\U0001F4C5 Ratiba ya Kesho"
                    push_service.send_push(uid, title, body, "/timetable", tag="daily")
                    push_service.mark_sent(uid, notif_key)
                    results["daily"] += 1
                except Exception as e:
                    results["errors"].append(str(e))

    # 2 & 3. 30-MIN AND 10-MIN REMINDERS
    today_entries = _get_entries_for_day(today_weekday)
    for entry in today_entries:
        if not entry["start_time"]:
            continue
        try:
            start_dt = datetime.strptime(
                today + " " + str(entry["start_time"]), "%Y-%m-%d %H:%M"
            ).replace(tzinfo=EAT)
        except (ValueError, TypeError):
            continue
        diff = (start_dt - now).total_seconds() / 60

        reminders = [
            (30, "rem30", "\u23F0 Kipindi Kinaanza Dakika 30",
             "'" + str(entry["title"]) + "' kinaanza saa " + str(entry["start_time"]) + ". Jiandae, kusanya vifaa vyako.",
             "reminder_30"),
            (10, "rem10", "\U0001F680 Kipindi Kinaanza Dakika 10",
             "Hope you're almost near or at the class - jipange, jiandae kwa '" + str(entry["title"]) + "' inayokuja!",
             "reminder_10"),
        ]

        for minutes, key_suffix, title, body_tpl, results_key in reminders:
            if minutes - 2 <= diff <= minutes + 2:
                notif_key = key_suffix + "_" + today + "_" + str(entry["id"])
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