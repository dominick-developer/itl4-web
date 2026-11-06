# add_routes.py
from pathlib import Path
import re

ROUTES = '''

# ============================================================
# ADMIN ADD STUDENT (CR only)
# ============================================================
@app.post("/students/admin-add")
def student_admin_add(request: Request,
                       full_name: str = Form(...),
                       admission_no: str = Form(...),
                       phone: str = Form(...),
                       email: str = Form(""),
                       gender: str = Form(""),
                       password: str = Form("it2026")):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    ok, msg = db.admin_add_student(
        full_name=full_name, admission_no=admission_no,
        phone=phone, email=email, gender=gender,
        password=(password or "it2026"))
    from urllib.parse import quote
    key = "success" if ok else "error"
    return RedirectResponse(f"/students?{key}={quote(msg)}", 303)


# ============================================================
# AUTO-GROUPING (CR only)
# ============================================================
@app.post("/groups/auto-group")
def groups_auto_group(request: Request):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    try:
        result = db.auto_group_ungrouped_students()
        from urllib.parse import quote
        if result.get("created", 0) > 0:
            msg = "Groups " + str(result["created"]) + " zimeundwa, " + str(result["remaining"]) + " wanafunzi bado hawajawekwa"
            return RedirectResponse(f"/groups?success={quote(msg)}", 303)
        else:
            msg = result.get("message") or "Hakuna wanafunzi wa ku-group (min 9)"
            return RedirectResponse(f"/groups?error={quote(msg)}", 303)
    except Exception as e:
        from urllib.parse import quote
        return RedirectResponse(f"/groups?error={quote(str(e))}", 303)


@app.post("/groups/{gid}/remove-member/{sid}")
def group_remove_member(request: Request, gid: int, sid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    conn = db.get_connection()
    conn.execute("DELETE FROM group_members WHERE group_id = ? AND student_id = ?", (gid, sid))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/groups/{gid}?success=Member+removed", 303)
'''

p = Path("main.py")
content = p.read_text(encoding="utf-8")

if "students/admin-add" in content and "groups/auto-group" in content:
    print("[OK] Routes already exist — skipping")
else:
    content = content.rstrip() + ROUTES
    p.write_text(content, encoding="utf-8")
    print("[OK] Added routes to main.py")

# Verify syntax
import ast
try:
    ast.parse(content)
    print("[OK] Syntax OK")
except SyntaxError as e:
    print(f"[ERROR] Syntax error at line {e.lineno}: {e.msg}")