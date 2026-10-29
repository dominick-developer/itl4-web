# ✅ IWE HIVI
import os
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
from pathlib import Path
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
import base64

import database as db
import auth
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

@app.on_event("startup")
def startup():
    # 1. Init database (migrations za columns mpya zipo ndani ya init_database)
    db.init_database()
    print("✅ Database ready")

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
        print("✅ CR 'cr' created with password 123456")
    else:
        # Update password kuwa 123456 kila app inapowaka
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE username = 'cr'",
            (pwd_hash, salt))
        conn.commit()
        print("✅ CR 'cr' password reset to 123456")

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
                role: str = Form("STUDENT")):
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
    ok, module_id, msg = db.add_module(name, code, description)
    if not ok:
        raise HTTPException(500, detail=msg)
    tid = int(teacher_id) if teacher_id else None
    db.create_offering(module_id, "IT Level 4", academic_year, semester, tid)
    return RedirectResponse("/modules", 303)


@app.get("/modules/{oid}", response_class=HTMLResponse)
def module_detail(request: Request, oid: int):
    require_login(request)
    o = db.get_offering(oid)
    if not o:
        raise HTTPException(404)
    return render("module_detail.html", ctx(request, {
        "offering": o, "topics": db.get_topics(oid),
    }))


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
def timetable_page(request: Request, q: str = ""):
    require_login(request)
    only_pub = request.session["role"] == "STUDENT"
    sessions = db.get_timetable_sessions(search=q, only_published=only_pub)
    return render("timetable.html", ctx(request, {
        "sessions": sessions, "query": q,
    }))


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