# clean_main.py — Rekebisha academy_lesson function
from pathlib import Path

p = Path("main.py")
lines = p.read_text(encoding="utf-8").split("\n")

# Tafuta @app.get("/academy/lessons/{lesson_id}" au def academy_lesson
start = None
for i, line in enumerate(lines):
    if 'app.get("/academy/lessons/{lesson_id}"' in line:
        start = i
        break
    if "def academy_lesson(" in line and start is None:
        # Rudi nyuma kutafuta @app decorator
        for j in range(i - 1, max(0, i - 5), -1):
            if lines[j].strip().startswith("@app."):
                start = j
                break

if start is None:
    print("KOSA: academy_lesson function haipo")
    exit(1)

# Tafuta mwisho: @app inayofuata au def nyingine ya academy_
end = len(lines)
for i in range(start + 1, len(lines)):
    stripped = lines[i].strip()
    if stripped.startswith("@app."):
        end = i
        break

print(f"Function ipo: mistari {start+1} hadi {end}")
print(f"Mstari wa kwanza: {lines[start]!r}")
print()

# Function mpya (sahihi)
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
]

new_lines = lines[:start] + correct + lines[end:]
p.write_text("\n".join(new_lines), encoding="utf-8")
print(f"IMEREKEBISHWA: {end - start} mistari -> {len(correct)} mistari sahihi")

# Syntax check
import ast
try:
    ast.parse("\n".join(new_lines))
    print("main.py: SYNTAX OK")
except SyntaxError as e:
    print(f"main.py: KOSA line {e.lineno}: {e.msg}")