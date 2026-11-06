# add_push.py - Ongeza push endpoints kwenye main.py
from pathlib import Path

p = Path("main.py")
content = p.read_text(encoding="utf-8")

if "/api/push/vapid-public-key" in content:
    print("✅ Endpoints already exist")
    exit(0)

ENDPOINTS = '''


# ============================================================
# PUSH NOTIFICATIONS ENDPOINTS
# ============================================================
@app.get("/api/push/vapid-public-key")
def get_vapid_public():
    return {"publicKey": os.getenv("VAPID_PUBLIC_KEY", "")}


@app.post("/api/push/subscribe")
async def push_subscribe(request: Request):
    if "user_id" not in request.session:
        raise HTTPException(401)
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, detail="Invalid JSON")
    if not data or "endpoint" not in data or "keys" not in data:
        raise HTTPException(400, detail="Missing endpoint or keys")
    try:
        import push_service
        push_service.save_subscription(request.session["user_id"], data)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/push/unsubscribe")
async def push_unsubscribe(request: Request):
    if "user_id" not in request.session:
        raise HTTPException(401)
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400)
    try:
        import push_service
        push_service.remove_subscription(
            request.session["user_id"], data.get("endpoint", ""))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/push/test")
def push_test(request: Request):
    if "user_id" not in request.session:
        raise HTTPException(401)
    try:
        import push_service
        result = push_service.send_push(
            request.session["user_id"],
            "🔔 IT Level 4 Connect",
            "Push notifications zinafanya kazi! Utapokea taarifa za ratiba.",
            "/timetable")
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# CRON ENDPOINT (Kwa cron-job.org)
# ============================================================
@app.get("/internal/send-notifications")
def trigger_notifications(secret: str = ""):
    if secret != os.getenv("CRON_SECRET", ""):
        raise HTTPException(403)
    try:
        import notification_service
        return notification_service.process_due_notifications()
    except ImportError:
        return {"error": "notification_service not found", "daily": 0}
    except Exception as e:
        return {"error": str(e), "daily": 0}
'''

new_content = content.rstrip() + "\n" + ENDPOINTS

backup = p.with_suffix(".py.bak_push")
backup.write_text(content, encoding="utf-8")
print(f"📁 Backup: {backup}")

p.write_text(new_content, encoding="utf-8")
print(f"✅ Wrote main.py ({len(new_content.splitlines())} lines)")

import ast
try:
    ast.parse(new_content)
    print("✅ Syntax OK")
except SyntaxError as e:
    print(f"❌ Syntax error at line {e.lineno}: {e.msg}")