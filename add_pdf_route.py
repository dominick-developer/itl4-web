# add_pdf_route.py
from pathlib import Path

ROUTE = '''

# ============================================================
# EXPORT GROUPS PDF
# ============================================================
@app.get("/groups/export-pdf")
def groups_export_pdf(request: Request):
    require_login(request)
    if request.session.get("role") not in ("CR", "LECTURER"):
        raise HTTPException(403)
    
    try:
        import pdf_export
    except ImportError:
        raise HTTPException(500, detail="pdf_export module not found. Run: pip install reportlab")
    
    # Build groups data with members
    conn = db.get_connection()
    groups_rows = conn.execute(
        "SELECT g.*, (SELECT COUNT(*) FROM group_members gm WHERE gm.group_id = g.id) AS cnt "
        "FROM groups g ORDER BY g.id ASC"
    ).fetchall()
    
    groups_data = []
    for g in groups_rows:
        members = conn.execute(
            "SELECT s.full_name, s.gender, s.phone "
            "FROM group_members gm "
            "JOIN students s ON gm.student_id = s.id "
            "WHERE gm.group_id = ? "
            "ORDER BY s.full_name ASC",
            (g["id"],)).fetchall()
        groups_data.append({
            "name": g["name"],
            "description": g["description"] or "",
            "members": [dict(m) for m in members],
        })
    conn.close()
    
    try:
        pdf_bytes = pdf_export.generate_groups_pdf(groups_data)
    except Exception as e:
        import traceback
        raise HTTPException(500, detail=f"PDF generation failed: {e}\\n{traceback.format_exc()[-500:]}")
    
    from fastapi.responses import Response
    from datetime import datetime as _dt
    ts = _dt.now().strftime("%Y%m%d")
    filename = f"Groups_Distribution_2026_{ts}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
'''

p = Path("main.py")
content = p.read_text(encoding="utf-8")

if "groups/export-pdf" in content:
    print("[OK] PDF route already exists — skipping")
else:
    content = content.rstrip() + ROUTE
    p.write_text(content, encoding="utf-8")
    print("[OK] Added PDF route")

import ast
try:
    ast.parse(content)
    print("[OK] Syntax OK")
except SyntaxError as e:
    print(f"[ERROR] Syntax error at line {e.lineno}: {e.msg}")