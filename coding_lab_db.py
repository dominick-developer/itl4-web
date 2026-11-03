# coding_lab_db.py — Coding Lab with challenges and test cases
from database import get_connection
import json
import os

LEARNING_PATHS = {
    "python-basics": {
        "title": "Python Basics",
        "description": "Anza na Python — kutoka Hello World hadi Functions",
        "icon": "🐍",
        "color": "#2563EB",
        "language": "python",
        "challenges": [
            {
                "sequence": 1,
                "title": "Hello, World!",
                "description": "Andika program inayochapisha 'Hello, World!' kwenye screen.",
                "starter_code": "# Andika code yako hapa\n",
                "hints": ["Tumia print() function", "Weka maandishi kwenye quotes: print('Hello, World!')"],
                "test_cases": [
                    {"expected_output": "Hello, World!"}
                ]
            },
            {
                "sequence": 2,
                "title": "Salamu Ya Kibinafsi",
                "description": "Chapisha 'Habari, Dunia!' na 'Karibu Python!' kwenye mistari miwili tofauti.",
                "starter_code": "# Chapisha mistari miwili\n",
                "hints": ["Tumia print() mara mbili", "Kila print() inachapisha mstari mmoja"],
                "test_cases": [
                    {"expected_output": "Habari, Dunia!\nKaribu Python!"}
                ]
            },
            {
                "sequence": 3,
                "title": "Variables",
                "description": "Unda variable `jina` yenye thamani yako, kisha chapisha. Mfano: 'Jina langu ni Amina'",
                "starter_code": "# Unda variable kisha chapisha\n",
                "hints": ["jina = 'Amina'", "print('Jina langu ni', jina)"],
                "test_cases": [
                    {"expected_output": "Jina langu ni Amina", "note": "Tumia jina lolote lakini muundo uwe sawa"}
                ],
                "flexible": True
            },
            {
                "sequence": 4,
                "title": "Namba na Hesabu",
                "description": "Unda variables `a = 10` na `b = 5`. Chapisha jumla yao.",
                "starter_code": "a = 10\nb = 5\n# Chapisha jumla\n",
                "hints": ["Jumla ni a + b", "print(a + b)"],
                "test_cases": [
                    {"expected_output": "15"}
                ]
            },
            {
                "sequence": 5,
                "title": "Conditions (if/else)",
                "description": "Unda variable `umri = 20`. Kama ni zaidi au sawa na 18, chapisha 'Mtu mzima'. La sivyo chapisha 'Mtoto'.",
                "starter_code": "umri = 20\n# Andika if/else hapa\n",
                "hints": ["if umri >= 18:", "print('Mtu mzima')", "else:", "print('Mtoto')"],
                "test_cases": [
                    {"expected_output": "Mtu mzima"}
                ]
            },
            {
                "sequence": 6,
                "title": "Loops (for)",
                "description": "Tumia `for` loop kuchapisha namba 1 hadi 5, kila moja kwenye mstari wake.",
                "starter_code": "# Tumia for loop\n",
                "hints": ["for i in range(1, 6):", "print(i)"],
                "test_cases": [
                    {"expected_output": "1\n2\n3\n4\n5"}
                ]
            },
            {
                "sequence": 7,
                "title": "Functions",
                "description": "Unda function `jumla(a, b)` inayorudisha `a + b`. Kisha chapisha `jumla(3, 5)`.",
                "starter_code": "# Unda function jumla\n",
                "hints": ["def jumla(a, b):", "return a + b", "print(jumla(3, 5))"],
                "test_cases": [
                    {"expected_output": "8"}
                ]
            },
            {
                "sequence": 8,
                "title": "Lists na Sum",
                "description": "Unda list `namba = [1, 2, 3, 4, 5]`. Chapisha jumla ya namba zote.",
                "starter_code": "namba = [1, 2, 3, 4, 5]\n# Chapisha jumla\n",
                "hints": ["Tumia sum() function", "print(sum(namba))"],
                "test_cases": [
                    {"expected_output": "15"}
                ]
            },
        ]
    }
}


def init_coding_tables():
    """Create coding lab tables."""
    conn = get_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS coding_challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path_slug TEXT NOT NULL,
        sequence INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        starter_code TEXT,
        hints TEXT,
        test_cases TEXT,
        language TEXT NOT NULL,
        difficulty TEXT DEFAULT 'easy',
        UNIQUE(path_slug, sequence)
    )""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS coding_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        challenge_id INTEGER NOT NULL,
        code_saved TEXT,
        passed INTEGER DEFAULT 0,
        attempts INTEGER DEFAULT 0,
        last_submitted_at TEXT,
        completed_at TEXT,
        UNIQUE(user_id, challenge_id)
    )""")
    conn.commit()
    _seed_challenges(conn)
    conn.close()


def _seed_challenges(conn):
    """Seed challenges from LEARNING_PATHS."""
    for path_slug, path in LEARNING_PATHS.items():
        for ch in path["challenges"]:
            existing = conn.execute(
                "SELECT id FROM coding_challenges WHERE path_slug = ? AND sequence = ?",
                (path_slug, ch["sequence"])).fetchone()
            if existing:
                continue
            conn.execute(
                "INSERT INTO coding_challenges "
                "(path_slug, sequence, title, description, starter_code, hints, test_cases, language) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (path_slug, ch["sequence"], ch["title"], ch["description"],
                 ch["starter_code"], json.dumps(ch["hints"]),
                 json.dumps(ch["test_cases"]), path["language"]))
    conn.commit()


def get_paths_with_progress(user_id):
    """Get all learning paths with completion counts."""
    conn = get_connection()
    result = []
    for slug, path in LEARNING_PATHS.items():
        total = conn.execute(
            "SELECT COUNT(*) as n FROM coding_challenges WHERE path_slug = ?",
            (slug,)).fetchone()["n"]
        completed = conn.execute(
            "SELECT COUNT(*) as n FROM coding_progress cp "
            "JOIN coding_challenges cc ON cp.challenge_id = cc.id "
            "WHERE cp.user_id = ? AND cc.path_slug = ? AND cp.passed = 1",
            (user_id, slug)).fetchone()["n"]
        result.append({
            "slug": slug,
            "title": path["title"],
            "description": path["description"],
            "icon": path["icon"],
            "color": path["color"],
            "total": total,
            "completed": completed,
        })
    conn.close()
    return result


def get_path_challenges(user_id, path_slug):
    """Get all challenges in a path with progress and unlock status."""
    if path_slug not in LEARNING_PATHS:
        return None
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM coding_challenges WHERE path_slug = ? "
        "ORDER BY sequence", (path_slug,)).fetchall()
    
    challenges = []
    prev_passed = True  # First is always unlocked
    for r in rows:
        progress = conn.execute(
            "SELECT * FROM coding_progress WHERE user_id = ? AND challenge_id = ?",
            (user_id, r["id"])).fetchone()
        
        passed = bool(progress["passed"]) if progress else False
        unlocked = prev_passed  # Unlock if previous passed
        
        challenges.append({
            "id": r["id"],
            "sequence": r["sequence"],
            "title": r["title"],
            "description": r["description"],
            "language": r["language"],
            "passed": passed,
            "unlocked": unlocked,
            "attempts": progress["attempts"] if progress else 0,
        })
        prev_passed = passed
    conn.close()
    return {
        "path": LEARNING_PATHS[path_slug],
        "challenges": challenges,
    }


def get_challenge(challenge_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM coding_challenges WHERE id = ?", (challenge_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["hints"] = json.loads(d.get("hints") or "[]")
        d["test_cases"] = json.loads(d.get("test_cases") or "[]")
    except Exception:
        d["hints"] = []
        d["test_cases"] = []
    return d


def save_code(user_id, challenge_id, code):
    """Auto-save user code."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM coding_progress WHERE user_id = ? AND challenge_id = ?",
        (user_id, challenge_id)).fetchone()
    if existing:
        conn.execute(
            "UPDATE coding_progress SET code_saved = ? WHERE id = ?",
            (code, existing["id"]))
    else:
        conn.execute(
            "INSERT INTO coding_progress (user_id, challenge_id, code_saved) "
            "VALUES (?, ?, ?)", (user_id, challenge_id, code))
    conn.commit()
    conn.close()


def get_saved_code(user_id, challenge_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT code_saved FROM coding_progress WHERE user_id = ? AND challenge_id = ?",
        (user_id, challenge_id)).fetchone()
    conn.close()
    return row["code_saved"] if row and row["code_saved"] else None


def record_submission(user_id, challenge_id, passed):
    """Record submission attempt and mark complete if passed."""
    from datetime import datetime
    conn = get_connection()
    existing = conn.execute(
        "SELECT id, attempts FROM coding_progress "
        "WHERE user_id = ? AND challenge_id = ?",
        (user_id, challenge_id)).fetchone()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if existing:
        new_attempts = (existing["attempts"] or 0) + 1
        if passed:
            conn.execute(
                "UPDATE coding_progress SET passed = 1, attempts = ?, "
                "last_submitted_at = ?, completed_at = ? WHERE id = ?",
                (new_attempts, now, now, existing["id"]))
        else:
            conn.execute(
                "UPDATE coding_progress SET attempts = ?, last_submitted_at = ? "
                "WHERE id = ?", (new_attempts, now, existing["id"]))
    else:
        conn.execute(
            "INSERT INTO coding_progress (user_id, challenge_id, passed, attempts, "
            "last_submitted_at, completed_at) VALUES (?, ?, ?, 1, ?, ?)",
            (user_id, challenge_id, 1 if passed else 0, now,
             now if passed else None))
    conn.commit()
    conn.close()


def get_coding_stats(user_id):
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as n FROM coding_challenges").fetchone()["n"]
    passed = conn.execute(
        "SELECT COUNT(*) as n FROM coding_progress WHERE user_id = ? AND passed = 1",
        (user_id,)).fetchone()["n"]
    attempts = conn.execute(
        "SELECT COALESCE(SUM(attempts), 0) as n FROM coding_progress WHERE user_id = ?",
        (user_id,)).fetchone()["n"]
    conn.close()
    return {"total": total, "passed": passed, "attempts": attempts}