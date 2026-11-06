# fix_modules.py — Fix module create UNIQUE + add edit routes
from pathlib import Path
import re
import ast

p = Path("main.py")
content = p.read_text(encoding="utf-8")
original = content

# ============================================================
# FIX 1: Replace module_create_post
# ============================================================
new_create = '''@app.post("/modules/create")
def module_create_post(request: Request,
                       name: str = Form(...),
                       code: str = Form(""),
                       description: str = Form(""),
                       academic_year: str = Form("2024/2025"),
                       semester: str = Form("Semester 1"),
                       teacher_id: str = Form("")):
    require_login(request)
    if request.session["role"] != "CR":
        raise HTTPException(403)
    
    name = name.strip()
    if not name:
        return render("module_form.html", ctx(request, {
            "teachers": db.get_all_teachers(),
            "error": "Jina la module linahitajika.",
            "form_data": {"name": name, "code": code, "description": description,
                         "teacher_id": teacher_id, "academic_year": academic_year,
                         "semester": semester},
        }))
    
    # Check if module with same name exists
    existing = None
    try:
        conn = db.get_connection()
        existing = conn.execute(
            "SELECT id FROM modules WHERE LOWER(name) = LOWER(?)",
            (name,)).fetchone()
        conn.close()
    except Exception as _e:
        print(f"⚠️ Module lookup failed: {_e}")
    
    if existing:
        module_id = existing["id"]
        print(f"✅ Reusing existing module '{name}' (id={module_id})")
    else:
        ok, module_id, msg = db.add_module(name, code, description)
        if not ok:
            return render("module_form.html", ctx(request, {
                "teachers": db.get_all_teachers(),
                "error": msg,
                "form_data": {"name": name, "code": code, "description": description,
                             "teacher_id": teacher_id, "academic_year": academic_year,
                             "semester": semester},
            }))
    
    # Create offering
    tid = int(teacher_id) if teacher_id else None
    try:
        db.create_offering(module_id, "IT Level 4", academic_year, semester, tid)
    except Exception as _e:
        return render("module_form.html", ctx(request, {
            "teachers": db.get_all_teachers(),
            "error": f"Imeshindwa kuunda offering: {_e}",
            "form_data": {"name": name, "code": code, "description": description,
                         "teacher_id": teacher_id, "academic_year": academic_year,
                         "semester": semester},
        }))
    
    return RedirectResponse("/modules", 303)
'''

pattern = r'@app\.post\("/modules/create"\)[\s\S]*?(?=@app\.|# ={3,}|\Z)'
if re.search(pattern, content):
    content = re.sub(pattern, new_create + "\n\n", content, count=1)
    print("✅ Replaced module_create_post")
else:
    print("⚠️ module_create_post pattern not found")

# ============================================================
# FIX 2: Add edit routes (before /modules/{oid}/delete)
# ============================================================
edit_routes = '''# ============================================================
# MODULE EDIT (CR only — works even after publish)
# ============================================================
@app.get("/modules/{oid}/edit", response_class=HTMLResponse)
def module_edit_get(request: Request, oid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    o = db.get_offering(oid)
    if not o:
        raise HTTPException(404)
    return render("module_form.html", ctx(request, {
        "teachers": db.get_all_teachers(),
        "offering": o,
        "is_edit": True,
        "form_data": {
            "name": o["module_name"] or "",
            "code": o["module_code"] or "",
            "description": o["module_desc"] or "",
            "academic_year": o["academic_year"] or "2024/2025",
            "semester": o["semester"] or "Semester 1",
            "teacher_id": str(o["teacher_id"]) if o["teacher_id"] else "",
        },
    }))


@app.post("/modules/{oid}/edit")
def module_edit_post(request: Request, oid: int,
                     name: str = Form(...),
                     code: str = Form(""),
                     description: str = Form(""),
                     academic_year: str = Form("2024/2025"),
                     semester: str = Form("Semester 1"),
                     teacher_id: str = Form("")):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    o = db.get_offering(oid)
    if not o:
        raise HTTPException(404)
    
    name = name.strip()
    if not name:
        return render("module_form.html", ctx(request, {
            "teachers": db.get_all_teachers(),
            "offering": o, "is_edit": True,
            "error": "Jina la module linahitajika.",
            "form_data": {"name": name, "code": code, "description": description,
                         "teacher_id": teacher_id, "academic_year": academic_year,
                         "semester": semester},
        }))
    
    # Check duplicate name (excluding this module)
    dup = None
    try:
        conn = db.get_connection()
        dup = conn.execute(
            "SELECT id FROM modules WHERE LOWER(name) = LOWER(?) AND id != ?",
            (name, o["module_id"])).fetchone()
        conn.close()
    except Exception as _e:
        print(f"⚠️ Dup check failed: {_e}")
    
    if dup:
        return render("module_form.html", ctx(request, {
            "teachers": db.get_all_teachers(),
            "offering": o, "is_edit": True,
            "error": f"Module nyingine inaitwa '{name}'. Chagua jina lingine.",
            "form_data": {"name": name, "code": code, "description": description,
                         "teacher_id": teacher_id, "academic_year": academic_year,
                         "semester": semester},
        }))
    
    ok, msg = db.update_module(o["module_id"], name, code, description)
    if not ok:
        return render("module_form.html", ctx(request, {
            "teachers": db.get_all_teachers(),
            "offering": o, "is_edit": True, "error": msg,
            "form_data": {"name": name, "code": code, "description": description,
                         "teacher_id": teacher_id, "academic_year": academic_year,
                         "semester": semester},
        }))
    
    # Update offering fields
    tid = int(teacher_id) if teacher_id else None
    try:
        conn = db.get_connection()
        conn.execute(
            "UPDATE module_offerings SET teacher_id = ?, academic_year = ?, semester = ? WHERE id = ?",
            (tid, academic_year, semester, oid))
        conn.commit()
        conn.close()
    except Exception as _e:
        print(f"⚠️ Offering update failed: {_e}")
    
    return RedirectResponse(f"/modules/{oid}", 303)


'''

marker = '@app.post("/modules/{oid}/delete")'
if marker in content and '@app.get("/modules/{oid}/edit"' not in content:
    content = content.replace(marker, edit_routes + marker, 1)
    print("✅ Inserted edit routes")
elif '@app.get("/modules/{oid}/edit"' in content:
    print("⚠️ Edit routes already exist")
else:
    print("⚠️ Cannot find /modules/{oid}/delete — appending at end")
    content = content + "\n\n" + edit_routes

# ============================================================
# Save + verify
# ============================================================
if content != original:
    backup = p.with_suffix(".py.bak_modfix")
    backup.write_text(original, encoding="utf-8")
    print(f"📁 Backup: {backup}")
    p.write_text(content, encoding="utf-8")
    print(f"✅ Wrote main.py ({len(content.splitlines())} lines)")
else:
    print("⚠️ No changes made")

try:
    ast.parse(content)
    print("✅ Syntax OK")
except SyntaxError as e:
    print(f"❌ Syntax error at line {e.lineno}: {e.msg}")
    print(f"   Text: {e.text}")