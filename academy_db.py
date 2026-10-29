# academy_db.py â€” IT Expert Academy data layer
import sqlite3
from datetime import datetime
from database import get_connection

def init_academy():
    """Create Academy tables and seed initial content (idempotent)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        passing_score INTEGER DEFAULT 70,
        max_attempts INTEGER DEFAULT 3,
        status TEXT DEFAULT 'published',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessment_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER NOT NULL,
        question_type TEXT NOT NULL,
        question_text TEXT NOT NULL,
        options_json TEXT,
        correct_answer TEXT NOT NULL,
        explanation TEXT,
        points INTEGER DEFAULT 10,
        sequence_number INTEGER DEFAULT 1,
        FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessment_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        attempt_number INTEGER DEFAULT 1,
        score INTEGER DEFAULT 0,
        max_score INTEGER DEFAULT 0,
        passed INTEGER DEFAULT 0,
        submitted_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessment_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        selected_answer TEXT,
        is_correct INTEGER DEFAULT 0,
        points_awarded INTEGER DEFAULT 0,
        FOREIGN KEY (attempt_id) REFERENCES assessment_attempts(id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES assessment_questions(id) ON DELETE CASCADE
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS learning_paths (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        icon TEXT,
        color TEXT,
        target_level TEXT,
        sequence_number INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS academy_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learning_path_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        difficulty_level TEXT,
        language TEXT DEFAULT 'sw',
        estimated_duration_min INTEGER DEFAULT 0,
        status TEXT DEFAULT 'published',
        version INTEGER DEFAULT 1,
        created_by INTEGER,
        published_at TEXT DEFAULT (datetime('now','localtime')),
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (learning_path_id) REFERENCES learning_paths(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS course_modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        sequence_number INTEGER DEFAULT 1,
        FOREIGN KEY (course_id) REFERENCES academy_courses(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        lesson_type TEXT DEFAULT 'text',
        sequence_number INTEGER DEFAULT 1,
        estimated_duration_min INTEGER DEFAULT 15,
        status TEXT DEFAULT 'published',
        FOREIGN KEY (module_id) REFERENCES course_modules(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS course_enrolments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        enrolled_at TEXT DEFAULT (datetime('now','localtime')),
        last_accessed_at TEXT,
        completed_at TEXT,
        UNIQUE(user_id, course_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lesson_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        lesson_id INTEGER NOT NULL,
        status TEXT DEFAULT 'in_progress',
        started_at TEXT DEFAULT (datetime('now','localtime')),
        completed_at TEXT,
        UNIQUE(user_id, lesson_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS academy_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        activity_type TEXT NOT NULL,
        related_id INTEGER,
        recorded_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    _seed_python_quiz(cur)
    conn.commit()
    _seed_paths(cur)
    _seed_python_course(cur)
    conn.commit()
    conn.close()


def _seed_paths(cur):
    paths = [
        ("Computer Foundations", "computer-foundations",
         "Anza kujenga ujuzi wa msingi wa kompyuta â€” kutoka kwa kuwasha hadi kutumia ofisi.",
         "ðŸ’»", "#2563EB", "Beginner", 1),
        ("Programming Foundations", "programming-foundations",
         "Jifunze misingi ya programu kwa Python â€” kutoka kwa dhana hadi msimbo halisi.",
         "âŒ¨ï¸", "#7C3AED", "Beginner", 2),
        ("Web Development", "web-development",
         "Jenga tovuti na aplikesheni za browser kwa HTML, CSS, na JavaScript.",
         "ðŸŒ", "#DC2626", "Intermediate", 3),
        ("Databases & Backend", "databases-backend",
         "Jifunze SQL, API, na jinsi ya kujenga mifumo ya data yenye usalama.",
         "ðŸ—„ï¸", "#0E8F78", "Intermediate", 4),
        ("AI-Assisted Development", "ai-assisted-development",
         "Tumia AI kujenga software haraka â€” bila kupoteza uelewa wa nini kinafanya kazi.",
         "ðŸ¤–", "#F47721", "Intermediate", 5),
    ]
    for title, slug, desc, icon, color, level, seq in paths:
        cur.execute(
            "INSERT OR IGNORE INTO learning_paths "
            "(title, slug, description, icon, color, target_level, sequence_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, slug, desc, icon, color, level, seq))


def _seed_python_course(cur):
    """Seed one complete course: Python Fundamentals 101."""
    existing = cur.execute(
        "SELECT id FROM academy_courses WHERE slug = 'python-fundamentals-101'"
    ).fetchone()
    if existing:
        return

    path = cur.execute(
        "SELECT id FROM learning_paths WHERE slug = 'programming-foundations'"
    ).fetchone()
    if not path:
        return

    cur.execute(
        "INSERT INTO academy_courses (learning_path_id, title, slug, description, "
        "difficulty_level, language, estimated_duration_min, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'published')",
        (path["id"], "Python Fundamentals 101", "python-fundamentals-101",
         "Kozi ya kuanzia Python â€” kuanzia dhana za msingi hadi kuandika programu yako ya kwanza yenye mantiki.",
         "Beginner", "sw", 240))

    course_id = cur.lastrowid

    modules = [
        ("Getting Started with Python",
         "Tambua Python, jinsi ya kuandika msimbo, na kukimbiza programu yako ya kwanza."),
        ("Variables and Data",
         "Hifadhi taarifa kwa variables na ujue aina za data katika Python."),
        ("Making Decisions",
         "Tumia masharti (if/else) kufanya programu yako ifanye maamuzi."),
    ]

    lessons_data = {
        0: [
            ("What is Python?",
             "<h2>What is Python?</h2><p>Python ni lugha ya programu inayojulikana kwa urahisi wake. Ilianzishwa mwaka 1991 na Guido van Rossum na leo inatumika katika:</p><ul><li>Uendelezaji wa tovuti (web development)</li><li>Sayansi ya data (data science)</li><li>Akili bandia (artificial intelligence)</li><li>Uendeshaji wa mifumo (automation)</li></ul><h3>Kwa nini Python?</h3><p>Python ni rahisi kusoma â€” karibu kama Kiingereza cha kawaida. Hii inafanya iwe lugha nzuri kwa wanaoanza.</p><pre><code>print(\"Habari, Dunia!\")</code></pre><p>Mstari huu mmoja unaandika ujumbe kwenye skrini. Ni programu yako ya kwanza!</p><h3>Unachohitaji kuanza</h3><ul><li>Kompyuta (Windows, Mac, au Linux)</li><li>Python iliyosakinishwa (tutaiona kwenye somo lijalo)</li><li>Hamasa ya kujifunza</li></ul>", 15),
            ("Your First Program",
             "<h2>Your First Program</h2><p>Tutaandika programu yetu ya kwanza halisi. Fungua Python (au editor yoyote) na andika:</p><pre><code>print(\"Karibu IT Expert Academy!\")</code></pre><h3>Kile kinachotokea</h3><ol><li><strong>print</strong> â€” ni kazi (function) inayochapisha kitu kwenye skrini</li><li><strong>\"Karibu...\"</strong> â€” ni maandishi (string) tuliyotaka kuchapisha</li><li><strong>(...)</strong> â€” mabano yanaelekeza print kile cha kuchapisha</li></ol><h3>Jaribu</h3><p>Badilisha maandishi ndani ya quotes na uone kinachotokea:</p><pre><code>print(\"Jina langu ni [jina lako]\")</code></pre><p>Hongera! Umeandika programu yako ya kwanza yenye maana.</p>", 20),
            ("Variables and Data Types",
             "<h2>Variables and Data Types</h2><p><strong>Variable</strong> ni chombo cha kuhifadhi taarifa. Fikiria kama sanduku lenye jina:</p><pre><code>jina = \"Amina\"\numri = 25\nurefu = 1.68\namefaulu = True</code></pre><h3>Aina za data kuu</h3><ul><li><strong>String (str)</strong> â€” maandishi: <code>\"Habari\"</code></li><li><strong>Integer (int)</strong> â€” namba nzima: <code>42</code></li><li><strong>Float</strong> â€” namba yenye desimali: <code>3.14</code></li><li><strong>Boolean (bool)</strong> â€” kweli au uongo: <code>True</code> / <code>False</code></li></ul><h3>Kuchapisha variables</h3><pre><code>jina = \"Amina\"\nprint(\"Habari, \" + jina)</code></pre><p>Matokeo: <em>Habari, Amina</em></p><h3>Kumbuka</h3><p>Majina ya variables hayawezi kuwa na nafasi au kuanza na namba. Tumia <code>_</code> badala ya nafasi: <code>jina_langu</code>.</p>", 25),
        ],
        1: [
            ("if / elif / else",
             "<h2>if / elif / else â€” Kufanya Maamuzi</h2><p>Programu mara nyingi zinahitaji kuchagua kile cha kufanya kulingana na hali. Tunatumia <code>if</code>:</p><pre><code>umri = 18\nif umri >= 18:\n    print(\"Wewe ni mtu mzima\")\nelse:\n    print(\"Wewe ni kijana\")</code></pre><h3>elif kwa hali nyingi</h3><pre><code>alama = 75\nif alama >= 80:\n    print(\"A\")\nelif alama >= 60:\n    print(\"B\")\nelse:\n    print(\"F\")</code></pre><h3>Kumbuka</h3><ul><li><code>if</code> na <code>else</code> zinahitaji <code>:</code> mwishoni</li><li>Msimbo ndani ya <code>if</code> unahitaji <strong>indentation</strong> (nafasi 4)</li><li>Masharti yanaweza kuwa <code>==</code>, <code>!=</code>, <code>&gt;</code>, <code>&lt;</code>, <code>&gt;=</code>, <code>&lt;=</code></li></ul>", 30),
        ],
    }

    for mi, (mtitle, mdesc) in enumerate(modules):
        cur.execute(
            "INSERT INTO course_modules (course_id, title, description, sequence_number) "
            "VALUES (?, ?, ?, ?)",
            (course_id, mtitle, mdesc, mi + 1))
        module_id = cur.lastrowid

        for li, (ltitle, lcontent, lmin) in enumerate(lessons_data.get(mi, [])):
            cur.execute(
                "INSERT INTO lessons (module_id, title, content, sequence_number, estimated_duration_min) "
                "VALUES (?, ?, ?, ?, ?)",
                (module_id, ltitle, lcontent, li + 1, lmin))


# ============================================================
# READ FUNCTIONS
# ============================================================
def get_all_paths():
    conn = get_connection()
    rows = conn.execute(
        "SELECT p.*, "
        "(SELECT COUNT(*) FROM academy_courses c WHERE c.learning_path_id = p.id "
        " AND c.status = 'published') AS course_count "
        "FROM learning_paths p WHERE p.status = 'active' "
        "ORDER BY p.sequence_number, p.id").fetchall()
    conn.close()
    return rows


def get_path_by_slug(slug):
    conn = get_connection()
    row = conn.execute("SELECT * FROM learning_paths WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    return row


def get_all_courses():
    conn = get_connection()
    rows = conn.execute(
        "SELECT c.*, p.title AS path_title, p.icon AS path_icon, p.color AS path_color, "
        "(SELECT COUNT(*) FROM course_modules WHERE course_id = c.id) AS module_count, "
        "(SELECT COUNT(*) FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        " WHERE m.course_id = c.id) AS lesson_count "
        "FROM academy_courses c JOIN learning_paths p ON c.learning_path_id = p.id "
        "WHERE c.status = 'published' ORDER BY p.sequence_number, c.id").fetchall()
    conn.close()
    return rows


def get_course(course_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT c.*, p.title AS path_title, p.icon AS path_icon, p.color AS path_color "
        "FROM academy_courses c JOIN learning_paths p ON c.learning_path_id = p.id "
        "WHERE c.id = ?", (course_id,)).fetchone()
    conn.close()
    return row


def get_course_modules(course_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM course_modules WHERE course_id = ? "
        "ORDER BY sequence_number, id", (course_id,)).fetchall()
    conn.close()
    return rows


def get_lessons_for_module(module_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM lessons WHERE module_id = ? AND status = 'published' "
        "ORDER BY sequence_number, id", (module_id,)).fetchall()
    conn.close()
    return rows


def get_lesson(lesson_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT l.*, m.course_id, m.title AS module_title, "
        "c.title AS course_title, c.slug AS course_slug "
        "FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        "JOIN academy_courses c ON m.course_id = c.id "
        "WHERE l.id = ?", (lesson_id,)).fetchone()
    conn.close()
    return row


# ============================================================
# ENROLMENT & PROGRESS
# ============================================================
def is_enrolled(user_id, course_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM course_enrolments WHERE user_id = ? AND course_id = ?",
        (user_id, course_id)).fetchone()
    conn.close()
    return row is not None


def enrol_user(user_id, course_id):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO course_enrolments (user_id, course_id) VALUES (?, ?)",
            (user_id, course_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_user_enrollments(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT e.*, c.title, c.slug, c.description, c.estimated_duration_min, "
        "p.title AS path_title, p.icon AS path_icon, p.color AS path_color, "
        "(SELECT COUNT(*) FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        " WHERE m.course_id = c.id) AS total_lessons, "
        "(SELECT COUNT(*) FROM lesson_progress lp "
        " JOIN lessons l ON lp.lesson_id = l.id "
        " JOIN course_modules m ON l.module_id = m.id "
        " WHERE lp.user_id = ? AND m.course_id = c.id AND lp.status = 'completed') AS completed_lessons "
        "FROM course_enrolments e "
        "JOIN academy_courses c ON e.course_id = c.id "
        "JOIN learning_paths p ON c.learning_path_id = p.id "
        "WHERE e.user_id = ? ORDER BY e.last_accessed_at DESC, e.enrolled_at DESC",
        (user_id, user_id)).fetchall()
    conn.close()
    return rows


def get_lesson_progress(user_id, lesson_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM lesson_progress WHERE user_id = ? AND lesson_id = ?",
        (user_id, lesson_id)).fetchone()
    conn.close()
    return row


def mark_lesson_complete(user_id, lesson_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO lesson_progress (user_id, lesson_id, status, completed_at) "
        "VALUES (?, ?, 'completed', datetime('now','localtime')) "
        "ON CONFLICT(user_id, lesson_id) DO UPDATE SET "
        "status = 'completed', completed_at = datetime('now','localtime')",
        (user_id, lesson_id))
    # Touch enrolment
    lesson = get_lesson(lesson_id)
    if lesson:
        conn.execute(
            "UPDATE course_enrolments SET last_accessed_at = datetime('now','localtime') "
            "WHERE user_id = ? AND course_id = ?",
            (user_id, lesson["course_id"]))
    conn.commit()
    conn.close()


def touch_enrolment(user_id, course_id):
    conn = get_connection()
    conn.execute(
        "UPDATE course_enrolments SET last_accessed_at = datetime('now','localtime') "
        "WHERE user_id = ? AND course_id = ?", (user_id, course_id))
    conn.commit()
    conn.close()


def get_user_academy_stats(user_id):
    conn = get_connection()
    enrolled = conn.execute(
        "SELECT COUNT(*) FROM course_enrolments WHERE user_id = ?",
        (user_id,)).fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM lesson_progress WHERE user_id = ? AND status = 'completed'",
        (user_id,)).fetchone()[0]
    courses_done = conn.execute(
        "SELECT COUNT(*) FROM course_enrolments WHERE user_id = ? AND status = 'completed'",
        (user_id,)).fetchone()[0]
    conn.close()
    return {"enrolled": enrolled, "lessons_completed": completed, "courses_completed": courses_done}


def get_continue_learning(user_id):
    """Get the most recent in-progress lesson for the user."""
    conn = get_connection()
    row = conn.execute(
        "SELECT l.id AS lesson_id, l.title AS lesson_title, c.id AS course_id, "
        "c.title AS course_title, c.slug AS course_slug "
        "FROM course_enrolments e "
        "JOIN academy_courses c ON e.course_id = c.id "
        "JOIN course_modules m ON m.course_id = c.id "
        "JOIN lessons l ON l.module_id = m.id "
        "WHERE e.user_id = ? "
        "AND l.id NOT IN (SELECT lesson_id FROM lesson_progress WHERE user_id = ? AND status = 'completed') "
        "AND e.last_accessed_at IS NOT NULL "
        "ORDER BY e.last_accessed_at DESC, m.sequence_number, l.sequence_number "
        "LIMIT 1", (user_id, user_id)).fetchone()
    conn.close()
    return row


def get_first_lesson(course_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT l.id FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        "WHERE m.course_id = ? AND l.status = 'published' "
        "ORDER BY m.sequence_number, l.sequence_number LIMIT 1",
        (course_id,)).fetchone()
    conn.close()
    return row["id"] if row else None


def get_next_lesson(current_lesson_id):
    """Find the next lesson in the same course."""
    conn = get_connection()
    current = get_lesson(current_lesson_id)
    if not current:
        conn.close()
        return None
    row = conn.execute(
        "SELECT l.id FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        "WHERE m.course_id = ? AND l.status = 'published' "
        "AND (m.sequence_number > (SELECT sequence_number FROM course_modules WHERE id = ?) "
        "  OR (m.sequence_number = (SELECT sequence_number FROM course_modules WHERE id = ?) "
        "      AND l.sequence_number > (SELECT sequence_number FROM lessons WHERE id = ?))) "
        "ORDER BY m.sequence_number, l.sequence_number LIMIT 1",
        (current["course_id"], current["module_id"], current["module_id"], current_lesson_id)).fetchone()
    conn.close()
    return row["id"] if row else None
def _seed_python_quiz(cur):
    """Seed one quiz for the Variables and Data Types lesson."""
    existing = cur.execute("SELECT id FROM assessments LIMIT 1").fetchone()
    if existing:
        return
    lesson = cur.execute(
        "SELECT id FROM lessons WHERE title = 'Variables and Data Types' LIMIT 1"
    ).fetchone()
    if not lesson:
        return

    import json as _json

    cur.execute(
        "INSERT INTO assessments (lesson_id, title, description, passing_score, max_attempts) "
        "VALUES (?, ?, ?, ?, ?)",
        (lesson["id"], "Variables & Data Types â€” Quiz",
         "Jaribu uelewa wako wa variables na aina za data katika Python.",
         70, 3))
    aid = cur.lastrowid

    questions = [
        ("multiple_choice", "Ni ipi kati ya hizi ni string?",
         ["42", '"Habari"', "3.14", "True"], "1",
         "String ni maandishi yaliyofungwa kwenye quotes. `\"Habari\"` ni string.", 10),
        ("true_false", '`jina = "Amina"` inahifadhi maandishi kwenye variable inayoitwa `jina`.',
         ["True", "False"], "0",
         "Kweli. Ishara `=` inahifadhi thamani upande wa kulia kwenye variable upande wa kushoto.", 10),
        ("multiple_choice", "Namba `3.14` ni aina gani ya data?",
         ["Integer", "String", "Float", "Boolean"], "2",
         "Float ni namba yenye desimali (pointi).", 10),
        ("true_false", "Variable inaweza kuanza na namba, mfano `1jina`.",
         ["True", "False"], "1",
         "Uongo. Variable haiwezi kuanza na namba. Tumia `jina1` badala yake.", 10),
        ("multiple_choice", "Kuchapisha variable `jina` kwenye Python, unatumia:",
         ["show jina", "print(jina)", "echo jina", "display jina"], "1",
         "`print(jina)` inachapisha thamani ya variable.", 10),
    ]

    for qi, (qtype, qtext, options, correct, explanation, pts) in enumerate(questions):
        cur.execute(
            "INSERT INTO assessment_questions "
            "(assessment_id, question_type, question_text, options_json, "
            "correct_answer, explanation, points, sequence_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (aid, qtype, qtext, _json.dumps(options, ensure_ascii=False),
             correct, explanation, pts, qi + 1))
# ============================================================
# QUIZZES / ASSESSMENTS
# ============================================================
def get_assessment_for_lesson(lesson_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM assessments WHERE lesson_id = ? AND status = 'published'",
        (lesson_id,)).fetchone()
    conn.close()
    return row


def get_assessment(assessment_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT a.*, l.title AS lesson_title, l.id AS lesson_id, "
        "m.course_id, c.title AS course_title "
        "FROM assessments a "
        "JOIN lessons l ON a.lesson_id = l.id "
        "JOIN course_modules m ON l.module_id = m.id "
        "JOIN academy_courses c ON m.course_id = c.id "
        "WHERE a.id = ?", (assessment_id,)).fetchone()
    conn.close()
    return row


def get_assessment_questions(assessment_id):
    import json as _json
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM assessment_questions WHERE assessment_id = ? "
        "ORDER BY sequence_number, id", (assessment_id,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["options"] = _json.loads(d.get("options_json") or "[]")
        except Exception:
            d["options"] = []
        result.append(d)
    return result


def get_total_points(assessment_id):
    conn = get_connection()
    n = conn.execute(
        "SELECT COALESCE(SUM(points), 0) FROM assessment_questions WHERE assessment_id = ?",
        (assessment_id,)).fetchone()[0]
    conn.close()
    return n or 0


def get_user_attempts(assessment_id, user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM assessment_attempts WHERE assessment_id = ? AND user_id = ? "
        "ORDER BY attempt_number DESC", (assessment_id, user_id)).fetchall()
    conn.close()
    return rows


def get_best_attempt(assessment_id, user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM assessment_attempts WHERE assessment_id = ? AND user_id = ? "
        "ORDER BY score DESC, submitted_at DESC LIMIT 1",
        (assessment_id, user_id)).fetchone()
    conn.close()
    return row


def submit_attempt(assessment_id, user_id, answers):
    """
    Grade and save a new attempt.
    answers = {question_id: selected_index_as_string}
    Returns (attempt_id, score, max_score, passed).
    """
    assessment = get_assessment(assessment_id)
    if not assessment:
        return None, 0, 0, False

    # Attempt limit check
    prior = get_user_attempts(assessment_id, user_id)
    if len(prior) >= assessment["max_attempts"]:
        return None, 0, 0, False

    questions = get_assessment_questions(assessment_id)
    max_score = sum(q["points"] for q in questions)
    score = 0

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO assessment_attempts (assessment_id, user_id, attempt_number, "
        "score, max_score, passed) VALUES (?, ?, ?, ?, ?, ?)",
        (assessment_id, user_id, len(prior) + 1, 0, max_score, 0))
    attempt_id = cur.lastrowid

    for q in questions:
        selected = answers.get(str(q["id"]), "")
        is_correct = 1 if str(selected).strip() == str(q["correct_answer"]).strip() else 0
        awarded = q["points"] if is_correct else 0
        score += awarded
        cur.execute(
            "INSERT INTO assessment_responses (attempt_id, question_id, "
            "selected_answer, is_correct, points_awarded) VALUES (?, ?, ?, ?, ?)",
            (attempt_id, q["id"], str(selected), is_correct, awarded))

    passing = assessment["passing_score"]
    pct = (score * 100 // max_score) if max_score > 0 else 0
    passed = 1 if pct >= passing else 0

    cur.execute(
        "UPDATE assessment_attempts SET score = ?, max_score = ?, passed = ? "
        "WHERE id = ?", (score, max_score, passed, attempt_id))
    conn.commit()
    conn.close()

    # Auto-complete the linked lesson if passed
    if passed:
        mark_lesson_complete(user_id, assessment["lesson_id"])

    return attempt_id, score, max_score, bool(passed)


def get_attempt_details(attempt_id):
    """Get attempt + questions + user answers for the result page."""
    conn = get_connection()
    attempt = conn.execute(
        "SELECT * FROM assessment_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if not attempt:
        conn.close()
        return None
    responses = conn.execute(
        "SELECT r.*, q.question_text, q.options_json, q.correct_answer, "
        "q.explanation, q.question_type, q.points, q.sequence_number "
        "FROM assessment_responses r "
        "JOIN assessment_questions q ON r.question_id = q.id "
        "WHERE r.attempt_id = ? ORDER BY q.sequence_number",
        (attempt_id,)).fetchall()
    conn.close()

    import json as _json
    items = []
    for r in responses:
        d = dict(r)
        try:
            d["options"] = _json.loads(d.get("options_json") or "[]")
        except Exception:
            d["options"] = []
        items.append(d)

    return {"attempt": dict(attempt), "responses": items}
