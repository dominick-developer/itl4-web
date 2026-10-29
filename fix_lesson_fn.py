# fix_lesson_fn.py — Fix academy_lesson function indentation
from pathlib import Path

p = Path("main.py")
lines = p.read_text(encoding="utf-8").split("\n")

# Find start of academy_lesson function
start = None
for i, line in enumerate(lines):
    if line.startswith('@app.get("/academy/lessons/{lesson_id}"'):
        start = i
        break

if start is None:
    print("ERROR: function not found")
    exit(1)

# Find end (next @app. decorator)
end = len(lines)
for i in range(start + 1, len(lines)):
    if lines[i].startswith("@app.") or lines[i].startswith("# ==="):
        end = i
        break

print(f"Found function: lines {start+1} to {end}")
print(f"Old content (first 3 lines):")
for l in lines[start:start+3]:
    print(f"  {l!r}")

# Correct function
correct = [
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
    '',
    '    academy.touch_enrolment(user_id, lesson["course_id"])',
    '    progress = academy.get_lesson_progress(user_id, lesson_id)',
    '    next_lesson_id = academy.get_next_lesson(lesson_id)',
    '',
    '    quiz = academy.get_assessment_for_lesson(lesson_id)',
    '    quiz_best = None',
    '    quiz_attempts = 0',
    '    if quiz:',
    '        quiz_attempts = len(academy.get_user_attempts(quiz["id"], user_id))',
    '        quiz_best = academy.get_best_attempt(quiz["id"], user_id)',
    '',
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
]

new_lines = lines[:start] + correct + lines[end:]
p.write_text("\n".join(new_lines), encoding="utf-8")
print(f"\nFIXED! Replaced {end - start} lines with {len(correct)} correct lines")
print("Now run: python -c \"import main\"")
