# fix_group_v2.py — Simplified (no complex fallback)
from pathlib import Path

# ============================================================
# 1. ADD functions to database.py
# ============================================================
DB_ADD = """

# ============================================================
# GROUPING DIAGNOSTICS + BULK APPROVE
# ============================================================
def get_grouping_diagnostics():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM students WHERE is_active = 1").fetchone()[0]
    approved = conn.execute(
        "SELECT COUNT(*) FROM students WHERE is_active = 1 AND membership_status = 'approved'"
    ).fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM students WHERE is_active = 1 AND membership_status = 'pending'"
    ).fetchone()[0]
    in_groups = conn.execute(
        "SELECT COUNT(DISTINCT student_id) FROM group_members"
    ).fetchone()[0]
    ungrouped = conn.execute(
        "SELECT COUNT(*) FROM students WHERE is_active = 1 AND membership_status = 'approved' "
        "AND id NOT IN (SELECT student_id FROM group_members)"
    ).fetchone()[0]
    conn.close()
    return {
        "total_active": total,
        "approved": approved,
        "pending": pending,
        "in_groups": in_groups,
        "ungrouped_approved": ungrouped,
    }


def approve_all_pending():
    conn = get_connection()
    result = conn.execute(
        "UPDATE students SET membership_status = 'approved', "
        "date_joined = COALESCE(date_joined, date('now')) "
        "WHERE is_active = 1 AND membership_status = 'pending'"
    )
    count = result.rowcount
    conn.commit()
    conn.close()
    return count
"""

p = Path("database.py")
content = p.read_text(encoding="utf-8")
if "get_grouping_diagnostics" in content:
    print("[OK] Functions already in database.py")
else:
    content = content.rstrip() + DB_ADD
    p.write_text(content, encoding="utf-8")
    print("[OK] Added diagnostics + approve_all_pending")


# ============================================================
# 2. REPLACE auto-group route with diagnostic version
# ============================================================
p = Path("main.py")
content = p.read_text(encoding="utf-8")

old_route = """        result = db.auto_group_ungrouped_students()
        from urllib.parse import quote
        if result.get("created", 0) > 0:
            msg = "Groups " + str(result["created"]) + " zimeundwa, " + str(result["remaining"]) + " wanafunzi bado hawajawekwa"
            return RedirectResponse(f"/groups?success={quote(msg)}", 303)
        else:
            msg = result.get("message") or "Hakuna wanafunzi wa ku-group (min 9)"
            return RedirectResponse(f"/groups?error={quote(msg)}", 303)"""

new_route = """        result = db.auto_group_ungrouped_students()
        from urllib.parse import quote
        if result.get("created", 0) > 0:
            msg = "Groups " + str(result["created"]) + " zimeundwa, " + str(result["remaining"]) + " wanafunzi bado hawajawekwa"
            return RedirectResponse(f"/groups?success={quote(msg)}", 303)
        else:
            try:
                diag = db.get_grouping_diagnostics()
                msg = (
                    "Hakuna wanafunzi wa ku-group. "
                    "Active: " + str(diag["total_active"]) + ", "
                    "Approved: " + str(diag["approved"]) + ", "
                    "Pending: " + str(diag["pending"]) + ", "
                    "In groups: " + str(diag["in_groups"]) + ", "
                    "Ungrouped approved: " + str(diag["ungrouped_approved"])
                )
            except Exception:
                msg = "Hakuna wanafunzi wa ku-group (min 9)"
            return RedirectResponse(f"/groups?error={quote(msg)}", 303)"""

if new_route in content:
    print("[OK] Route already updated")
elif old_route in content:
    content = content.replace(old_route, new_route)
    print("[OK] Updated auto-group route with diagnostics")
else:
    print("[WARN] Route pattern not found — checking manually")
    if 'def groups_auto_group' in content:
        print("       Function exists — but body may have changed")
        print("       Recommend: paste route manually")
    else:
        print("       Function groups_auto_group NOT FOUND — route missing!")

# ============================================================
# 3. ADD delete + approve-all routes
# ============================================================
routes_add = """

# ============================================================
# GROUP DELETE + APPROVE ALL (CR)
# ============================================================
@app.post("/groups/{gid}/delete")
def group_delete(request: Request, gid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    try:
        conn = db.get_connection()
        conn.execute("DELETE FROM groups WHERE id = ?", (gid,))
        conn.commit()
        conn.close()
        from urllib.parse import quote
        return RedirectResponse("/groups?success=" + quote("Group imefutwa"), 303)
    except Exception as e:
        from urllib.parse import quote
        return RedirectResponse("/groups?error=" + quote(str(e)), 303)


@app.post("/students/approve-all-pending")
def students_approve_all_pending(request: Request):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    try:
        count = db.approve_all_pending()
        from urllib.parse import quote
        return RedirectResponse("/students?success=" + quote("Wanafunzi " + str(count) + " wamekubaliwa"), 303)
    except Exception as e:
        from urllib.parse import quote
        return RedirectResponse("/students?error=" + quote(str(e)), 303)
"""

if 'groups/{gid}/delete' in content:
    print("[OK] Delete route already exists")
else:
    content = content.rstrip() + routes_add
    print("[OK] Added delete + approve-all routes")

p.write_text(content, encoding="utf-8")

# Verify
import ast
try:
    ast.parse(content)
    print("[OK] Syntax OK")
except SyntaxError as e:
    print("[ERROR] Line " + str(e.lineno) + ": " + str(e.msg))