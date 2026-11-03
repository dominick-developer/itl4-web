# âœ… IWE HIVI
import os
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
from pathlib import Path
from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
import base64
import push_service

import database as db
import auth
import academy_db as academy
import legal_db as legal
import ai_service
from email_service import send_verification_email

BASE_DIR = Path(__file__).parent
app = FastAPI(title="IT Level 4 Connect")
app.add_middleware(SessionMiddleware, secret_key="itl4-secret-2026")

(BASE_DIR / "static").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def render(name: str, context: dict):
    """Render a Jinja2 template (Starlette 1.0+ compatible)."""
    request = context.get("request")
    if request is None:
        raise ValueError("context must include 'request'")
    return templates.TemplateResponse(request, name, context)
# ============================================================
# PUSH NOTIFICATIONS
# ============================================================
@app.get("/api/push/vapid-public-key")
def get_vapid_public():
    return {"publicKey": os.getenv("VAPID_PUBLIC_KEY", "")}


@app.post("/api/push/unsubscribe")
async def push_unsubscribe(request: Request):
    if "user_id" not in request.session:
        raise HTTPException(401)
    data = await request.json()
    push_service.remove_subscription(request.session["user_id"], data.get("endpoint", ""))
    return {"ok": True}


@app.on_event("startup")
def startup():
    # 1. Init database (migrations za columns mpya zipo ndani ya init_database)
    db.init_database()
    try:
        db.migrate_attendance_system()
        print("✅ Attendance migration ready")
    except Exception as _e:
        print(f"⚠️ Attendance migration: {_e}")
        db.migrate_timetable_status()
        print("✅ Timetable status migration ready")
    except Exception as _e:
        print(f"⚠️ Timetable migration: {_e}")
        print("✅ Attendance migration ready")
    except Exception as _e:
        print(f"⚠️ Attendance migration: {_e}")
    print("âœ… Database ready")
    academy.init_academy()
    
    try:
        db.init_materials_table()
        print("✅ Materials table ready")
    except Exception as _e:
        print(f"⚠️ Materials init: {_e}")
    
    # Clean up unused sample modules
    try:
        _del, _kept = db.cleanup_unused_seed_modules()
        if _del > 0:
            print(f"✅ Cleaned up {_del} unused sample module(s) ({_kept} kept)")
    except Exception as _e:
        print(f"⚠️ Seed cleanup failed: {_e}")
    try:
        legal.init_legal_tables()
        print("✅ Legal tables ready")
    except Exception as _e:
        print(f"⚠️ Legal init failed: {_e}")
    academy.init_ai_tables()
    academy.init_coding_tables()
    try:
        import push_service
        push_service.init_push_table()
        print("✅ Push tables ready")
    except Exception as _e:
        print(f"⚠️ Push init failed: {_e}")
    print("✅ Academy ready")

    # PHASE 1: Career + Web Design modules seeds
    try:
        academy.init_career_tables()
        print("✅ Career + Web Design seeds complete")
    except Exception as _e:
        print(f"⚠️  init_career_tables failed: {_e}")

    # PHASE 2: Portfolio + Certificates + Achievements (if exists)
    try:
        if hasattr(academy, "init_phase6_tables"):
            academy.init_phase6_tables()
            print("✅ Phase 6 tables complete")
    except Exception as _e:
        print(f"⚠️  init_phase6_tables failed: {_e}")


    # FORCE-PUBLISH all courses with lessons (startup safety)
    try:
        _c = db.get_connection()
        _c.execute("UPDATE academy_courses SET status = 'published' WHERE slug = 'web-design-development'")
        _c.commit()
        _r = _c.execute("SELECT status FROM academy_courses WHERE slug = 'web-design-development'").fetchone()
        _n = _c.execute("SELECT COUNT(*) FROM lessons WHERE status = 'published'").fetchone()[0]
        print(f"FORCE-PUBLISH: status={_r[0] if _r else 'NOT FOUND'}, lessons={_n}")
        _c.close()
    except Exception as _e:
        print(f"FORCE-PUBLISH FAILED: {_e}")

    # 2. Hakikisha CR 'cr' yupo na ana password 123456
    import hashlib, os
    conn = db.get_connection()
    row = conn.execute(
        "SELECT u.id FROM users u WHERE u.username = 'cr'"
    ).fetchone()

    salt = os.urandom(16).hex()
    pwd_hash = hashlib.sha256((salt + "123456").encode()).hexdigest()

    if not row:
        # Unda CR mpya
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO students (full_name, reg_number, phone, is_active, "
            "membership_status, date_joined, is_verified) "
            "VALUES (?, ?, ?, 1, 'approved', date('now'), 1)",
            ("Class Representative", "ITL4/CR/001", "0700111111"))
        sid = cur.lastrowid
        cur.execute(
            "INSERT INTO users (role, student_id, username, password_hash, salt, is_admin) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            ("CR", sid, "cr", pwd_hash, salt))
        conn.commit()
        print("âœ… CR 'cr' created with password 123456")
    else:
        # Update password kuwa 123456 kila app inapowaka
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE username = 'cr'",
            (pwd_hash, salt))
        conn.commit()
        print("âœ… CR 'cr' password reset to 123456")

    conn.close()


def require_login(request: Request):
    if "user_id" not in request.session:
        raise HTTPException(status_code=303, headers={"Location": "/login"})


def ctx(request, extra=None):
    d = {
        "request": request,
        "role": request.session.get("role", "STUDENT"),
        "full_name": request.session.get("full_name", "User"),
        "user_id": request.session.get("user_id"),
        "now": datetime.now(),
    }
    # Load logo from settings (base64 data URI)
    try:
        logo_b64 = db.get_setting("logo_base64", "")
        d["logo_data_uri"] = f"data:image/png;base64,{logo_b64}" if logo_b64 else None
    except Exception:
        d["logo_data_uri"] = None
    if extra:
        d.update(extra)
    return d
@app.get("/academy", response_class=HTMLResponse)
def academy_page(request: Request):
    logged_in = "user_id" in request.session
    return render("academy.html", {
        "request": request,
        "logged_in": logged_in,
        "role": request.session.get("role"),
        "full_name": request.session.get("full_name"),
        "now": datetime.now(),
    })
# ============================================================
# AUTH
# ============================================================
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    if "user_id" in request.session:
        return RedirectResponse("/dashboard", 303)
    return render("landing.html", ctx(request))


@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if "user_id" in request.session:
        return RedirectResponse("/dashboard", 303)
    return render("login.html", {"request": request, "error": None, "success": None})

@app.post("/login", response_class=HTMLResponse)
def login_post(request: Request, username: str = Form(...),
               password: str = Form(...)):
    ok, result = auth.login(username, password)
    if ok:
        request.session.update({
            "user_id": result["id"],
            "role": result["role"],
            "full_name": result["full_name"],
            "student_id": result.get("student_id"),
        })
        return RedirectResponse("/dashboard", 303)

    if isinstance(result, dict) and result.get("verify_needed"):
        return RedirectResponse(f"/verify?username={result['username']}", 303)

    return render("login.html", {"request": request, "error": result, "success": None})
@app.get("/signup", response_class=HTMLResponse)
def signup_get(request: Request):
    if "user_id" in request.session:
        return RedirectResponse("/dashboard", 303)
    return render("signup.html", {"request": request, "error": None})


@app.post("/signup", response_class=HTMLResponse)
def signup_post(request: Request, full_name: str = Form(...),
                admission_no: str = Form(...),
                phone: str = Form(...),
                email: str = Form(...),
                gender: str = Form(""),
                password: str = Form(...),
                confirm_password: str = Form(...),
                role: str = Form("STUDENT"),
                accept_terms: str = Form(""),
                accept_privacy: str = Form("")):
    # Legal consent check
    if accept_terms != "on":
        return render("signup.html", {
            "request": request,
            "error": "Lazima ukubali Terms & Conditions ili kuendelea.",
        })
    if accept_privacy != "on":
        return render("signup.html", {
            "request": request,
            "error": "Lazima ukubali Privacy Policy ili kuendelea.",
        })

    if password != confirm_password:
        return render("signup.html", {
            "request": request,
            "error": "Password na Confirm Password hazifanani.",
        })

    ok, info, msg = db.signup_student(
        admission_no=admission_no, password=password,
        full_name=full_name, phone=phone, email=email,
        gender=gender, role=role,
    )

    if not ok:
        return render("signup.html", {"request": request, "error": msg})

    # Record legal acceptances
    try:
        terms_doc = legal.get_current_document("terms")
        privacy_doc = legal.get_current_document("privacy")
        if terms_doc:
            legal.record_acceptance(
                info["user_id"], terms_doc["id"], "terms",
                terms_doc["version"], "signup")
        if privacy_doc:
            legal.record_acceptance(
                info["user_id"], privacy_doc["id"], "privacy",
                privacy_doc["version"], "signup")
    except Exception as _e:
        print(f"⚠️ Legal acceptance recording failed: {_e}")

    if role == "CR":
        return RedirectResponse(
            "/login?success=CR+account+created.+You+can+log+in+now.", 303)

    email_ok, email_err = send_verification_email(
        info["email"], info["full_name"], info["code"])

    if not email_ok:
        return RedirectResponse(
            f"/verify?username={info['admission_no']}&warning=1", 303)

    return RedirectResponse(
        f"/verify?username={info['admission_no']}", 303)
    if password != confirm_password:
        return render("signup.html", {
            "request": request,
            "error": "Password na Confirm Password hazifanani.",
        })

    ok, info, msg = db.signup_student(
        admission_no=admission_no, password=password,
        full_name=full_name, phone=phone, email=email,
        gender=gender, role=role,
    )

    if not ok:
        return render("signup.html", {"request": request, "error": msg})

    # CR hahitaji verification â€” login moja kwa moja
    if role == "CR":
        return RedirectResponse("/login?success=CR+account+created.+You+can+log+in+now.", 303)

    # STUDENT anahitaji email verification
    email_ok, email_err = send_verification_email(
        info["email"], info["full_name"], info["code"])

    if not email_ok:
        return RedirectResponse(
            f"/verify?username={info['admission_no']}&warning=1", 303)

    return RedirectResponse(
        f"/verify?username={info['admission_no']}", 303)
@app.get("/verify", response_class=HTMLResponse)
def verify_get(request: Request, username: str = "", warning: int = 0):
    warning_msg = None
    if warning:
        warning_msg = (
            "Akaunti imeundwa lakini email ya uthibitisho haijatumwa. "
            "Bonyeza 'Resend Code' chini, au wasiliana na msimamizi.")
    return render("verify.html", {
        "request": request,
        "username": username.upper(),
        "error": warning_msg,
        "success": None,
    })


@app.post("/verify", response_class=HTMLResponse)
def verify_post(request: Request, username: str = Form(...),
                code: str = Form(...)):
    ok, msg = db.verify_student_code(username, code)
    if ok:
        return RedirectResponse("/login?success=Account+verified.+Please+log+in.", 303)
    return render("verify.html", {
        "request": request,
        "username": username.upper(),
        "error": msg,
        "success": None,
    })


@app.post("/verify/resend", response_class=HTMLResponse)
def verify_resend(request: Request, username: str = Form(...)):
    ok, info, msg = db.resend_verification_code(username)
    if not ok:
        return render("verify.html", {
            "request": request,
            "username": username.upper(),
            "error": msg,
            "success": None,
        })

    email_ok, email_err = send_verification_email(
        info["email"], info["full_name"], info["code"])

    if not email_ok:
        return render("verify.html", {
            "request": request,
            "username": username.upper(),
            "error": f"Imeshindwa kutuma email: {email_err}",
            "success": None,
        })

    return render("verify.html", {
        "request": request,
        "username": username.upper(),
        "error": None,
        "success": f"Code mpya imetumwa kwa {info['email']}",
    })
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", 303)


# ============================================================
# DASHBOARD
# ============================================================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    require_login(request)
    role = request.session["role"]
    if role == "CR":
        stats = db.get_cr_dashboard_stats()
    elif role == "LECTURER":
        t = db.get_teacher_by_user(request.session["user_id"])
        stats = db.get_teacher_stats(t["id"]) if t else {}
    else:
        stats = db.get_student_dashboard_stats(request.session.get("student_id"))
    try:
        sessions = db.get_upcoming_sessions(3, True)
    except Exception:
        sessions = []
    try:
        exams = db.get_upcoming_exams(3)
    except Exception:
        exams = []
    try:
        ann = db.get_recent_announcements(3)
    except Exception:
        ann = []
    try:
        dm = db.get_active_daily_message()
    except Exception:
        dm = None
    return render("dashboard.html", ctx(request, {
        "stats": stats, "sessions": sessions, "exams": exams,
        "announcements": ann, "daily_msg": dm,
    }))


# ============================================================
# STUDENTS
# ============================================================
@app.get("/students", response_class=HTMLResponse)
def students_list(request: Request, q: str = ""):
    require_login(request)
    students = db.search_students(q) if q else db.get_students_with_attendance()
    return render("students.html", ctx(request, {"students": students, "query": q}))


@app.get("/students/add", response_class=HTMLResponse)
def student_add_get(request: Request):
    require_login(request)
    return render("student_form.html", ctx(request, {"student": None}))


@app.post("/students/add")
def student_add_post(request: Request, full_name: str = Form(...),
                     reg_number: str = Form(""), gender: str = Form(""),
                     phone: str = Form(...), whatsapp: str = Form(""),
                     email: str = Form(""), mtaa: str = Form(""),
                     namba_nyumba: str = Form(""), parent_name: str = Form(""),
                     parent_phone: str = Form(""), notes: str = Form("")):
    require_login(request)
    db.add_student(full_name, reg_number or None, gender or None, phone,
                   whatsapp or None, email or None, None, None,
                   mtaa or None, parent_name or None, parent_phone or None, notes or None)
    return RedirectResponse("/students", 303)


@app.get("/students/{sid}/edit", response_class=HTMLResponse)
def student_edit_get(request: Request, sid: int):
    require_login(request)
    s = db.get_student(sid)
    if not s:
        raise HTTPException(404)
    return render("student_form.html", ctx(request, {"student": s}))


@app.post("/students/{sid}/edit")
def student_edit_post(request: Request, sid: int, full_name: str = Form(...),
                      reg_number: str = Form(""), gender: str = Form(""),
                      phone: str = Form(...), whatsapp: str = Form(""),
                      email: str = Form(""), mtaa: str = Form(""),
                      namba_nyumba: str = Form(""), parent_name: str = Form(""),
                      parent_phone: str = Form(""), notes: str = Form("")):
    require_login(request)
    db.update_student(sid, full_name, reg_number or None, gender or None, phone,
                      whatsapp or None, email or None, None, None,
                      mtaa or None, parent_name or None, parent_phone or None, notes or None)
    return RedirectResponse("/students", 303)


@app.post("/students/{sid}/delete")
def student_delete(request: Request, sid: int):
    require_login(request)
    db.delete_student(sid)
    return RedirectResponse("/students", 303)


@app.post("/students/{sid}/approve")
def student_approve(request: Request, sid: int):
    require_login(request)
    db.update_membership_status(sid, "approved")
    return RedirectResponse("/students", 303)


@app.post("/students/{sid}/suspend")
def student_suspend(request: Request, sid: int):
    require_login(request)
    db.update_membership_status(sid, "suspended")
    return RedirectResponse("/students", 303)


# ============================================================
# ATTENDANCE
# ============================================================
@app.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request):
    require_login(request)
    role = request.session["role"]
    if role not in ("CR", "LECTURER"):
        return render("attendance_student.html", ctx(request, {
            "my_attendance": db.get_student_own_attendance(request.session.get("student_id")),
        }))
    return render("attendance.html", ctx(request, {
        "students": db.get_approved_students(),
        "modules": db.get_all_modules(),
        "modules_for_dropdown": db.get_all_modules_for_timetable(),
        "sessions": db.get_class_sessions(10),
    }))


@app.post("/attendance/save")
async def attendance_save(request: Request):
    require_login(request)
    form = await request.form()
    date_str = form.get("date", datetime.now().strftime("%Y-%m-%d"))
    mid = form.get("module_id")
    mid = int(mid) if mid else None
    sid, _ = db.create_or_get_class_session(
        date_str, mid, form.get("type", "Regular"),
        created_by=request.session["user_id"])
    statuses = {}
    for k, v in form.items():
        if k.startswith("status_") and v in ("present", "absent", "late", "excused"):
            statuses[int(k.replace("status_", ""))] = v
    db.save_class_attendance(sid, statuses)
    return RedirectResponse("/attendance", 303)


# ============================================================
# MODULES
# ============================================================
@app.get("/modules", response_class=HTMLResponse)
def modules_list(request: Request):
    require_login(request)
    role = request.session["role"]
    if role == "CR":
        offs = db.get_all_offerings()
    elif role == "LECTURER":
        t = db.get_teacher_by_user(request.session["user_id"])
        offs = db.get_offerings_for_teacher(t["id"]) if t else []
    else:
        offs = db.get_published_offerings()
    return render("modules.html", ctx(request, {"offerings": offs}))


@app.get("/modules/create", response_class=HTMLResponse)
def module_create_get(request: Request):
    require_login(request)
    if request.session["role"] != "CR":
        raise HTTPException(403)
    return render("module_form.html", ctx(request, {
        "teachers": db.get_all_teachers(),
    }))


@app.post("/modules/create")
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


@app.get("/modules/{oid}", response_class=HTMLResponse)
def module_detail(request: Request, oid: int):
    require_login(request)
    o = db.get_offering(oid)
    if not o:
        raise HTTPException(404)
    try:
        materials = db.get_materials_for_offering(oid)
    except Exception:
        materials = []
    try:
        mat_stats = db.get_material_stats(oid)
    except Exception:
        mat_stats = {"count": 0, "size": 0}
    return render("module_detail.html", ctx(request, {
        "offering": o,
        "topics": db.get_topics(oid),
        "materials": materials,
        "mat_stats": mat_stats,
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    }))


# ============================================================
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


@app.post("/modules/{oid}/delete")
def module_delete(request: Request, oid: int):
    require_login(request)
    if request.session["role"] != "CR":
        raise HTTPException(403)
    db.delete_offering(oid)
    return RedirectResponse("/modules", 303)


@app.post("/modules/{oid}/add_topic")
def add_topic(request: Request, oid: int, title: str = Form(...),
              description: str = Form(""), duration: float = Form(0)):
    require_login(request)
    db.add_topic(oid, title, description, duration)
    return RedirectResponse(f"/modules/{oid}", 303)


@app.post("/modules/{oid}/publish")
def publish_module(request: Request, oid: int):
    require_login(request)
    db.publish_offering(oid, request.session["user_id"])
    return RedirectResponse(f"/modules/{oid}", 303)


@app.post("/topics/{tid}/add_session")
def add_session(request: Request, tid: int, date: str = Form(...),
                start: str = Form(...), end: str = Form(""),
                venue: str = Form("")):
    require_login(request)
    db.add_session(tid, date, start, end, venue)
    return RedirectResponse(request.headers.get("referer", "/modules"), 303)


@app.post("/topics/{tid}/delete")
def delete_topic(request: Request, tid: int):
    require_login(request)
    db.delete_topic(tid)
    return RedirectResponse(request.headers.get("referer", "/modules"), 303)


# ============================================================
# TIMETABLE
# ============================================================
@app.get("/timetable", response_class=HTMLResponse)
def timetable_view(request: Request):
    require_login(request)
    grouped = db.get_timetable_grouped_by_day()
    return render("timetable.html", ctx(request, {
        "grouped": grouped,
        "entries": db.get_all_timetable_entries(),
        "vapid_public_key": os.getenv("VAPID_PUBLIC_KEY", ""),
    }))
@app.get("/timetable/manage", response_class=HTMLResponse)
def timetable_manage(request: Request):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    return render("timetable_manage.html", ctx(request, {
        "entries": db.get_all_timetable_entries(),
        "modules": db.get_all_modules(),
        "modules_for_dropdown": db.get_all_modules_for_timetable(),
        "teachers": db.get_all_teachers(),
        "edit_entry": None,
    }))


@app.get("/timetable/manage/{entry_id}/edit", response_class=HTMLResponse)
def timetable_edit(request: Request, entry_id: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    entry = db.get_timetable_entry(entry_id)
    if not entry:
        raise HTTPException(404)
    return render("timetable_manage.html", ctx(request, {
        "entries": db.get_all_timetable_entries(),
        "modules": db.get_all_modules(),
        "modules_for_dropdown": db.get_all_modules_for_timetable(),
        "teachers": db.get_all_teachers(),
        "edit_entry": entry,
    }))
@app.post("/timetable/add")
def timetable_add(request: Request, day: str = Form(...),
                  start_time: str = Form(...),
                  end_time: str = Form(""),
                  session_name: str = Form(""),
                  venue: str = Form(""),
                  notes: str = Form("")):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    db.add_timetable_entry(day, start_time, end_time, None, None, venue, notes, session_name)
    return RedirectResponse("/timetable/manage", 303)


@app.post("/timetable/{entry_id}/update")
def timetable_update(request: Request, entry_id: int,
                     day: str = Form(...),
                     start_time: str = Form(...),
                     end_time: str = Form(""),
                     session_name: str = Form(""),
                     venue: str = Form(""),
                     notes: str = Form("")):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    conn = db.get_connection()
    conn.execute("PRAGMA table_info(timetable)")
    conn.execute(
        "UPDATE timetable SET day=?, start_time=?, end_time=?, venue=?, notes=?, session_name=? WHERE id=?",
        (day, start_time, end_time, venue, notes, session_name, entry_id))
    conn.commit()
    conn.close()
    return RedirectResponse("/timetable/manage", 303)
@app.post("/timetable/{entry_id}/delete")
def timetable_delete(request: Request, entry_id: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    db.delete_timetable_entry(entry_id)
    return RedirectResponse("/timetable/manage", 303)
# ============================================================
# ASSIGNMENTS
# ============================================================
@app.get("/assignments", response_class=HTMLResponse)
def assignments_list(request: Request):
    require_login(request)
    role = request.session["role"]
    if role == "LECTURER":
        t = db.get_teacher_by_user(request.session["user_id"])
        items = db.get_assignments_for_teacher(t["id"]) if t else []
        return render("assignments.html", ctx(request, {
            "assignments": items,
            "my_modules": db.get_offerings_for_teacher(t["id"]) if t else [],
        }))
    items = db.get_published_assignments()
    subs = {}
    if request.session.get("student_id"):
        for a in items:
            subs[a["id"]] = db.get_submission(a["id"], request.session["student_id"])
    return render("assignments.html", ctx(request, {
        "assignments": items, "submissions": subs,
    }))


@app.post("/assignments/create")
def assignment_create(request: Request, title: str = Form(...),
                      module_id: int = Form(...),
                      type: str = Form("individual"),
                      max_marks: int = Form(100),
                      due_date: str = Form(...),
                      instructions: str = Form("")):
    require_login(request)
    t = db.get_teacher_by_user(request.session["user_id"])
    if not t:
        raise HTTPException(403)
    db.create_assignment(module_id, t["id"], title, instructions,
                         type, max_marks, due_date)
    return RedirectResponse("/assignments", 303)


@app.post("/assignments/{aid}/publish")
def assignment_publish(request: Request, aid: int):
    require_login(request)
    db.publish_assignment(aid)
    return RedirectResponse("/assignments", 303)


@app.post("/assignments/{aid}/delete")
def assignment_delete(request: Request, aid: int):
    require_login(request)
    db.delete_assignment(aid)
    return RedirectResponse("/assignments", 303)


@app.get("/assignments/{aid}/submissions", response_class=HTMLResponse)
def assignment_submissions(request: Request, aid: int):
    require_login(request)
    a = db.get_assignment(aid)
    if not a:
        raise HTTPException(404)
    return render("submissions.html", ctx(request, {
        "assignment": a,
        "submissions": db.get_submissions_for_assignment(aid),
    }))


@app.post("/assignments/{aid}/submit")
async def assignment_submit(request: Request, aid: int):
    require_login(request)
    form = await request.form()
    text = form.get("submission_text", "")
    db.submit_assignment(aid, request.session["student_id"], text, None)
    return RedirectResponse("/assignments", 303)


@app.post("/submissions/{sub_id}/grade")
def submission_grade(request: Request, sub_id: int, score: int = Form(...),
                     feedback: str = Form("")):
    require_login(request)
    db.grade_submission(sub_id, score, feedback, request.session["user_id"])
    return RedirectResponse(request.headers.get("referer", "/assignments"), 303)


# ============================================================
# EXAMS
# ============================================================
@app.get("/exams", response_class=HTMLResponse)
def exams_list(request: Request):
    require_login(request)
    role = request.session["role"]
    items = db.get_all_exams() if role == "CR" else db.get_published_exams()
    return render("exams.html", ctx(request, {
        "exams": items,
        "modules": db.get_all_modules() if role == "CR" else [],
    }))


@app.post("/exams/create")
def exam_create(request: Request, name: str = Form(...),
                module_id: int = Form(...), type: str = Form("CAT"),
                date: str = Form(...), start_time: str = Form(...),
                end_time: str = Form(""), venue: str = Form(""),
                instructions: str = Form("")):
    require_login(request)
    db.create_exam(module_id, request.session["user_id"], name, type,
                   date, start_time, end_time, venue, instructions)
    return RedirectResponse("/exams", 303)


@app.post("/exams/{eid}/publish")
def exam_publish(request: Request, eid: int):
    require_login(request)
    db.publish_exam(eid)
    return RedirectResponse("/exams", 303)


@app.post("/exams/{eid}/cancel")
def exam_cancel(request: Request, eid: int):
    require_login(request)
    db.cancel_exam(eid)
    return RedirectResponse("/exams", 303)


@app.post("/exams/{eid}/delete")
def exam_delete(request: Request, eid: int):
    require_login(request)
    db.delete_exam(eid)
    return RedirectResponse("/exams", 303)


# ============================================================
# GROUPS
# ============================================================
@app.get("/groups", response_class=HTMLResponse)
def groups_list(request: Request):
    require_login(request)
    return render("groups.html", ctx(request, {
        "groups": db.get_all_groups(),
        "students": db.get_approved_students(),
    }))


@app.post("/groups/create")
def group_create(request: Request, name: str = Form(...),
                 description: str = Form("")):
    require_login(request)
    db.create_group(name, description, request.session["user_id"])
    return RedirectResponse("/groups", 303)


@app.post("/groups/{gid}/delete")
def group_delete(request: Request, gid: int):
    require_login(request)
    db.delete_group(gid)
    return RedirectResponse("/groups", 303)


@app.get("/groups/{gid}", response_class=HTMLResponse)
def group_detail(request: Request, gid: int):
    require_login(request)
    g = db.get_group(gid)
    if not g:
        raise HTTPException(404)
    return render("group_detail.html", ctx(request, {
        "group": g,
        "members": db.get_group_members(gid),
        "all_students": db.get_approved_students(),
    }))


@app.post("/groups/{gid}/add_members")
async def group_add_members(request: Request, gid: int):
    require_login(request)
    form = await request.form()
    ids = [int(v) for k, v in form.items() if k.startswith("member_")]
    db.set_group_members(gid, ids)
    return RedirectResponse(f"/groups/{gid}", 303)


# ============================================================
# MEETINGS
# ============================================================
@app.get("/meetings", response_class=HTMLResponse)
def meetings_list(request: Request):
    require_login(request)
    return render("meetings.html", ctx(request, {
        "meetings": db.get_all_meetings(),
        "students": db.get_approved_students(),
    }))


@app.post("/meetings/create")
def meeting_create(request: Request, title: str = Form(...),
                   type: str = Form("Regular"), date: str = Form(...),
                   start_time: str = Form(""), end_time: str = Form(""),
                   venue: str = Form(""), chairperson_id: str = Form(""),
                   secretary_id: str = Form(""), purpose: str = Form(""),
                   opening_activity: str = Form("")):
    require_login(request)
    cid = int(chairperson_id) if chairperson_id else None
    sid = int(secretary_id) if secretary_id else None
    mid = db.create_meeting(title, type, date, start_time, end_time, venue,
                            cid, sid, opening_activity, purpose)
    return RedirectResponse(f"/meetings/{mid}", 303)


@app.get("/meetings/{mid}", response_class=HTMLResponse)
def meeting_detail(request: Request, mid: int):
    require_login(request)
    m = db.get_meeting(mid)
    if not m:
        raise HTTPException(404)
    return render("meeting_detail.html", ctx(request, {
        "meeting": m,
        "agenda": db.get_agenda(mid),
        "attendance": db.get_meeting_attendance(mid),
        "all_students": db.get_approved_students(),
    }))


@app.post("/meetings/{mid}/publish")
def meeting_publish(request: Request, mid: int):
    require_login(request)
    db.publish_meeting(mid)
    return RedirectResponse(f"/meetings/{mid}", 303)


@app.post("/meetings/{mid}/delete")
def meeting_delete(request: Request, mid: int):
    require_login(request)
    db.delete_meeting(mid)
    return RedirectResponse("/meetings", 303)


@app.post("/meetings/{mid}/add_agenda")
def meeting_add_agenda(request: Request, mid: int, title: str = Form(...),
                       description: str = Form(""), discussion: str = Form(""),
                       decisions: str = Form("")):
    require_login(request)
    aid = db.add_agenda(mid, title, description)
    db.update_agenda(aid, title, description, discussion, decisions)
    return RedirectResponse(f"/meetings/{mid}", 303)


@app.post("/meetings/{mid}/save_attendance")
async def meeting_save_attendance(request: Request, mid: int):
    require_login(request)
    form = await request.form()
    ids = [int(v) for k, v in form.items() if k.startswith("att_")]
    db.set_meeting_attendance(mid, ids)
    return RedirectResponse(f"/meetings/{mid}", 303)


# ============================================================
# REPORTS
# ============================================================
@app.get("/reports", response_class=HTMLResponse)
def reports_list(request: Request):
    require_login(request)
    return render("reports.html", ctx(request, {
        "reports": db.get_all_reports(),
        "meetings": db.get_all_meetings(),
        "stats": db.get_report_stats(),
    }))


@app.post("/reports/create")
def report_create(request: Request, type: str = Form(...),
                  period_from: str = Form(""), period_to: str = Form(""),
                  meeting_id: str = Form(""), achievements: str = Form(""),
                  challenges: str = Form(""), recommendations: str = Form(""),
                  conclusion: str = Form("")):
    require_login(request)
    mid = int(meeting_id) if meeting_id else None
    db.create_report(type, period_from, period_to, mid,
                     request.session["student_id"], achievements,
                     challenges, recommendations, conclusion)
    return RedirectResponse("/reports", 303)


@app.post("/reports/{rid}/publish")
def report_publish(request: Request, rid: int):
    require_login(request)
    db.publish_report(rid)
    return RedirectResponse("/reports", 303)


@app.post("/reports/{rid}/delete")
def report_delete(request: Request, rid: int):
    require_login(request)
    db.delete_report(rid)
    return RedirectResponse("/reports", 303)


# ============================================================
# LETTERS
# ============================================================
@app.get("/letters", response_class=HTMLResponse)
def letters_list(request: Request):
    require_login(request)
    return render("letters.html", ctx(request, {
        "letters": db.get_all_letters(),
    }))


@app.post("/letters/create")
def letter_create(request: Request, reference_no: str = Form(""),
                  date: str = Form(...), type: str = Form("Official"),
                  recipient: str = Form(...), address: str = Form(""),
                  subject: str = Form(...), body: str = Form(""),
                  closing: str = Form("Yours faithfully,"),
                  sender_position: str = Form("")):
    require_login(request)
    db.create_letter(reference_no, date, type, recipient, address, subject,
                     body, closing, request.session["student_id"],
                     sender_position)
    return RedirectResponse("/letters", 303)


@app.post("/letters/{lid}/publish")
def letter_publish(request: Request, lid: int):
    require_login(request)
    db.publish_letter(lid)
    return RedirectResponse("/letters", 303)


@app.post("/letters/{lid}/delete")
def letter_delete(request: Request, lid: int):
    require_login(request)
    db.delete_letter(lid)
    return RedirectResponse("/letters", 303)


# ============================================================
# ANNOUNCEMENTS
# ============================================================
@app.get("/announcements", response_class=HTMLResponse)
def announcements_list(request: Request):
    require_login(request)
    return render("announcements.html", ctx(request, {
        "announcements": db.get_all_announcements(),
    }))


@app.post("/announcements/create")
def announcement_create(request: Request, title: str = Form(...),
                        description: str = Form(""), important: int = Form(0)):
    require_login(request)
    db.add_announcement(title, description,
                        request.session["student_id"], important)
    return RedirectResponse("/announcements", 303)


@app.post("/announcements/{aid}/delete")
def announcement_delete(request: Request, aid: int):
    require_login(request)
    db.delete_announcement(aid)
    return RedirectResponse("/announcements", 303)


# ============================================================
# DAILY MESSAGE
# ============================================================
@app.get("/daily_message", response_class=HTMLResponse)
def daily_message_page(request: Request):
    require_login(request)
    return render("daily_message.html", ctx(request, {
        "active": db.get_active_daily_message(),
        "history": db.get_daily_messages_history(20),
    }))


@app.post("/daily_message/create")
def daily_message_create(request: Request, message_text: str = Form(...),
                         publish_date: str = Form(...),
                         expires_date: str = Form("")):
    require_login(request)
    for m in db.get_daily_messages_history(100):
        if m["is_active"]:
            db.deactivate_daily_message(m["id"])
    db.create_daily_message(message_text, request.session["student_id"],
                            publish_date, expires_date)
    return RedirectResponse("/daily_message", 303)


@app.post("/daily_message/{mid}/archive")
def daily_message_archive(request: Request, mid: int):
    require_login(request)
    db.deactivate_daily_message(mid)
    return RedirectResponse("/daily_message", 303)


@app.post("/daily_message/{mid}/delete")
def daily_message_delete(request: Request, mid: int):
    require_login(request)
    db.delete_daily_message(mid)
    return RedirectResponse("/daily_message", 303)


# ============================================================
# NOTIFICATIONS
# ============================================================
@app.get("/notifications", response_class=HTMLResponse)
def notifications_page(request: Request):
    require_login(request)
    return render("notifications.html", ctx(request, {
        "notifications": db.get_user_notifications(request.session["user_id"]),
    }))


@app.post("/notifications/{nid}/read")
def notif_read(request: Request, nid: int):
    require_login(request)
    db.mark_notification_read(nid)
    return RedirectResponse("/notifications", 303)


@app.post("/notifications/read_all")
def notif_read_all(request: Request):
    require_login(request)
    db.mark_all_read(request.session["user_id"])
    return RedirectResponse("/notifications", 303)


@app.post("/notifications/{nid}/delete")
def notif_delete(request: Request, nid: int):
    require_login(request)
    db.delete_notification(nid)
    return RedirectResponse("/notifications", 303)


# ============================================================
# SETTINGS
# ============================================================
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    require_login(request)
    return render("settings.html", ctx(request))


@app.post("/settings/change_password")
def change_password_route(request: Request,
                          current_password: str = Form(...),
                          new_password: str = Form(...),
                          confirm_password: str = Form(...)):
    require_login(request)
    if new_password != confirm_password:
        return RedirectResponse(
            "/settings?error=Passwords+do+not+match", 303)
    if len(new_password) < 4:
        return RedirectResponse(
            "/settings?error=Password+must+be+at+least+4+characters", 303)
    ok, msg = auth.change_password(
        request.session["user_id"], current_password, new_password)
    if ok:
        return RedirectResponse(
            "/settings?success=Password+changed+successfully", 303)
    return RedirectResponse(
        f"/settings?error={msg.replace(' ', '+')}", 303)
@app.post("/settings/upload_logo")
async def upload_logo(request: Request):
    require_login(request)
    if request.session.get("role") not in ("CR", "LECTURER"):
        raise HTTPException(403)

    form = await request.form()
    file = form.get("logo")

    if not file or not file.filename:
        return RedirectResponse("/settings?error=No+file+selected", 303)

    if not file.filename.lower().endswith(".png"):
        return RedirectResponse("/settings?error=Only+PNG+files+allowed", 303)

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        return RedirectResponse("/settings?error=File+too+large+(max+2MB)", 303)

    b64 = base64.b64encode(content).decode()
    db.save_settings_list([("logo_base64", b64)])
    return RedirectResponse("/settings?success=Logo+updated+successfully", 303)


@app.post("/settings/remove_logo")
def remove_logo(request: Request):
    require_login(request)
    if request.session.get("role") not in ("CR", "LECTURER"):
        raise HTTPException(403)
    db.save_settings_list([("logo_base64", "")])
    return RedirectResponse("/settings?success=Logo+removed", 303)
@app.get("/verify/debug")
def verify_debug(username: str = ""):
    """TEMPORARY: show DB state for a user. Remove after debugging."""
    if not username:
        return {"error": "Add ?username=ITL4/STU/XXX"}
    conn = db.get_connection()
    row = conn.execute(
        "SELECT id, full_name, reg_number, email, is_verified, "
        "verification_code, verification_expires_at, membership_status "
        "FROM students WHERE LOWER(reg_number) = LOWER(?)",
        (username.strip().upper(),)
    ).fetchone()
    conn.close()
    if not row:
        return {"error": "Not found", "username": username}
    return {
        "id": row["id"],
        "reg_number": row["reg_number"],
        "email": row["email"],
        "is_verified": row["is_verified"],
        "verification_code": row["verification_code"],
        "verification_expires_at": row["verification_expires_at"],
        "membership_status": row["membership_status"],
        "now_utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "now_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
# ============================================================
# IT EXPERT ACADEMY
# ============================================================
@app.get("/academy/courses", response_class=HTMLResponse)
def academy_courses(request: Request):
    courses = academy.get_all_courses()
    paths = academy.get_all_paths()
    user_id = request.session.get("user_id")
    enrolled_ids = set()
    if user_id:
        for e in academy.get_user_enrollments(user_id):
            enrolled_ids.add(e["course_id"])
    return render("academy_courses.html", {
        "request": request,
        "courses": courses,
        "paths": paths,
        "enrolled_ids": enrolled_ids,
        "logged_in": user_id is not None,
        "now": datetime.now(),
    })


@app.get("/academy/dashboard", response_class=HTMLResponse)
def academy_dashboard(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    return render("academy_dashboard.html", ctx(request, {
        "enrollments": academy.get_user_enrollments(user_id),
        "stats": academy.get_user_academy_stats(user_id),
        "continue": academy.get_continue_learning(user_id),
        "all_paths": academy.get_all_paths(),
    }))


@app.get("/academy/courses/{course_id}", response_class=HTMLResponse)
def academy_course_detail(request: Request, course_id: int):
    course = academy.get_course(course_id)
    if not course:
        raise HTTPException(404)
    modules = academy.get_course_modules(course_id)
    modules_with_lessons = []
    for m in modules:
        modules_with_lessons.append({
            "module": m,
            "lessons": academy.get_lessons_for_module(m["id"]),
        })
    user_id = request.session.get("user_id")
    is_enrolled = academy.is_enrolled(user_id, course_id) if user_id else False
    return render("academy_course_detail.html", {
        "request": request,
        "course": course,
        "modules": modules_with_lessons,
        "is_enrolled": is_enrolled,
        "logged_in": user_id is not None,
        "now": datetime.now(),
    })


@app.post("/academy/enroll/{course_id}")
def academy_enroll(request: Request, course_id: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    course = academy.get_course(course_id)
    if not course:
        raise HTTPException(404)
    if course["status"] != "published":
        raise HTTPException(400, detail="Course hii bado haijawa tayari.")
    academy.enrol_user(request.session["user_id"], course_id)
    return RedirectResponse(f"/academy/courses/{course_id}", 303)
@app.get("/academy/lessons/{lesson_id}", response_class=HTMLResponse)
def academy_lesson(request: Request, lesson_id: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    lesson = academy.get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(404)
    if not academy.is_enrolled(user_id, lesson["course_id"]):
        return RedirectResponse(f"/academy/courses/{lesson['course_id']}", 303)

    # MASTERY GATING
    if not academy.is_lesson_unlocked(user_id, lesson):
        lock_info = academy.get_lesson_lock_info(user_id, lesson)
        return render("academy_lesson_locked.html", {
            "request": request,
            "lesson": lesson,
            "lock_reason": lock_info.get("reason", "Somo hili bado limefungwa."),
            "now": datetime.now(),
        })

    academy.touch_enrolment(user_id, lesson["course_id"])
    progress = academy.get_lesson_progress(user_id, lesson_id)
    next_lesson_id = academy.get_next_lesson(lesson_id)
    quiz = academy.get_assessment_for_lesson(lesson_id)
    quiz_best = None
    quiz_attempts = 0
    if quiz:
        quiz_attempts = len(academy.get_user_attempts(quiz["id"], user_id))
        quiz_best = academy.get_best_attempt(quiz["id"], user_id)

    return render("academy_lesson.html", {
        "request": request,
        "lesson": lesson,
        "progress": progress,
        "next_lesson_id": next_lesson_id,
        "quiz": quiz,
        "quiz_best": quiz_best,
        "quiz_attempts": quiz_attempts,
        "now": datetime.now(),
    })
@app.post("/academy/lessons/{lesson_id}/complete")
def academy_lesson_complete(request: Request, lesson_id: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    academy.mark_lesson_complete(user_id, lesson_id)
    next_id = academy.get_next_lesson(lesson_id)
    if next_id:
        return RedirectResponse(f"/academy/lessons/{next_id}", 303)
    lesson = academy.get_lesson(lesson_id)
    return RedirectResponse(f"/academy/courses/{lesson['course_id']}?completed=1", 303)


@app.get("/academy/debug")
def academy_debug():
    paths = academy.get_all_paths()
    courses = academy.get_all_courses()
    return {
        "paths": [dict(p) for p in paths],
        "courses": [dict(c) for c in courses],
    }


@app.get("/academy/quizzes/{assessment_id}", response_class=HTMLResponse)
def academy_quiz(request: Request, assessment_id: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    assessment = academy.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(404)
    if not academy.is_enrolled(user_id, assessment["course_id"]):
        return RedirectResponse(f"/academy/courses/{assessment['course_id']}", 303)
    attempts = academy.get_user_attempts(assessment_id, user_id)
    max_attempts = assessment["max_attempts"]
    remaining = max_attempts - len(attempts)
    if remaining <= 0:
        best = academy.get_best_attempt(assessment_id, user_id)
        return render("academy_quiz_limit.html", {
            "request": request,
            "assessment": assessment,
            "best": best,
            "attempts": attempts,
            "now": datetime.now(),
        })
    questions = academy.get_assessment_questions(assessment_id)
    return render("academy_quiz.html", {
        "request": request,
        "assessment": assessment,
        "questions": questions,
        "remaining": remaining,
        "now": datetime.now(),
    })


@app.post("/academy/quizzes/{assessment_id}/submit")
async def academy_quiz_submit(request: Request, assessment_id: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    form = await request.form()
    answers = {}
    for key, value in form.items():
        if key.startswith("q_"):
            qid = key[2:]
            answers[qid] = str(value)
    attempt_id, score, max_score, passed = academy.submit_attempt(
        assessment_id, user_id, answers)
    if attempt_id is None:
        return RedirectResponse(f"/academy/quizzes/{assessment_id}", 303)
    return RedirectResponse(f"/academy/quizzes/result/{attempt_id}", 303)


@app.get("/academy/quizzes/result/{attempt_id}", response_class=HTMLResponse)
def academy_quiz_result(request: Request, attempt_id: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    details = academy.get_attempt_details(attempt_id)
    if not details:
        raise HTTPException(404)
    if details["attempt"]["user_id"] != user_id:
        raise HTTPException(403)
    assessment = academy.get_assessment(details["attempt"]["assessment_id"])
    return render("academy_quiz_result.html", {
        "request": request,
        "assessment": assessment,
        "attempt": details["attempt"],
        "responses": details["responses"],
        "now": datetime.now(),
    })


# ============================================================
# AI TUTOR (Phase 4)
# ============================================================
@app.get("/academy/tutor", response_class=HTMLResponse)
def academy_tutor_home(request: Request, lesson_id: int = 0):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]

    # If lesson_id provided, create a new conversation linked to that lesson
    if lesson_id:
        lesson = academy.get_lesson(lesson_id)
        if lesson:
            if not academy.is_enrolled(user_id, lesson["course_id"]):
                return RedirectResponse(f"/academy/courses/{lesson['course_id']}", 303)
            conv_id = academy.create_conversation(
                user_id,
                lesson_id=lesson_id,
                course_id=lesson["course_id"],
                title=f"Help with: {lesson['title'][:40]}")
            return RedirectResponse(f"/academy/tutor/c/{conv_id}", 303)

    # Otherwise, show conversation list + new chat
    conversations = academy.get_user_conversations(user_id)
    return render("academy_tutor_list.html", {
        "request": request,
        "conversations": conversations,
        "ai_available": ai_service.is_available(),
        "now": datetime.now(),
    })


@app.post("/academy/tutor/start")
def academy_tutor_start(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    conv_id = academy.create_conversation(request.session["user_id"])
    return RedirectResponse(f"/academy/tutor/c/{conv_id}", 303)


@app.get("/academy/tutor/c/{conv_id}", response_class=HTMLResponse)
def academy_tutor_conversation(request: Request, conv_id: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]

    conv = academy.get_conversation(conv_id, user_id)
    if not conv:
        raise HTTPException(404)

    # Fetch lesson context if linked
    lesson_context = None
    if conv["lesson_id"]:
        lesson = academy.get_lesson(conv["lesson_id"])
        if lesson:
            lesson_context = {
                "lesson_title": lesson["title"],
                "course_title": lesson["course_title"],
                "lesson_content": lesson["content"] or "",
            }

    messages = academy.get_messages(conv_id)
    today_usage = academy.get_today_ai_usage(user_id)
    daily_limit = 20

    return render("academy_tutor.html", {
        "request": request,
        "conversation": conv,
        "messages": messages,
        "lesson_context": lesson_context,
        "ai_available": ai_service.is_available(),
        "today_usage": today_usage,
        "daily_limit": daily_limit,
        "remaining": max(0, daily_limit - today_usage),
        "now": datetime.now(),
    })


@app.post("/academy/tutor/c/{conv_id}/send")
async def academy_tutor_send(request: Request, conv_id: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]

    conv = academy.get_conversation(conv_id, user_id)
    if not conv:
        raise HTTPException(404)

    form = await request.form()
    user_msg = (form.get("message") or "").strip()
    language = form.get("language") or conv["language"]
    mode = form.get("mode") or conv["teaching_mode"]

    if not user_msg:
        return RedirectResponse(f"/academy/tutor/c/{conv_id}", 303)

    # Daily limit
    today_usage = academy.get_today_ai_usage(user_id)
    if today_usage >= 20:
        raise HTTPException(429, detail="Daily AI message limit reached (20/day). Try again tomorrow.")

    # Save user message
    academy.add_message(conv_id, "user", user_msg)

    # Update settings if changed
    if language != conv["language"] or mode != conv["teaching_mode"]:
        academy.update_conversation_settings(conv_id, language=language, teaching_mode=mode)

    # Build lesson context
    lesson_context = None
    if conv["lesson_id"]:
        lesson = academy.get_lesson(conv["lesson_id"])
        if lesson:
            lesson_context = {
                "lesson_title": lesson["title"],
                "course_title": lesson["course_title"],
                "lesson_content": lesson["content"] or "",
            }

    # Get history (excluding this latest user msg — it's passed separately)
    history_rows = academy.get_messages(conv_id)[:-1]
    history = [{"sender_type": r["sender_type"], "content": r["content"]} for r in history_rows]

    # Call AI
    result = ai_service.chat(mode, language, lesson_context, history, user_msg)

    if result.get("ok"):
        academy.add_message(
            conv_id, "assistant", result["text"],
            model_name=ai_service.MODEL,
            tokens_input=result["tokens_input"],
            tokens_output=result["tokens_output"])
        academy.record_ai_usage(
            user_id, conv_id,
            result["tokens_input"], result["tokens_output"],
            result["cost_usd"])
    else:
        academy.add_message(
            conv_id, "assistant",
            f"?? {result.get('error', 'AI haipatikani kwa sasa.')}")

    return RedirectResponse(f"/academy/tutor/c/{conv_id}", 303)


@app.post("/academy/tutor/c/{conv_id}/delete")
def academy_tutor_delete(request: Request, conv_id: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    academy.delete_conversation(conv_id, request.session["user_id"])
    return RedirectResponse("/academy/tutor", 303)


# ============================================================
# CODING LAB (Phase 5)
# ============================================================
@app.get("/academy/lab", response_class=HTMLResponse)
def academy_lab_home(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    projects = academy.get_user_projects(user_id)
    return render("academy_lab.html", {
        "request": request,
        "projects": projects,
        "now": datetime.now(),
    })


@app.post("/academy/lab/new")
def academy_lab_new(request: Request, language: str = Form(...),
                     title: str = Form(...)):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    if language not in ("html", "javascript", "python"):
        raise HTTPException(400)
    title = title.strip()[:80] or "Untitled"
    pid = academy.create_project(
        request.session["user_id"], title, language)
    if not pid:
        raise HTTPException(400)
    return RedirectResponse(f"/academy/lab/p/{pid}", 303)


@app.get("/academy/lab/p/{pid}", response_class=HTMLResponse)
def academy_lab_editor(request: Request, pid: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    project = academy.get_project(pid, user_id)
    if not project:
        raise HTTPException(404)
    return render("academy_lab_editor.html", {
        "request": request,
        "project": project,
        "now": datetime.now(),
    })


@app.post("/academy/lab/p/{pid}/save")
async def academy_lab_save(request: Request, pid: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    project = academy.get_project(pid, user_id)
    if not project:
        raise HTTPException(404)

    form = await request.form()
    code = form.get("code", "")
    if len(code) > 100_000:
        raise HTTPException(413, "Code too large (max 100KB)")

    academy.save_project(pid, user_id, code)

    # Return JSON for AJAX save
    from fastapi.responses import JSONResponse
    return JSONResponse({"ok": True, "saved_at": datetime.now().strftime("%H:%M:%S")})


@app.post("/academy/lab/p/{pid}/rename")
def academy_lab_rename(request: Request, pid: int, title: str = Form(...)):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    academy.rename_project(pid, request.session["user_id"], title.strip()[:80])
    return RedirectResponse(f"/academy/lab/p/{pid}", 303)


@app.post("/academy/lab/p/{pid}/delete")
def academy_lab_delete(request: Request, pid: int):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    academy.delete_project(pid, request.session["user_id"])
    return RedirectResponse("/academy/lab", 303)


# ============================================================
# CAREER LEARNING PATHS (Modification 2)
# ============================================================
@app.get("/academy/careers", response_class=HTMLResponse)
def academy_careers(request: Request):
    careers = academy.get_all_career_paths()
    user_id = request.session.get("user_id")
    progress = {}
    if user_id:
        for c in careers:
            done, total = academy.get_user_career_progress(user_id, c["id"])
            progress[c["id"]] = {"done": done, "total": total}
    return render("academy_careers.html", {
        "request": request,
        "careers": careers,
        "progress": progress,
        "logged_in": user_id is not None,
        "now": datetime.now(),
    })


@app.get("/academy/careers/{slug}", response_class=HTMLResponse)
def academy_career_detail(request: Request, slug: str):
    career = academy.get_career_path(slug)
    if not career:
        raise HTTPException(404)
    courses = academy.get_career_courses(career["id"])
    user_id = request.session.get("user_id")
    progress = None
    if user_id:
        done, total = academy.get_user_career_progress(user_id, career["id"])
        progress = {"done": done, "total": total}
    return render("academy_career_detail.html", {
        "request": request,
        "career": career,
        "courses": courses,
        "progress": progress,
        "logged_in": user_id is not None,
        "now": datetime.now(),
    })
# ============================================================
# PUSH NOTIFICATIONS ENDPOINTS
# ============================================================
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


# ============================================================
# CRON ENDPOINT (Kwa cron-job.org)
# ============================================================
# ============================================================
# LEGAL & PRIVACY
# ============================================================
@app.get("/legal/terms", response_class=HTMLResponse)
def legal_terms(request: Request):
    doc = legal.get_current_document("terms")
    if not doc:
        raise HTTPException(404, "Terms not found")
    content = legal.get_document_content("terms", doc["version"])
    if not content:
        raise HTTPException(404, "Terms content not found")
    return HTMLResponse(content)


@app.get("/legal/privacy", response_class=HTMLResponse)
def legal_privacy(request: Request):
    doc = legal.get_current_document("privacy")
    if not doc:
        raise HTTPException(404, "Privacy Policy not found")
    content = legal.get_document_content("privacy", doc["version"])
    if not content:
        raise HTTPException(404, "Privacy Policy content not found")
    return HTMLResponse(content)


@app.get("/legal/my-acceptances", response_class=HTMLResponse)
def legal_my_acceptances(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    acceptances = legal.get_user_acceptances(user_id)
    terms_current = legal.get_current_document("terms")
    privacy_current = legal.get_current_document("privacy")
    return render("legal_acceptances.html", ctx(request, {
        "acceptances": acceptances,
        "terms_current": terms_current,
        "privacy_current": privacy_current,
        "has_terms": legal.has_accepted_current(user_id, "terms"),
        "has_privacy": legal.has_accepted_current(user_id, "privacy"),
    }))


@app.get("/legal/accept-required", response_class=HTMLResponse)
def legal_accept_required(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    return render("legal_accept_required.html", ctx(request, {
        "terms_current": legal.get_current_document("terms"),
        "privacy_current": legal.get_current_document("privacy"),
    }))


@app.post("/legal/accept")
async def legal_accept_post(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", 303)
    user_id = request.session["user_id"]
    form = await request.form()

    terms_ok = form.get("accept_terms") == "on"
    privacy_ok = form.get("accept_privacy") == "on"
    if not (terms_ok and privacy_ok):
        raise HTTPException(400, detail="Both acceptances required")

    terms = legal.get_current_document("terms")
    privacy = legal.get_current_document("privacy")
    if terms:
        legal.record_acceptance(user_id, terms["id"], "terms", terms["version"], "reaccept")
    if privacy:
        legal.record_acceptance(user_id, privacy["id"], "privacy", privacy["version"], "reaccept")

    return RedirectResponse("/dashboard", 303)

# ============================================================
# PUSH NOTIFICATIONS ENDPOINTS
# ============================================================
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


# ============================================================
# CRON ENDPOINT (Kwa cron-job.org)
# ============================================================


# ============================================================
# INTERNAL: CRON TRIGGER (NO LOGIN REQUIRED)
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


# ============================================================
# PUSH: Subscribe (robust)
# ============================================================
@app.post("/api/push/subscribe")
async def push_subscribe(request: Request):
    if "user_id" not in request.session:
        return {"ok": False, "error": "Not logged in"}
    try:
        data = await request.json()
    except Exception as e:
        return {"ok": False, "error": f"Invalid JSON: {e}"}
    if not data or "endpoint" not in data or "keys" not in data:
        return {"ok": False, "error": "Missing endpoint or keys"}
    
    user_id = request.session["user_id"]
    try:
        import push_service
        push_service.save_subscription(user_id, data)
        # Verify
        from database import get_connection
        conn = get_connection()
        row = conn.execute(
            "SELECT COUNT(*) as n FROM push_subscriptions WHERE user_id = ?",
            (user_id,)).fetchone()
        conn.close()
        count = row["n"] if row else 0
        if count == 0:
            return {"ok": False, "error": "DB insert failed - 0 rows"}
        return {"ok": True, "count": count}
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()[-500:]}


# ============================================================
# PUSH: Server-side status check
# ============================================================
@app.get("/api/push/status")
def push_status(request: Request):
    if "user_id" not in request.session:
        return {"subscribed": False, "reason": "not_logged_in"}
    user_id = request.session["user_id"]
    try:
        from database import get_connection
        conn = get_connection()
        row = conn.execute(
            "SELECT COUNT(*) as n FROM push_subscriptions WHERE user_id = ?",
            (user_id,)).fetchone()
        conn.close()
        count = row["n"] if row else 0
        return {"subscribed": count > 0, "count": count}
    except Exception as e:
        return {"subscribed": False, "error": str(e)}


# ============================================================
# PUSH: Unsubscribe
# ============================================================
@app.post("/api/push/unsubscribe")
async def push_unsubscribe(request: Request):
    if "user_id" not in request.session:
        return {"ok": False, "error": "Not logged in"}
    try:
        data = await request.json()
    except Exception:
        return {"ok": False, "error": "Invalid JSON"}
    try:
        import push_service
        push_service.remove_subscription(
            request.session["user_id"], data.get("endpoint", ""))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# PUSH TEST (single clean version)
# ============================================================
@app.get("/api/push/test")
def push_test(request: Request):
    if "user_id" not in request.session:
        return {"ok": False, "error": "Not logged in"}
    
    user_id = request.session["user_id"]
    
    try:
        from database import get_connection
        conn = get_connection()
        row = conn.execute(
            "SELECT COUNT(*) as n FROM push_subscriptions WHERE user_id = ?",
            (user_id,)).fetchone()
        conn.close()
        count = row["n"] if row else 0
        
        if count == 0:
            return {
                "ok": False,
                "error": "No subscriptions",
                "user_id": user_id,
                "debug": f"DB has 0 rows for user_id={user_id}"
            }
        
        import push_service
        result = push_service.send_push(
            user_id,
            "🔔 IT Level 4 Connect",
            "Push notifications zinafanya kazi!",
            "/timetable")
        result["user_id"] = user_id
        result["db_count"] = count
        return result
    except Exception as e:
        import traceback
        return {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc()[-500:],
            "user_id": user_id
        }


# ============================================================
# LECTURER MANAGEMENT ROUTES (CR only)
# ============================================================
@app.get("/lecturers/manage", response_class=HTMLResponse)
def lecturers_manage(request: Request):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    return render("lecturers_manage.html", ctx(request, {
        "teachers": db.get_all_teachers(),
        "edit_teacher": None,
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    }))


@app.post("/lecturers/add")
def lecturer_add(request: Request,
                 full_name: str = Form(...),
                 phone: str = Form(""),
                 email: str = Form(""),
                 notes: str = Form("")):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    if not full_name.strip():
        return RedirectResponse("/lecturers/manage?error=Jina+lazima", 303)
    db.add_teacher(full_name.strip(), phone.strip(), email.strip(), notes.strip())
    return RedirectResponse("/lecturers/manage?success=Lecturer+ameongezwa", 303)


@app.get("/lecturers/{tid}/edit", response_class=HTMLResponse)
def lecturer_edit(request: Request, tid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    teacher = db.get_teacher(tid)
    if not teacher:
        raise HTTPException(404)
    return render("lecturers_manage.html", ctx(request, {
        "teachers": db.get_all_teachers(),
        "edit_teacher": teacher,
        "error": None,
        "success": None,
    }))


@app.post("/lecturers/{tid}/update")
def lecturer_update(request: Request, tid: int,
                    full_name: str = Form(...),
                    phone: str = Form(""),
                    email: str = Form(""),
                    notes: str = Form("")):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    db.update_teacher(tid, full_name.strip(), phone.strip(), email.strip(), notes.strip())
    return RedirectResponse("/lecturers/manage?success=Imebadilishwa", 303)


@app.post("/lecturers/{tid}/delete")
def lecturer_delete(request: Request, tid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    ok, msg = db.delete_teacher(tid)
    if not ok:
        from urllib.parse import quote
        return RedirectResponse(f"/lecturers/manage?error={quote(msg)}", 303)
    return RedirectResponse("/lecturers/manage?success=Imefutwa", 303)


# ============================================================
# SESSION-BASED ATTENDANCE ROUTES
# ============================================================
@app.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request):
    require_login(request)
    role = request.session["role"]
    
    if role not in ("CR", "LECTURER"):
        return render("attendance_student.html", ctx(request, {
            "my_attendance": db.get_student_session_attendance(request.session.get("student_id")),
        }))
    
    todays = db.get_todays_timetable_with_status(request.session["user_id"])
    recent = db.get_class_sessions(20)
    return render("attendance.html", ctx(request, {
        "todays_sessions": todays,
        "recent_sessions": recent,
        "today_label": datetime.now().strftime("%A, %d %B %Y"),
    }))


@app.post("/attendance/start/{timetable_id}")
def attendance_start(request: Request, timetable_id: int):
    require_login(request)
    if request.session["role"] not in ("CR", "LECTURER"):
        raise HTTPException(403)
    today = datetime.now().strftime("%Y-%m-%d")
    session_id, status, created = db.get_or_create_session_from_timetable(
        timetable_id, today, request.session["user_id"])
    if not session_id:
        raise HTTPException(404)
    return RedirectResponse(f"/attendance/session/{session_id}", 303)


@app.get("/attendance/session/{session_id}", response_class=HTMLResponse)
def attendance_session(request: Request, session_id: int):
    require_login(request)
    if request.session["role"] not in ("CR", "LECTURER"):
        raise HTTPException(403)
    data = db.get_session_with_attendance(session_id)
    if not data:
        raise HTTPException(404)
    return render("attendance_mark.html", ctx(request, {
        "session": data["session"],
        "attendance_map": {a["student_id"]: a["status"] for a in data["attendance"]},
        "students": db.get_approved_students(),
    }))


@app.post("/attendance/session/{session_id}/save")
async def attendance_session_save(request: Request, session_id: int):
    require_login(request)
    if request.session["role"] not in ("CR", "LECTURER"):
        raise HTTPException(403)
    form = await request.form()
    statuses = {}
    for k, v in form.items():
        if k.startswith("status_") and v in ("present", "absent", "late", "excused"):
            try:
                statuses[int(k.replace("status_", ""))] = v
            except ValueError:
                pass
    db.save_class_attendance(session_id, statuses)
    
    new_status = form.get("session_status", "conducted")
    if new_status in ("scheduled", "conducted", "cancelled"):
        db.update_session_status(session_id, new_status)
    
    return RedirectResponse(f"/attendance/session/{session_id}?saved=1", 303)


# ============================================================
# CR MANAGEMENT ROUTES (CR only)
# ============================================================
@app.get("/cr-management", response_class=HTMLResponse)
def cr_management_get(request: Request):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    crs = []
    try:
        crs = db.get_all_crs_with_student_info()
    except Exception as _e:
        print(f"⚠️ get_all_crs_with_student_info failed: {_e}, falling back")
        crs = db.get_all_crs()
    try:
        eligible = db.get_students_eligible_for_cr()
    except Exception as _e:
        print(f"⚠️ get_students_eligible_for_cr failed: {_e}")
        eligible = []
    return render("cr_management.html", ctx(request, {
        "crs": crs,
        "eligible_students": eligible,
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    }))


@app.post("/cr-management/create")
def cr_management_create(request: Request,
                          username: str = Form(...),
                          password: str = Form(...),
                          full_name: str = Form(...),
                          phone: str = Form(...),
                          email: str = Form("")):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    ok, msg = db.create_cr_account(username, password, full_name, phone, email)
    from urllib.parse import quote
    key = "success" if ok else "error"
    return RedirectResponse(f"/cr-management?{key}={quote(msg)}", 303)


@app.post("/cr-management/{uid}/delete")
def cr_management_delete(request: Request, uid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    ok, msg = db.delete_cr_user(uid)
    from urllib.parse import quote
    key = "success" if ok else "error"
    return RedirectResponse(f"/cr-management?{key}={quote(msg)}", 303)


# ============================================================
# CR PROMOTION ROUTES
# ============================================================
@app.post("/cr-management/promote/{student_id}")
def cr_promote(request: Request, student_id: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    ok, msg = db.promote_student_to_cr(student_id)
    from urllib.parse import quote
    key = "success" if ok else "error"
    return RedirectResponse(f"/cr-management?{key}={quote(msg)}", 303)


@app.post("/cr-management/{uid}/demote")
def cr_demote(request: Request, uid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    ok, msg = db.demote_cr_to_student(uid)
    from urllib.parse import quote
    key = "success" if ok else "error"
    return RedirectResponse(f"/cr-management?{key}={quote(msg)}", 303)


@app.post("/cr-management/{uid}/delete-v2")
def cr_delete_v2(request: Request, uid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    ok, msg = db.delete_cr_with_safety(uid)
    from urllib.parse import quote
    key = "success" if ok else "error"
    return RedirectResponse(f"/cr-management?{key}={quote(msg)}", 303)


# ============================================================
# TIMETABLE POSTPONE/CANCEL ROUTES
# ============================================================


# ============================================================
# TIMETABLE POSTPONE/CANCEL ROUTES
# ============================================================
@app.post("/timetable/{entry_id}/postpone")
def timetable_postpone(request: Request, entry_id: int,
                        postponed_to: str = Form(...),
                        reason: str = Form("")):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    db.postpone_timetable_entry(entry_id, postponed_to, reason)
    return RedirectResponse("/timetable/manage?success=Ratiba+imeahirishwa", 303)


@app.post("/timetable/{entry_id}/restore")
def timetable_restore(request: Request, entry_id: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    db.restore_timetable_entry(entry_id)
    return RedirectResponse("/timetable/manage?success=Ratiba+imerudishwa", 303)


@app.post("/timetable/{entry_id}/cancel")
def timetable_cancel(request: Request, entry_id: int,
                      reason: str = Form("")):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    db.cancel_timetable_entry(entry_id, reason)
    return RedirectResponse("/timetable/manage?success=Kipindi+kimefutwa", 303)


@app.post("/modules/cleanup-samples")
def modules_cleanup_samples(request: Request):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    try:
        deleted, kept = db.cleanup_unused_seed_modules()
        from urllib.parse import quote
        msg = f"Sample modules zimefutwa: {deleted} (zilizotumika: {kept})"
        return RedirectResponse(f"/modules?success={quote(msg)}", 303)
    except Exception as e:
        from urllib.parse import quote
        return RedirectResponse(f"/modules?error={quote(str(e))}", 303)


# ============================================================
# ATTENDANCE SUMMARY VIEW (with names)
# ============================================================
@app.get("/attendance/session/{session_id}/view", response_class=HTMLResponse)
def attendance_view_summary(request: Request, session_id: int):
    require_login(request)
    if request.session.get("role") not in ("CR", "LECTURER"):
        raise HTTPException(403)
    data = db.get_session_attendance_summary(session_id)
    if not data:
        raise HTTPException(404)
    return render("attendance_summary.html", ctx(request, {
        "session": data["session"],
        "present": data["present"],
        "absent": data["absent"],
        "late": data["late"],
        "excused": data["excused"],
        "total": data["total"],
        "present_count": len(data["present"]) + len(data["late"]),
        "absent_count": len(data["absent"]),
        "late_count": len(data["late"]),
        "excused_count": len(data["excused"]),
    }))


# ============================================================
# MODULE NOTES + TOPIC STATUS
# ============================================================
@app.post("/topics/{tid}/update_notes")
def topic_update_notes(request: Request, tid: int, description: str = Form("")):
    require_login(request)
    if request.session.get("role") not in ("CR", "LECTURER"):
        raise HTTPException(403)
    try:
        conn = db.get_connection()
        conn.execute("UPDATE topics SET description = ? WHERE id = ?",
                     (description, tid))
        conn.commit()
        conn.close()
        return RedirectResponse(
            request.headers.get("referer", "/modules"), 303)
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.post("/topics/{tid}/toggle_status")
def topic_toggle_status(request: Request, tid: int):
    require_login(request)
    if request.session.get("role") not in ("CR", "LECTURER"):
        raise HTTPException(403)
    try:
        conn = db.get_connection()
        row = conn.execute("SELECT status FROM topics WHERE id = ?",
                           (tid,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(404)
        current = row["status"] or "not_started"
        if current == "not_started":
            new_status = "in_progress"
        elif current == "in_progress":
            new_status = "completed"
        else:
            new_status = "not_started"
        conn.execute("UPDATE topics SET status = ? WHERE id = ?",
                     (new_status, tid))
        conn.commit()
        conn.close()
        return RedirectResponse(
            request.headers.get("referer", "/modules"), 303)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


# ============================================================
# MATERIALS UPLOAD/DOWNLOAD/DELETE
# ============================================================
@app.post("/modules/{oid}/materials/upload")
async def material_upload(
    request: Request, oid: int,
    title: str = Form(...),
    description: str = Form(""),
    topic_id: str = Form(""),
    file: UploadFile = File(...)
):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    
    o = db.get_offering(oid)
    if not o:
        raise HTTPException(404)
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        return RedirectResponse(f"/modules/{oid}?error=File+too+large+(max+10MB)#notes", 303)
    
    import base64 as _b64
    b64_content = _b64.b64encode(content).decode()
    tid = int(topic_id) if topic_id else None
    
    try:
        db.add_material(oid, tid, title.strip(), description.strip(),
                        file.filename or "file", file.content_type or "application/octet-stream",
                        b64_content, request.session["user_id"])
    except Exception as e:
        return RedirectResponse(f"/modules/{oid}?error={str(e)}#notes", 303)
    
    return RedirectResponse(f"/modules/{oid}?success=Material+uploaded#notes", 303)


@app.get("/materials/{mid}/download")
def material_download(request: Request, mid: int):
    require_login(request)
    m = db.get_material(mid)
    if not m:
        raise HTTPException(404)
    
    import base64 as _b64
    try:
        content = _b64.b64decode(m["file_content"] or "")
    except Exception:
        raise HTTPException(500, "File corrupted")
    
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type=m["file_type"] or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{m["file_name"]}"'}
    )


@app.post("/materials/{mid}/delete")
def material_delete(request: Request, mid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    m = db.get_material(mid)
    if m:
        db.delete_material(mid)
        return RedirectResponse(f"/modules/{m['offering_id']}?success=Material+deleted#notes", 303)
    return RedirectResponse("/modules", 303)


# ============================================================
# AUTO-SUBSCRIBE: Called after login to auto-enable push
# ============================================================
@app.post("/api/push/auto-subscribe")
async def push_auto_subscribe(request: Request):
    """Auto-save subscription (browser already subscribed)."""
    if "user_id" not in request.session:
        return {"ok": False, "error": "Not logged in"}
    try:
        data = await request.json()
    except Exception:
        return {"ok": False, "error": "Invalid JSON"}
    if not data or "endpoint" not in data or "keys" not in data:
        return {"ok": False, "error": "Missing endpoint or keys"}
    try:
        import push_service
        push_service.save_subscription(request.session["user_id"], data)
        from database import get_connection
        conn = get_connection()
        row = conn.execute(
            "SELECT COUNT(*) as n FROM push_subscriptions WHERE user_id = ?",
            (request.session["user_id"],)).fetchone()
        conn.close()
        count = row["n"] if row else 0
        return {"ok": True, "count": count, "auto": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# DIAGNOSTIC: Check DB state (temporary - remove later)
# ============================================================
@app.get("/admin/db-check")
def admin_db_check(secret: str = ""):
    if secret != os.getenv("CRON_SECRET", ""):
        raise HTTPException(403)
    
    from datetime import datetime, timezone, timedelta
    EAT = timezone(timedelta(hours=3))
    now = datetime.now(EAT)
    
    result = {
        "eat_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "checks": {},
        "errors": [],
    }
    
    try:
        conn = db.get_connection()
        
        # 1. Push subscriptions
        try:
            row = conn.execute("SELECT COUNT(*) as n FROM push_subscriptions").fetchone()
            result["checks"]["push_subscriptions_total"] = row["n"] if row else 0
            rows = conn.execute(
                "SELECT user_id, LEFT(endpoint, 50) as ep, created_at "
                "FROM push_subscriptions ORDER BY id DESC LIMIT 5").fetchall()
            result["checks"]["push_subscriptions_list"] = [
                {"user_id": r["user_id"], "endpoint": r["ep"], "created_at": r["created_at"]}
                for r in rows
            ]
        except Exception as e:
            result["errors"].append(f"push_subscriptions: {e}")
        
        # 2. Daily messages
        try:
            row = conn.execute("SELECT COUNT(*) as n FROM daily_messages").fetchone()
            result["checks"]["daily_messages_total"] = row["n"] if row else 0
            rows = conn.execute(
                "SELECT id, LEFT(message_text, 40) as msg, author_id, "
                "publish_date, expires_date, is_active, created_at "
                "FROM daily_messages ORDER BY id DESC LIMIT 5").fetchall()
            result["checks"]["daily_messages_list"] = [
                {"id": r["id"], "msg": r["msg"], "author_id": r["author_id"],
                 "publish_date": r["publish_date"], "expires_date": r["expires_date"],
                 "is_active": r["is_active"], "created_at": r["created_at"]}
                for r in rows
            ]
        except Exception as e:
            result["errors"].append(f"daily_messages: {e}")
        
        # 3. Notifications
        try:
            row = conn.execute("SELECT COUNT(*) as n FROM notifications").fetchone()
            result["checks"]["notifications_total"] = row["n"] if row else 0
        except Exception as e:
            result["errors"].append(f"notifications: {e}")
        
        # 4. Timetable status
        try:
            rows = conn.execute(
                "SELECT id, session_name, day, start_time, status FROM timetable "
                "WHERE status IS NOT NULL ORDER BY id DESC LIMIT 5").fetchall()
            result["checks"]["timetable_status"] = [
                {"id": r["id"], "name": r["session_name"], "day": r["day"],
                 "start": r["start_time"], "status": r["status"]}
                for r in rows
            ]
        except Exception as e:
            result["errors"].append(f"timetable: {e}")
        
        conn.close()
    except Exception as e:
        result["errors"].append(f"connection: {e}")
    
    return result


@app.get("/admin/db-force-init")
def admin_db_force_init(secret: str = ""):
    """Force-create push tables."""
    if secret != os.getenv("CRON_SECRET", ""):
        raise HTTPException(403)
    try:
        import push_service
        push_service.init_push_table()
        return {"ok": True, "message": "Push tables force-created"}
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()[-500:]}


@app.get("/admin/db-test-subscribe")
def admin_db_test_subscribe(secret: str = "", user_id: int = 1):
    """Insert fake subscription to test DB write."""
    if secret != os.getenv("CRON_SECRET", ""):
        raise HTTPException(403)
    try:
        conn = db.get_connection()
        # Insert test
        conn.execute(
            "INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth) "
            "VALUES (?, ?, ?, ?)",
            (user_id, "test-endpoint-" + str(user_id) + "-" + str(__import__('time').time()),
             "test-p256dh", "test-auth"))
        conn.commit()
        # Verify
        row = conn.execute(
            "SELECT COUNT(*) as n FROM push_subscriptions WHERE user_id = ?",
            (user_id,)).fetchone()
        count = row["n"] if row else 0
        conn.close()
        return {"ok": True, "user_id": user_id, "count_after_insert": count}
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()[-500:]}