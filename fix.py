# fix.py — Rebuild entire academy section in main.py
from pathlib import Path
import ast

p = Path("main.py")
content = p.read_text(encoding="utf-8")
lines = content.split("\n")

print(f"main.py: {len(lines)} lines total")
print()

# Show current broken state
print("=== CURRENT STATE (lines 1085-1200) ===")
for i in range(1084, min(1200, len(lines))):
    print(f"{i+1:5d}: {lines[i]}")
print("=" * 50)
print()

# Find academy section start
start = None
for i, line in enumerate(lines):
    if line.strip() == "# IT EXPERT ACADEMY":
        s = i
        while s > 0 and (lines[s-1].strip().startswith("#") or lines[s-1].strip() == ""):
            s -= 1
        start = s
        break

if start is None:
    for i, line in enumerate(lines):
        if '@app.get("/academy/courses"' in line:
            s = i
            while s > 0 and (lines[s-1].strip().startswith("#") or lines[s-1].strip() == ""):
                s -= 1
            start = s
            break

if start is None:
    print("ERROR: Cannot find academy section in main.py")
    print("Fix manually around line 1090.")
    exit(1)

print(f"Will keep lines 1-{start}, rebuild {start+1}-{len(lines)}")
print()

# Build clean academy section (list of strings)
c = [
    "# ============================================================",
    "# IT EXPERT ACADEMY",
    "# ============================================================",
    '@app.get("/academy/courses", response_class=HTMLResponse)',
    'def academy_courses(request: Request):',
    '    courses = academy.get_all_courses()',
    '    paths = academy.get_all_paths()',
    '    user_id = request.session.get("user_id")',
    '    enrolled_ids = set()',
    '    if user_id:',
    '        for e in academy.get_user_enrollments(user_id):',
    '            enrolled_ids.add(e["course_id"])',
    '    return render("academy_courses.html", {',
    '        "request": request,',
    '        "courses": courses,',
    '        "paths": paths,',
    '        "enrolled_ids": enrolled_ids,',
    '        "logged_in": user_id is not None,',
    '        "now": datetime.now(),',
    '    })',
    '',
    '',
    '@app.get("/academy/dashboard", response_class=HTMLResponse)',
    'def academy_dashboard(request: Request):',
    '    if "user_id" not in request.session:',
    '        return RedirectResponse("/login", 303)',
    '    user_id = request.session["user_id"]',
    '    return render("academy_dashboard.html", ctx(request, {',
    '        "enrollments": academy.get_user_enrollments(user_id),',
    '        "stats": academy.get_user_academy_stats(user_id),',
    '        "continue": academy.get_continue_learning(user_id),',
    '        "all_paths": academy.get_all_paths(),',
    '    }))',
    '',
    '',
    '@app.get("/academy/courses/{course_id}", response_class=HTMLResponse)',
    'def academy_course_detail(request: Request, course_id: int):',
    '    course = academy.get_course(course_id)',
    '    if not course:',
    '        raise HTTPException(404)',
    '    modules = academy.get_course_modules(course_id)',
    '    modules_with_lessons = []',
    '    for m in modules:',
    '        modules_with_lessons.append({',
    '            "module": m,',
    '            "lessons": academy.get_lessons_for_module(m["id"]),',
    '        })',
    '    user_id = request.session.get("user_id")',
    '    is_enrolled = academy.is_enrolled(user_id, course_id) if user_id else False',
    '    return render("academy_course_detail.html", {',
    '        "request": request,',
    '        "course": course,',
    '        "modules": modules_with_lessons,',
    '        "is_enrolled": is_enrolled,',
    '        "logged_in": user_id is not None,',
    '        "now": datetime.now(),',
    '    })',
    '',
    '',
    '@app.post("/academy/enroll/{course_id}")',
    'def academy_enroll(request: Request, course_id: int):',
    '    if "user_id" not in request.session:',
    '        return RedirectResponse("/login", 303)',
    '    academy.enrol_user(request.session["user_id"], course_id)',
    '    return RedirectResponse(f"/academy/courses/{course_id}", 303)',
    '',
    '',
    '@app.get("/academy/lessons/{lesson_id}", response_class=HTMLResponse)',
    'def academy_lesson(request: Request, lesson_id: int):',
    '    if "user_id" not in request.session:',
    '        return RedirectResponse("/login", 303)',
    '    user_id = request.session["user_id"]',
    '    lesson = academy.get_lesson(lesson_id)',
    '    if not lesson:',
    '        raise HTTPException(404)',
    '    if not academy.is_enrolled(user_id, lesson["course_id"]):',
    '        return RedirectResponse(f"/academy/courses/{lesson[\'course_id\']}", 303)',
    '    academy.touch_enrolment(user_id, lesson["course_id"])',
    '    progress = academy.get_lesson_progress(user_id, lesson_id)',
    '    next_lesson_id = academy.get_next_lesson(lesson_id)',
    '    quiz = academy.get_assessment_for_lesson(lesson_id)',
    '    quiz_best = None',
    '    quiz_attempts = 0',
    '    if quiz:',
    '        quiz_attempts = len(academy.get_user_attempts(quiz["id"], user_id))',
    '        quiz_best = academy.get_best_attempt(quiz["id"], user_id)',
    '    return render("academy_lesson.html", {',
    '        "request": request,',
    '        "lesson": lesson,',
    '        "progress": progress,',
    '        "next_lesson_id": next_lesson_id,',
    '        "quiz": quiz,',
    '        "quiz_best": quiz_best,',
    '        "quiz_attempts": quiz_attempts,',
    '        "now": datetime.now(),',
    '    })',
    '',
    '',
    '@app.post("/academy/lessons/{lesson_id}/complete")',
    'def academy_lesson_complete(request: Request, lesson_id: int):',
    '    if "user_id" not in request.session:',
    '        return RedirectResponse("/login", 303)',
    '    user_id = request.session["user_id"]',
    '    academy.mark_lesson_complete(user_id, lesson_id)',
    '    next_id = academy.get_next_lesson(lesson_id)',
    '    if next_id:',
    '        return RedirectResponse(f"/academy/lessons/{next_id}", 303)',
    '    lesson = academy.get_lesson(lesson_id)',
    '    return RedirectResponse(f"/academy/courses/{lesson[\'course_id\']}?completed=1", 303)',
    '',
    '',
    '@app.get("/academy/debug")',
    'def academy_debug():',
    '    paths = academy.get_all_paths()',
    '    courses = academy.get_all_courses()',
    '    return {',
    '        "paths": [dict(p) for p in paths],',
    '        "courses": [dict(c) for c in courses],',
    '    }',
    '',
    '',
    '@app.get("/academy/quizzes/{assessment_id}", response_class=HTMLResponse)',
    'def academy_quiz(request: Request, assessment_id: int):',
    '    if "user_id" not in request.session:',
    '        return RedirectResponse("/login", 303)',
    '    user_id = request.session["user_id"]',
    '    assessment = academy.get_assessment(assessment_id)',
    '    if not assessment:',
    '        raise HTTPException(404)',
    '    if not academy.is_enrolled(user_id, assessment["course_id"]):',
    '        return RedirectResponse(f"/academy/courses/{assessment[\'course_id\']}", 303)',
    '    attempts = academy.get_user_attempts(assessment_id, user_id)',
    '    max_attempts = assessment["max_attempts"]',
    '    remaining = max_attempts - len(attempts)',
    '    if remaining <= 0:',
    '        best = academy.get_best_attempt(assessment_id, user_id)',
    '        return render("academy_quiz_limit.html", {',
    '            "request": request,',
    '            "assessment": assessment,',
    '            "best": best,',
    '            "attempts": attempts,',
    '            "now": datetime.now(),',
    '        })',
    '    questions = academy.get_assessment_questions(assessment_id)',
    '    return render("academy_quiz.html", {',
    '        "request": request,',
    '        "assessment": assessment,',
    '        "questions": questions,',
    '        "remaining": remaining,',
    '        "now": datetime.now(),',
    '    })',
    '',
    '',
    '@app.post("/academy/quizzes/{assessment_id}/submit")',
    'async def academy_quiz_submit(request: Request, assessment_id: int):',
    '    if "user_id" not in request.session:',
    '        return RedirectResponse("/login", 303)',
    '    user_id = request.session["user_id"]',
    '    form = await request.form()',
    '    answers = {}',
    '    for key, value in form.items():',
    '        if key.startswith("q_"):',
    '            qid = key[2:]',
    '            answers[qid] = str(value)',
    '    attempt_id, score, max_score, passed = academy.submit_attempt(',
    '        assessment_id, user_id, answers)',
    '    if attempt_id is None:',
    '        return RedirectResponse(f"/academy/quizzes/{assessment_id}", 303)',
    '    return RedirectResponse(f"/academy/quizzes/result/{attempt_id}", 303)',
    '',
    '',
    '@app.get("/academy/quizzes/result/{attempt_id}", response_class=HTMLResponse)',
    'def academy_quiz_result(request: Request, attempt_id: int):',
    '    if "user_id" not in request.session:',
    '        return RedirectResponse("/login", 303)',
    '    user_id = request.session["user_id"]',
    '    details = academy.get_attempt_details(attempt_id)',
    '    if not details:',
    '        raise HTTPException(404)',
    '    if details["attempt"]["user_id"] != user_id:',
    '        raise HTTPException(403)',
    '    assessment = academy.get_assessment(details["attempt"]["assessment_id"])',
    '    return render("academy_quiz_result.html", {',
    '        "request": request,',
    '        "assessment": assessment,',
    '        "attempt": details["attempt"],',
    '        "responses": details["responses"],',
    '        "now": datetime.now(),',
    '    })',
]

# Splice
new_lines = lines[:start] + c
new_content = "\n".join(new_lines)

# Save
p.write_text(new_content, encoding="utf-8")
print(f"✅ WROTE {len(new_lines)} lines to main.py")
print()

# Syntax check
try:
    ast.parse(new_content)
    print("✅ Syntax check PASSED")
    print()
    print("NEXT:")
    print("  git add main.py")
    print('  git commit -m "Rebuild academy section"')
    print("  git push")
except SyntaxError as e:
    print(f"❌ Syntax error at line {e.lineno}: {e.msg}")
    print(f"   Text: {e.text}")