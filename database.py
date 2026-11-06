# IT LEVEL 4 CONNECT - CLASS MANAGEMENT SYSTEM
# database.py - Complete data layer

import sqlite3
import hashlib
import os
import shutil
import time
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import turso_serverless
except ImportError:
    turso_serverless = None

DB_PATH = Path(__file__).parent / "itl4.db"

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")
USE_TURSO = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN and turso_serverless)

if USE_TURSO:
    print(f"✅ Using Turso: {TURSO_DATABASE_URL[:40]}...")
else:
    print(f"⚠️  Using local SQLite: {DB_PATH}")




# ============================================================
# TURSO WRAPPER: Geuza tuples kuwa dict-like rows
# ============================================================
class DictRow:
    """Row inayofanya kazi kama sqlite3.Row (dict-like access)."""
    def __init__(self, keys, values):
        self._keys = list(keys)
        self._values = tuple(values)
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        try:
            return self._values[self._keys.index(key)]
        except ValueError:
            raise KeyError(key)
    def __getattr__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        try:
            return self._values[self._keys.index(key)]
        except ValueError:
            raise AttributeError(key)
    def keys(self):
        return self._keys
    def values(self):
        return self._values
    def __iter__(self):
        return iter(self._values)
    def __len__(self):
        return len(self._values)
    def __repr__(self):
        return f"DictRow({dict(zip(self._keys, self._values))})"


class TursoCursor:
    def __init__(self, cursor):
        self._cursor = cursor
    def execute(self, sql, params=()):
        self._cursor.execute(sql, params)
        return self
    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, tuple) and self._cursor.description:
            keys = [d[0] for d in self._cursor.description]
            return DictRow(keys, row)
        return row
    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], tuple) and self._cursor.description:
            keys = [d[0] for d in self._cursor.description]
            return [DictRow(keys, r) for r in rows]
        return rows
    def __getattr__(self, name):
        return getattr(self._cursor, name)


class TursoConnection:
    def __init__(self, conn):
        object.__setattr__(self, '_conn', conn)
    def cursor(self):
        return TursoCursor(self._conn.cursor())
    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return TursoCursor(cur)
    def commit(self):
        return self._conn.commit()
    def rollback(self):
        return self._conn.rollback()
    def close(self):
        return self._conn.close()
    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_connection():
    if USE_TURSO:
        raw_conn = turso_serverless.connect(
            TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN,
        )
        return TursoConnection(raw_conn)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
# ============================================================
# INIT DATABASE
# ============================================================
def init_database():
    conn = get_connection()
    cur = conn.cursor()

    # ---------- STREAMS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS streams (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        description TEXT
    )
    """)

    # ---------- STUDENTS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name          TEXT NOT NULL,
        reg_number         TEXT UNIQUE,
        gender             TEXT,
        date_of_birth      TEXT,
        phone              TEXT NOT NULL,
        whatsapp           TEXT,
        email              TEXT,
        stream_id          INTEGER,
        address            TEXT,
        parent_name        TEXT,
        parent_phone       TEXT,
        notes              TEXT,
        membership_status  TEXT DEFAULT 'approved',
        date_joined        TEXT,
        project_team       TEXT,
        is_active          INTEGER DEFAULT 1,
        created_at         TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (stream_id) REFERENCES streams(id)
    )
    """)

    # ---------- TEACHERS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name   TEXT NOT NULL,
        phone       TEXT,
        email       TEXT,
        notes       TEXT
    )
    """)

    # ---------- MODULES ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS modules (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        code        TEXT,
        description TEXT,
        teacher_id  INTEGER,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id)
    )
    """)

    # ---------- POSITIONS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        name    TEXT NOT NULL,
        type    TEXT NOT NULL,
        level   INTEGER DEFAULT 0
    )
    """)

    # ---------- LEADERSHIP ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leadership (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id      INTEGER NOT NULL,
        position_id     INTEGER NOT NULL,
        start_date      TEXT,
        end_date        TEXT,
        is_active       INTEGER DEFAULT 1,
        FOREIGN KEY (student_id)  REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (position_id) REFERENCES positions(id)
    )
    """)

    # ---------- USERS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        role          TEXT NOT NULL,
        student_id    INTEGER,
        teacher_id    INTEGER,
        username      TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt          TEXT NOT NULL,
        is_admin      INTEGER DEFAULT 0,
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
    )
    """)

    # ---------- MEETINGS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        title                 TEXT NOT NULL,
        meeting_type          TEXT,
        date                  TEXT,
        start_time            TEXT,
        end_time              TEXT,
        venue                 TEXT,
        chairperson_id        INTEGER,
        secretary_id          INTEGER,
        status                TEXT DEFAULT 'draft',
        resolutions           TEXT,
        next_meeting_date     TEXT,
        opened_by_id          INTEGER,
        opening_activity      TEXT,
        other_activity        TEXT,
        previous_meeting      INTEGER DEFAULT 0,
        minutes_reader_id     INTEGER,
        minutes_status        TEXT,
        purpose               TEXT,
        FOREIGN KEY (chairperson_id)    REFERENCES students(id),
        FOREIGN KEY (secretary_id)      REFERENCES students(id),
        FOREIGN KEY (opened_by_id)      REFERENCES students(id),
        FOREIGN KEY (minutes_reader_id) REFERENCES students(id)
    )
    """)

    # ---------- AGENDA ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS agenda (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id          INTEGER NOT NULL,
        order_number        INTEGER,
        title               TEXT NOT NULL,
        description         TEXT,
        discussion          TEXT,
        decisions           TEXT,
        responsible_id      INTEGER,
        due_date            TEXT,
        FOREIGN KEY (meeting_id)     REFERENCES meetings(id) ON DELETE CASCADE,
        FOREIGN KEY (responsible_id) REFERENCES students(id)
    )
    """)

    # ---------- ATTENDANCE (meetings) ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id          INTEGER NOT NULL,
        student_id          INTEGER,
        guest_name          TEXT,
        attended            INTEGER DEFAULT 1,
        absence_reason      TEXT,
        FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)

    # ---------- TIMETABLE ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS timetable (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        day             TEXT NOT NULL,
        start_time      TEXT,
        end_time        TEXT,
        module_id       INTEGER,
        teacher_id      INTEGER,
        venue           TEXT,
        notes           TEXT,
        FOREIGN KEY (module_id)  REFERENCES modules(id),
        FOREIGN KEY (teacher_id) REFERENCES teachers(id)
    )
    """)

    # ---------- ASSIGNMENTS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        type                TEXT NOT NULL,
        module_id           INTEGER,
        title               TEXT NOT NULL,
        description         TEXT,
        instructions        TEXT,
        given_date          TEXT,
        due_date            TEXT,
        max_score           INTEGER DEFAULT 100,
        teacher_id          INTEGER,
        allow_late          INTEGER DEFAULT 0,
        allowed_file_types  TEXT,
        status              TEXT DEFAULT 'draft',
        published_at        TEXT,
        updated_at          TEXT,
        created_at          TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (module_id)  REFERENCES modules(id),
        FOREIGN KEY (teacher_id) REFERENCES teachers(id)
    )
    """)

    # ---------- SUBMISSIONS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id   INTEGER NOT NULL,
        student_id      INTEGER NOT NULL,
        submitted_at    TEXT,
        submission_text TEXT,
        file_path       TEXT,
        score           INTEGER,
        comments        TEXT,
        graded_by       INTEGER,
        graded_at       TEXT,
        status          TEXT DEFAULT 'submitted',
        updated_at      TEXT,
        FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id)    REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(assignment_id, student_id)
    )
    """)

    # ---------- EXAMS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        type            TEXT,
        module_id       INTEGER,
        date            TEXT,
        start_time      TEXT,
        end_time        TEXT,
        venue           TEXT,
        max_score       INTEGER DEFAULT 100,
        notes           TEXT,
        instructions    TEXT,
        created_by_cr_id INTEGER,
        status          TEXT DEFAULT 'draft',
        published_at    TEXT,
        updated_at      TEXT,
        FOREIGN KEY (module_id) REFERENCES modules(id)
    )
    """)

    # ---------- RESULTS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id         INTEGER NOT NULL,
        student_id      INTEGER NOT NULL,
        score           INTEGER,
        grade           TEXT,
        comments        TEXT,
        FOREIGN KEY (exam_id)    REFERENCES exams(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(exam_id, student_id)
    )
    """)

    # ---------- ANNOUNCEMENTS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS announcements (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT NOT NULL,
        description     TEXT,
        important       INTEGER DEFAULT 0,
        author_id       INTEGER,
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        expires_at      TEXT,
        FOREIGN KEY (author_id) REFERENCES students(id)
    )
    """)

    # ---------- REPORTS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        type                TEXT NOT NULL,
        period_from         TEXT,
        period_to           TEXT,
        meeting_id          INTEGER,
        author_id           INTEGER,
        achievements        TEXT,
        challenges          TEXT,
        recommendations     TEXT,
        conclusion          TEXT,
        status              TEXT DEFAULT 'draft',
        created_at          TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (meeting_id) REFERENCES meetings(id),
        FOREIGN KEY (author_id)  REFERENCES students(id)
    )
    """)

    # ---------- SETTINGS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key     TEXT PRIMARY KEY,
        value   TEXT
    )
    """)

    # ---------- LETTERS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS letters (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        reference_no      TEXT,
        date              TEXT,
        type              TEXT,
        recipient         TEXT,
        address           TEXT,
        subject           TEXT,
        body              TEXT,
        closing           TEXT,
        sender_id         INTEGER,
        sender_position   TEXT,
        status            TEXT DEFAULT 'draft',
        created_at        TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (sender_id) REFERENCES students(id)
    )
    """)

    # ---------- NOTIFICATIONS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER NOT NULL,
        type          TEXT NOT NULL,
        category      TEXT,
        title         TEXT NOT NULL,
        message       TEXT,
        source_type   TEXT,
        source_id     INTEGER,
        action_url    TEXT,
        priority      TEXT DEFAULT 'normal',
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        read_at       TEXT,
        expires_at    TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # ---------- CLASS SESSIONS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS class_sessions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        session_date  TEXT NOT NULL,
        module_id     INTEGER,
        session_type  TEXT,
        start_time    TEXT,
        end_time      TEXT,
        notes         TEXT,
        created_by    INTEGER,
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (module_id)  REFERENCES modules(id),
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    """)

    # ---------- CLASS ATTENDANCE ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS class_attendance (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id    INTEGER NOT NULL,
        student_id    INTEGER NOT NULL,
        status        TEXT DEFAULT 'present',
        notes         TEXT,
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (session_id) REFERENCES class_sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(session_id, student_id)
    )
    """)

    # ---------- GROUPS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        description TEXT,
        created_by  INTEGER,
        created_at  TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (created_by) REFERENCES users(id)
    )
    """)

    # ---------- GROUP MEMBERS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS group_members (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id    INTEGER NOT NULL,
        student_id  INTEGER NOT NULL,
        joined_at   TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (group_id)   REFERENCES groups(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(group_id, student_id)
    )
    """)

    # ---------- MODULE OFFERINGS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS module_offerings (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        module_id     INTEGER NOT NULL,
        class_name    TEXT,
        academic_year TEXT,
        semester      TEXT,
        teacher_id    INTEGER,
        is_published  INTEGER DEFAULT 0,
        published_at  TEXT,
        published_by  INTEGER,
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (module_id)    REFERENCES modules(id) ON DELETE CASCADE,
        FOREIGN KEY (teacher_id)   REFERENCES teachers(id),
        FOREIGN KEY (published_by) REFERENCES users(id)
    )
    """)

    # ---------- TOPICS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        offering_id   INTEGER NOT NULL,
        title         TEXT NOT NULL,
        description   TEXT,
        order_num     INTEGER DEFAULT 1,
        duration_hrs  REAL,
        status        TEXT DEFAULT 'not_started',
        notes         TEXT,
        cover_image   TEXT,
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (offering_id) REFERENCES module_offerings(id) ON DELETE CASCADE
    )
    """)

    # ---------- SESSIONS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id      INTEGER NOT NULL,
        planned_date  TEXT,
        start_time    TEXT,
        end_time      TEXT,
        venue         TEXT,
        status        TEXT DEFAULT 'scheduled',
        notes         TEXT,
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
    )
    """)

    # ---------- MATERIALS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS materials (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id      INTEGER NOT NULL,
        title         TEXT NOT NULL,
        description   TEXT,
        file_path     TEXT,
        is_published  INTEGER DEFAULT 0,
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
    )
    """)

    # ---------- SESSION REMINDERS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS session_reminders (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id     INTEGER NOT NULL,
        minutes_before INTEGER NOT NULL,
        sent_at        TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
        UNIQUE(session_id, minutes_before)
    )
    """)
    # ---------- DAILY MESSAGES ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_messages (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        message_text  TEXT NOT NULL,
        author_id     INTEGER,
        publish_date  TEXT NOT NULL,
        expires_date  TEXT,
        is_active     INTEGER DEFAULT 1,
        created_at    TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (author_id) REFERENCES students(id)
    )
    """)
    # ---------- EXAM REMINDERS ----------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_reminders (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id         INTEGER NOT NULL,
        student_id      INTEGER NOT NULL,
        reminder_date   TEXT NOT NULL,
        channel         TEXT DEFAULT 'in_app',
        sent_at         TEXT,
        delivery_status TEXT DEFAULT 'scheduled',
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (exam_id)    REFERENCES exams(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(exam_id, student_id, reminder_date)
    )
    """)

    # ---------- MIGRATIONS ----------
    migrations = [
        ("assignments", "instructions", "TEXT"),
        ("assignments", "published_at", "TEXT"),
        ("assignments", "updated_at", "TEXT"),
        ("assignments", "allow_late", "INTEGER DEFAULT 0"),
        ("assignments", "allowed_file_types", "TEXT"),
        ("submissions", "submission_text", "TEXT"),
        ("submissions", "file_path", "TEXT"),
        ("submissions", "graded_by", "INTEGER"),
        ("submissions", "graded_at", "TEXT"),
        ("submissions", "updated_at", "TEXT"),
        ("exams", "created_by_cr_id", "INTEGER"),
        ("exams", "instructions", "TEXT"),
        ("exams", "status", "TEXT DEFAULT 'draft'"),
        ("exams", "published_at", "TEXT"),
        ("exams", "updated_at", "TEXT"),
        ("topics", "cover_image", "TEXT"),
        ("students", "is_verified", "INTEGER DEFAULT 0"),
        ("students", "verification_code", "TEXT"),
        ("students", "verification_expires_at", "TEXT"),
    ]
    for table, col, coltype in migrations:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
        except Exception:
            pass

    # ================= SEED =================
    # _seed_modules(cur)  # DISABLED — user adds own modules
    _seed_positions(cur)
    _seed_streams(cur)
    _seed_users(cur)
    _seed_settings(cur)

    conn.commit()
    conn.close()
    print("IT LEVEL 4 CONNECT database initialized.")


# ============================================================
# SEED FUNCTIONS
# ============================================================
def _seed_modules(cur):
    modules = [
        ("Programming in Java", "ITL4-JAVA", "Java programming"),
        ("Programming in Python", "ITL4-PY", "Python programming"),
        ("Database Management Systems", "ITL4-DB", "SQL and databases"),
        ("Computer Networking", "ITL4-NET", "Networking"),
        ("Web Technologies", "ITL4-WEB", "HTML, CSS, JavaScript"),
        ("Computer Hardware", "ITL4-HW", "Hardware maintenance"),
        ("Software Engineering", "ITL4-SE", "Software development"),
        ("System Analysis & Design", "ITL4-SAD", "Systems analysis"),
        ("ICT Ethics & Law", "ITL4-ETH", "ICT ethics"),
        ("Mathematics for ICT", "ITL4-MATH", "Mathematics"),
        ("Business Communication", "ITL4-COMM", "Communication"),
        ("Final Year Project", "ITL4-PROJ", "Capstone project"),
    ]
    for name, code, desc in modules:
        cur.execute(
            "INSERT OR IGNORE INTO modules (name, code, description) "
            "VALUES (?, ?, ?)", (name, code, desc))


def _seed_positions(cur):
    positions = [
        ("Class Representative (CR)", "class_leader", 1),
        ("Assistant Class Representative", "class_leader", 2),
        ("Secretary", "class_leader", 3),
        ("Assistant Secretary", "class_leader", 4),
        ("Treasurer", "class_leader", 5),
        ("Academic Representative", "class_leader", 6),
        ("Sports Representative", "class_leader", 7),
        ("Discipline Representative", "class_leader", 8),
    ]
    for name, ptype, level in positions:
        cur.execute(
            "INSERT OR IGNORE INTO positions (name, type, level) "
            "VALUES (?, ?, ?)", (name, ptype, level))


def _seed_streams(cur):
    streams = ["IT Level 4 - Stream A", "IT Level 4 - Stream B",
               "IT Level 4 - Stream C"]
    for name in streams:
        cur.execute(
            "INSERT OR IGNORE INTO streams (name) VALUES (?)", (name,))


def _seed_users(cur):
    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return

    # CR account
    cur.execute(
        "INSERT INTO students (full_name, reg_number, phone, is_active, "
        "membership_status, date_joined) "
        "VALUES (?, ?, ?, 1, 'approved', date('now'))",
        ("John Class Rep", "ITL4/CR/001", "0700111111"))
    cr_id = cur.lastrowid
    salt = os.urandom(16).hex()
    pwd = hashlib.sha256((salt + "0000").encode()).hexdigest()
    cur.execute(
        "INSERT INTO users (role, student_id, username, password_hash, "
        "salt, is_admin) VALUES (?, ?, ?, ?, ?, 1)",
        ("CR", cr_id, "cr", pwd, salt))
    row = cur.execute(
        "SELECT id FROM positions WHERE name = 'Class Representative (CR)'"
    ).fetchone()
    if row:
        cur.execute(
            "INSERT INTO leadership (student_id, position_id, "
            "start_date, is_active) VALUES (?, ?, date('now'), 1)",
            (cr_id, row[0]))

    # Lecturer account
    cur.execute(
        "INSERT INTO teachers (full_name, phone, email) VALUES (?, ?, ?)",
        ("Mr. Lecturer", "0700222222", "lecturer@college.ac.tz"))
    teacher_id = cur.lastrowid
    salt = os.urandom(16).hex()
    pwd = hashlib.sha256((salt + "0000").encode()).hexdigest()
    cur.execute(
        "INSERT INTO users (role, teacher_id, username, password_hash, "
        "salt, is_admin) VALUES (?, ?, ?, ?, ?, 0)",
        ("LECTURER", teacher_id, "lecturer", pwd, salt))

    # Student account
    cur.execute(
        "INSERT INTO students (full_name, reg_number, phone, is_active, "
        "membership_status, date_joined) "
        "VALUES (?, ?, ?, 1, 'approved', date('now'))",
        ("Jane Student", "ITL4/STU/002", "0700333333"))
    student_id = cur.lastrowid
    salt = os.urandom(16).hex()
    pwd = hashlib.sha256((salt + "0000").encode()).hexdigest()
    cur.execute(
        "INSERT INTO users (role, student_id, username, password_hash, "
        "salt, is_admin) VALUES (?, ?, ?, ?, ?, 0)",
        ("STUDENT", student_id, "student", pwd, salt))

    # Sample students
    sample = [
        ("Michael Mwangi", "ITL4/STU/003", "0700444444", "pending"),
        ("Aisha Hassan", "ITL4/STU/004", "0700555555", "approved"),
        ("David Kimaro", "ITL4/STU/005", "0700666666", "approved"),
        ("Grace Mushi", "ITL4/STU/006", "0700777777", "suspended"),
        ("Peter Msigwa", "ITL4/STU/007", "0700888888", "pending"),
    ]
    for name, reg, phone, status in sample:
        cur.execute(
            "INSERT INTO students (full_name, reg_number, phone, is_active, "
            "membership_status, date_joined) "
            "VALUES (?, ?, ?, 1, ?, date('now'))",
            (name, reg, phone, status))


def _seed_settings(cur):
    settings = [
        ("college_name", "COLLEGE OF INFORMATION TECHNOLOGY"),
        ("course_name", "IT LEVEL 4 CONNECT"),
        ("class_name", "IT LEVEL 4"),
        ("academic_year", "2024/2025"),
        ("region", "MOROGORO REGION, TANZANIA"),
        ("email", "itl4@college.ac.tz"),
        ("main_phone", "+255 700 000 000"),
        ("pobox", "P.O. Box 1000, Morogoro"),
    ]
    for key, value in settings:
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value))


# ============================================================
# STUDENTS
# ============================================================
def get_all_students():
    conn = get_connection()
    rows = conn.execute(
        "SELECT s.*, st.name AS stream_name "
        "FROM students s LEFT JOIN streams st ON s.stream_id = st.id "
        "ORDER BY s.full_name").fetchall()
    conn.close()
    return rows


def get_student(student_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT s.*, st.name AS stream_name "
        "FROM students s LEFT JOIN streams st ON s.stream_id = st.id "
        "WHERE s.id = ?", (student_id,)).fetchone()
    conn.close()
    return row


def add_student(full_name, reg_number, gender, phone, whatsapp, email,
                stream_id, date_of_birth, address, parent_name,
                parent_phone, notes=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (full_name, reg_number, gender, phone, "
        "whatsapp, email, stream_id, date_of_birth, address, "
        "parent_name, parent_phone, notes, membership_status, "
        "date_joined) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "'approved', date('now'))",
        (full_name, reg_number, gender, phone, whatsapp, email,
         stream_id, date_of_birth, address, parent_name, parent_phone,
         notes))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def update_student(student_id, full_name, reg_number, gender, phone,
                   whatsapp, email, stream_id, date_of_birth, address,
                   parent_name, parent_phone, notes=""):
    conn = get_connection()
    conn.execute(
        "UPDATE students SET full_name=?, reg_number=?, gender=?, "
        "phone=?, whatsapp=?, email=?, stream_id=?, date_of_birth=?, "
        "address=?, parent_name=?, parent_phone=?, notes=? WHERE id=?",
        (full_name, reg_number, gender, phone, whatsapp, email,
         stream_id, date_of_birth, address, parent_name, parent_phone,
         notes, student_id))
    conn.commit()
    conn.close()


def delete_student(student_id):
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()


def search_students(query):
    conn = get_connection()
    q = f"%{query}%"
    rows = conn.execute(
        "SELECT s.*, st.name AS stream_name FROM students s "
        "LEFT JOIN streams st ON s.stream_id = st.id "
        "WHERE s.full_name LIKE ? OR s.reg_number LIKE ? OR "
        "s.phone LIKE ? ORDER BY s.full_name",
        (q, q, q)).fetchall()
    conn.close()
    return rows


def get_students_with_attendance(status_filter=None, search=""):
    conn = get_connection()
    sql = (
        "SELECT s.*, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status = 'present') AS attended, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status != 'excused') AS eligible "
        "FROM students s")
    conditions = []
    params = []
    if status_filter and status_filter != "all":
        conditions.append("s.membership_status = ?")
        params.append(status_filter)
    if search:
        conditions.append("(s.full_name LIKE ? OR s.reg_number LIKE ?)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY s.full_name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if d["eligible"] > 0:
            d["attendance_pct"] = round(d["attended"] / d["eligible"] * 100)
        else:
            d["attendance_pct"] = None
        result.append(d)
    return result


def get_student_stats():
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) FROM students WHERE is_active = 1"
    ).fetchone()[0]
    approved = conn.execute(
        "SELECT COUNT(*) FROM students WHERE is_active = 1 AND "
        "membership_status = 'approved'").fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM students WHERE is_active = 1 AND "
        "membership_status = 'pending'").fetchone()[0]
    avg_sql = (
        "SELECT AVG(pct) FROM ("
        " SELECT (CAST(attended AS FLOAT) / eligible * 100) AS pct "
        " FROM (SELECT s.id, "
        "   (SELECT COUNT(*) FROM class_attendance ca WHERE "
        "    ca.student_id = s.id AND ca.status = 'present') AS attended, "
        "   (SELECT COUNT(*) FROM class_attendance ca WHERE "
        "    ca.student_id = s.id AND ca.status != 'excused') AS eligible "
        "   FROM students s WHERE s.is_active = 1) "
        " WHERE eligible > 0)")
    avg_row = conn.execute(avg_sql).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "approved": approved,
        "pending": pending,
        "avg_attendance": round(avg_row) if avg_row else 0,
    }


def update_membership_status(student_id, new_status, reason=""):
    conn = get_connection()
    if new_status == "approved":
        conn.execute(
            "UPDATE students SET membership_status = ?, "
            "date_joined = COALESCE(date_joined, date('now')) WHERE id = ?",
            (new_status, student_id))
    else:
        conn.execute(
            "UPDATE students SET membership_status = ? WHERE id = ?",
            (new_status, student_id))
    conn.commit()
    conn.close()


def get_student_profile(student_id):
    conn = get_connection()
    sql = (
        "SELECT s.*, st.name AS stream_name, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status = 'present') AS attended, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status = 'absent') AS absent, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status = 'late') AS late, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status = 'excused') AS excused, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status != 'excused') AS eligible "
        "FROM students s LEFT JOIN streams st ON s.stream_id = st.id "
        "WHERE s.id = ?")
    row = conn.execute(sql, (student_id,)).fetchone()
    conn.close()
    return row


# ============================================================
# STREAMS / TEACHERS / MODULES
# ============================================================
def get_all_streams():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM streams ORDER BY name").fetchall()
    conn.close()
    return rows


def find_or_create_stream(name):
    name = (name or "").strip()
    if not name:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM streams WHERE LOWER(name) = LOWER(?)",
        (name,)).fetchone()
    if row:
        conn.close()
        return row["id"]
    cur = conn.cursor()
    cur.execute("INSERT INTO streams (name) VALUES (?)", (name,))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_all_teachers():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM teachers ORDER BY full_name").fetchall()
    conn.close()
    return rows


def add_teacher(full_name, phone="", email="", notes=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO teachers (full_name, phone, email, notes) "
        "VALUES (?, ?, ?, ?)", (full_name, phone, email, notes))
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def get_all_modules():
    conn = get_connection()
    rows = conn.execute(
        "SELECT m.*, t.full_name AS teacher_name FROM modules m "
        "LEFT JOIN teachers t ON m.teacher_id = t.id ORDER BY m.name"
    ).fetchall()
    conn.close()
    return rows


def add_module(name, code, description=""):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO modules (name, code, description) "
            "VALUES (?, ?, ?)", (name, code, description))
        conn.commit()
        mid = cur.lastrowid
        return True, mid, "Module created."
    except Exception as e:
        return False, None, f"Error: {e}"
    finally:
        conn.close()


def update_module(module_id, name, code, description=""):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE modules SET name=?, code=?, description=? WHERE id=?",
            (name, code, description, module_id))
        conn.commit()
        return True, "Updated."
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()


def delete_module(module_id):
    conn = get_connection()
    conn.execute("DELETE FROM modules WHERE id = ?", (module_id,))
    conn.commit()
    conn.close()


def get_module(module_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM modules WHERE id = ?", (module_id,)).fetchone()
    conn.close()
    return row


# ============================================================
# POSITIONS / LEADERSHIP
# ============================================================
def get_positions(ptype=None):
    conn = get_connection()
    if ptype:
        rows = conn.execute(
            "SELECT * FROM positions WHERE type = ? ORDER BY level",
            (ptype,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM positions ORDER BY level").fetchall()
    conn.close()
    return rows


def add_leadership(student_id, position_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO leadership (student_id, position_id, start_date, "
        "is_active) VALUES (?, ?, date('now'), 1)",
        (student_id, position_id))
    conn.commit()
    conn.close()


def get_all_leadership():
    conn = get_connection()
    rows = conn.execute(
        "SELECT l.*, s.full_name, s.phone, p.name AS position_name, "
        "p.level FROM leadership l "
        "JOIN students s ON l.student_id = s.id "
        "JOIN positions p ON l.position_id = p.id "
        "WHERE l.is_active = 1 ORDER BY p.level, s.full_name"
    ).fetchall()
    conn.close()
    return rows


def delete_leadership(leadership_id):
    conn = get_connection()
    conn.execute("DELETE FROM leadership WHERE id = ?", (leadership_id,))
    conn.commit()
    conn.close()


def get_student_position(student_id):
    if not student_id:
        return ""
    conn = get_connection()
    row = conn.execute(
        "SELECT p.name FROM leadership l "
        "JOIN positions p ON l.position_id = p.id "
        "WHERE l.student_id = ? AND l.is_active = 1 "
        "ORDER BY p.level LIMIT 1", (student_id,)).fetchone()
    conn.close()
    return row["name"] if row else ""


# ============================================================
# STATS
# ============================================================
def count_students():
    conn = get_connection()
    n = conn.execute(
        "SELECT COUNT(*) FROM students WHERE is_active = 1"
    ).fetchone()[0]
    conn.close()
    return n


def count_leadership():
    conn = get_connection()
    n = conn.execute(
        "SELECT COUNT(*) FROM leadership WHERE is_active = 1"
    ).fetchone()[0]
    conn.close()
    return n


def count_modules():
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
    conn.close()
    return n


def count_pending_assignments():
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    n = conn.execute(
        "SELECT COUNT(*) FROM assignments WHERE due_date >= ? AND "
        "status = 'active'", (today,)).fetchone()[0]
    conn.close()
    return n


def count_unread_notifications(user_id):
    conn = get_connection()
    n = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND "
        "read_at IS NULL", (user_id,)).fetchone()[0]
    conn.close()
    return n


# ============================================================
# SETTINGS
# ============================================================
def get_setting(key, default=""):
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def save_settings_list(items):
    conn = get_connection()
    for key, value in items:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value))
    conn.commit()
    conn.close()


# ============================================================
# ANNOUNCEMENTS
# ============================================================
def get_all_announcements():
    conn = get_connection()
    rows = conn.execute(
        "SELECT a.*, s.full_name AS author_name FROM announcements a "
        "LEFT JOIN students s ON a.author_id = s.id "
        "ORDER BY a.important DESC, a.created_at DESC").fetchall()
    conn.close()
    return rows


def add_announcement(title, description, author_id, important=0,
                     expires_at=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO announcements (title, description, author_id, "
        "important, expires_at) VALUES (?, ?, ?, ?, ?)",
        (title, description, author_id, important, expires_at))
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def delete_announcement(announcement_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM announcements WHERE id = ?", (announcement_id,))
    conn.commit()
    conn.close()


# ============================================================
# NOTIFICATIONS
# ============================================================
def add_notification(user_id, notif_type, category, title, message="",
                     source_type="", source_id=None, action_url="",
                     priority="normal"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notifications (user_id, type, category, title, "
        "message, source_type, source_id, action_url, priority) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, notif_type, category, title, message, source_type,
         source_id, action_url, priority))
    conn.commit()
    nid = cur.lastrowid
    conn.close()
    return nid


def get_user_notifications(user_id, unread_only=False, category=None,
                            limit=100):
    conn = get_connection()
    sql = "SELECT * FROM notifications WHERE user_id = ?"
    params = [user_id]
    if unread_only:
        sql += " AND read_at IS NULL"
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def mark_notification_read(notification_id):
    conn = get_connection()
    conn.execute(
        "UPDATE notifications SET read_at = datetime('now','localtime') "
        "WHERE id = ? AND read_at IS NULL", (notification_id,))
    conn.commit()
    conn.close()


def mark_all_read(user_id):
    conn = get_connection()
    conn.execute(
        "UPDATE notifications SET read_at = datetime('now','localtime') "
        "WHERE user_id = ? AND read_at IS NULL", (user_id,))
    conn.commit()
    conn.close()


def delete_notification(notification_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM notifications WHERE id = ?", (notification_id,))
    conn.commit()
    conn.close()


# ============================================================
# STUDENT SIGNUP
# ============================================================
def signup_student(admission_no, password, full_name, phone,
                   email="", gender="", role="STUDENT"):
    """Create a pending account. Returns (ok, info_dict, message)."""
    from datetime import datetime, timedelta
    import random

    admission_no = (admission_no or "").strip().upper()
    email = (email or "").strip().lower()

    if not admission_no:
        return False, None, "Admission number is required."
    if not password or len(password) < 6:
        return False, None, "Password must be at least 6 characters."
    if not full_name or not full_name.strip():
        return False, None, "Full name is required."
    if not phone or not phone.strip():
        return False, None, "Phone number is required."
    if not email:
        return False, None, "Email is required for verification."
    if role not in ("STUDENT", "CR"):
        return False, None, "Invalid role."

    conn = get_connection()
    if conn.execute(
        "SELECT id FROM students WHERE LOWER(reg_number) = LOWER(?)",
        (admission_no,)).fetchone():
        conn.close()
        return False, None, "Admission number already registered."
    if conn.execute(
        "SELECT id FROM users WHERE LOWER(username) = LOWER(?)",
        (admission_no,)).fetchone():
        conn.close()
        return False, None, "Username already in use."
    if conn.execute(
        "SELECT id FROM students WHERE LOWER(email) = LOWER(?)",
        (email,)).fetchone():
        conn.close()
        return False, None, "Email already registered."

    cur = conn.cursor()
    code = f"{random.randint(100000, 999999)}"
    expires_at = (datetime.utcnow() + timedelta(minutes=15)).strftime(
        "%Y-%m-%d %H:%M:%S")

    if role == "CR":
        student_status = "approved"
        verified = 1
        verify_code = None
        verify_expires = None
    else:
        student_status = "pending"
        verified = 0
        verify_code = code
        verify_expires = expires_at

    cur.execute(
        "INSERT INTO students (full_name, reg_number, gender, phone, "
        "email, membership_status, is_active, is_verified, "
        "verification_code, verification_expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
        (full_name.strip(), admission_no, gender or None,
         phone.strip(), email, student_status, verified,
         verify_code, verify_expires))
    student_id = cur.lastrowid

    salt = os.urandom(16).hex()
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    is_admin = 1 if role == "CR" else 0
    cur.execute(
        "INSERT INTO users (role, student_id, username, password_hash, "
        "salt, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
        (role, student_id, admission_no, pwd_hash, salt, is_admin))
    user_id = cur.lastrowid

    conn.commit()
    conn.close()

    info = {
        "user_id": user_id,
        "student_id": student_id,
        "code": code,
        "email": email,
        "full_name": full_name.strip(),
        "admission_no": admission_no,
        "role": role,
    }
    return True, info, "Account created! Check your email for the verification code."
def approve_student_account(student_id):
    conn = get_connection()
    conn.execute(
        "UPDATE students SET membership_status = 'approved', "
        "date_joined = date('now') WHERE id = ?", (student_id,))
    user = conn.execute(
        "SELECT id, username FROM users WHERE student_id = ?",
        (student_id,)).fetchone()
    if user:
        conn.execute(
            "INSERT INTO notifications (user_id, type, category, title, "
            "message) VALUES (?, 'success', 'account', "
            "'Account Approved', ?)",
            (user["id"],
             "Your account has been approved! You can now access "
             "all class resources."))
    conn.commit()
    conn.close()
    return user["username"] if user else None


# ============================================================
# GROUPS
# ============================================================
def create_group(name, description, created_by):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO groups (name, description, created_by) "
        "VALUES (?, ?, ?)", (name, description, created_by))
    conn.commit()
    gid = cur.lastrowid
    conn.close()
    return gid


def get_all_groups():
    conn = get_connection()
    rows = conn.execute(
        "SELECT g.*, (SELECT COUNT(*) FROM group_members gm WHERE "
        " gm.group_id = g.id) AS member_count FROM groups g "
        "ORDER BY g.name").fetchall()
    conn.close()
    return rows


def get_group(group_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
    conn.close()
    return row


def delete_group(group_id):
    conn = get_connection()
    conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
    conn.commit()
    conn.close()


def get_group_members(group_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT gm.*, s.full_name, s.reg_number, s.phone, "
        "s.membership_status FROM group_members gm "
        "JOIN students s ON gm.student_id = s.id "
        "WHERE gm.group_id = ? ORDER BY s.full_name",
        (group_id,)).fetchall()
    conn.close()
    return rows


def set_group_members(group_id, student_ids):
    conn = get_connection()
    conn.execute(
        "DELETE FROM group_members WHERE group_id = ?", (group_id,))
    for sid in student_ids:
        conn.execute(
            "INSERT OR IGNORE INTO group_members (group_id, student_id) "
            "VALUES (?, ?)", (group_id, sid))
    conn.commit()
    conn.close()


# ============================================================
# MODULE OFFERINGS
# ============================================================
def create_offering(module_id, class_name, academic_year, semester,
                    teacher_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO module_offerings (module_id, class_name, "
        "academic_year, semester, teacher_id) VALUES (?, ?, ?, ?, ?)",
        (module_id, class_name, academic_year, semester, teacher_id))
    conn.commit()
    oid = cur.lastrowid
    conn.close()
    return oid


def get_offerings_for_teacher(teacher_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT o.*, m.name AS module_name, m.code AS module_code, "
        "t.full_name AS teacher_name, "
        "(SELECT COUNT(*) FROM topics WHERE offering_id = o.id) "
        " AS topic_count, "
        "(SELECT COUNT(*) FROM topics WHERE offering_id = o.id AND "
        " status = 'completed') AS topics_done FROM module_offerings o "
        "JOIN modules m ON o.module_id = m.id "
        "LEFT JOIN teachers t ON o.teacher_id = t.id "
        "WHERE o.teacher_id = ? ORDER BY o.is_published DESC, m.name",
        (teacher_id,)).fetchall()
    conn.close()
    return rows


def get_all_offerings():
    conn = get_connection()
    rows = conn.execute(
        "SELECT o.*, m.name AS module_name, m.code AS module_code, "
        "m.description AS module_desc, t.full_name AS teacher_name, "
        "(SELECT COUNT(*) FROM topics WHERE offering_id = o.id) "
        " AS topic_count, "
        "(SELECT COUNT(*) FROM topics WHERE offering_id = o.id AND "
        " status = 'completed') AS topics_done FROM module_offerings o "
        "JOIN modules m ON o.module_id = m.id "
        "LEFT JOIN teachers t ON o.teacher_id = t.id "
        "ORDER BY m.name").fetchall()
    conn.close()
    return rows


def get_published_offerings():
    conn = get_connection()
    rows = conn.execute(
        "SELECT o.*, m.name AS module_name, m.code AS module_code, "
        "m.description AS module_desc, t.full_name AS teacher_name, "
        "(SELECT COUNT(*) FROM topics WHERE offering_id = o.id) "
        " AS topic_count, "
        "(SELECT COUNT(*) FROM topics WHERE offering_id = o.id AND "
        " status = 'completed') AS topics_done FROM module_offerings o "
        "JOIN modules m ON o.module_id = m.id "
        "LEFT JOIN teachers t ON o.teacher_id = t.id "
        "WHERE o.is_published = 1 ORDER BY m.name").fetchall()
    conn.close()
    return rows


def get_offering(offering_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT o.*, m.name AS module_name, m.code AS module_code, "
        "m.description AS module_desc, t.full_name AS teacher_name "
        "FROM module_offerings o JOIN modules m ON o.module_id = m.id "
        "LEFT JOIN teachers t ON o.teacher_id = t.id WHERE o.id = ?",
        (offering_id,)).fetchone()
    conn.close()
    return row


def publish_offering(offering_id, user_id):
    conn = get_connection()
    conn.execute(
        "UPDATE module_offerings SET is_published = 1, "
        "published_at = datetime('now','localtime'), published_by = ? "
        "WHERE id = ?", (user_id, offering_id))
    conn.commit()
    conn.close()


def unpublish_offering(offering_id):
    conn = get_connection()
    conn.execute(
        "UPDATE module_offerings SET is_published = 0 WHERE id = ?",
        (offering_id,))
    conn.commit()
    conn.close()


def delete_offering(offering_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM module_offerings WHERE id = ?", (offering_id,))
    conn.commit()
    conn.close()


# ============================================================
# TOPICS
# ============================================================
def add_topic(offering_id, title, description, duration_hrs=0):
    conn = get_connection()
    cur = conn.cursor()
    order_num = cur.execute(
        "SELECT COALESCE(MAX(order_num), 0) + 1 FROM topics WHERE "
        "offering_id = ?", (offering_id,)).fetchone()[0]
    cur.execute(
        "INSERT INTO topics (offering_id, title, description, "
        "order_num, duration_hrs) VALUES (?, ?, ?, ?, ?)",
        (offering_id, title, description, order_num, duration_hrs))
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def get_topics(offering_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM topics WHERE offering_id = ? "
        "ORDER BY order_num, id", (offering_id,)).fetchall()
    conn.close()
    return rows


def update_topic_status(topic_id, status, notes=""):
    conn = get_connection()
    conn.execute(
        "UPDATE topics SET status = ?, notes = ? WHERE id = ?",
        (status, notes, topic_id))
    conn.commit()
    conn.close()


def update_topic(topic_id, title, description, duration_hrs):
    conn = get_connection()
    conn.execute(
        "UPDATE topics SET title = ?, description = ?, "
        "duration_hrs = ? WHERE id = ?",
        (title, description, duration_hrs, topic_id))
    conn.commit()
    conn.close()


def delete_topic(topic_id):
    conn = get_connection()
    conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
    conn.commit()
    conn.close()


def _covers_dir():
    base = Path(__file__).parent / "uploads" / "covers"
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_topic_cover(topic_id, source_path):
    src = Path(source_path)
    if not src.exists():
        return False, "File does not exist."
    uploads = _covers_dir()
    safe = src.name.replace(" ", "_")
    filename = f"t{topic_id}_{int(time.time())}_{safe}"
    dest = uploads / filename
    try:
        shutil.copy2(src, dest)
    except Exception as e:
        return False, f"Copy failed: {e}"
    conn = get_connection()
    conn.execute(
        "UPDATE topics SET cover_image = ? WHERE id = ?",
        (filename, topic_id))
    conn.commit()
    conn.close()
    return True, filename


def get_topic_cover_path(topic):
    if not topic:
        return None
    try:
        cover = topic["cover_image"]
    except (KeyError, IndexError):
        return None
    if not cover:
        return None
    p = _covers_dir() / cover
    return str(p) if p.exists() else None


# ============================================================
# SESSIONS
# ============================================================
def add_session(topic_id, planned_date, start_time, end_time, venue):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sessions (topic_id, planned_date, start_time, "
        "end_time, venue) VALUES (?, ?, ?, ?, ?)",
        (topic_id, planned_date, start_time, end_time, venue))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def get_sessions(topic_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE topic_id = ? "
        "ORDER BY planned_date, start_time", (topic_id,)).fetchall()
    conn.close()
    return rows


def update_session(session_id, planned_date, start_time, end_time,
                   venue, status="scheduled"):
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET planned_date = ?, start_time = ?, "
        "end_time = ?, venue = ?, status = ? WHERE id = ?",
        (planned_date, start_time, end_time, venue, status, session_id))
    conn.commit()
    conn.close()


def delete_session(session_id):
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def get_timetable_sessions(search="", date_filter=None,
                            day_filter=None, module_id=None,
                            only_published=False):
    conn = get_connection()
    sql = (
        "SELECT s.id AS session_id, s.planned_date, s.start_time, "
        "s.end_time, s.venue, s.status AS session_status, "
        "t.id AS topic_id, t.title AS topic_title, "
        "o.id AS offering_id, o.is_published, "
        "m.id AS module_id, m.name AS module_name, m.code AS module_code, "
        "te.full_name AS teacher_name, te.phone AS teacher_phone, te.email AS teacher_email, m.description AS module_desc "
        "FROM sessions s JOIN topics t ON s.topic_id = t.id "
        "JOIN module_offerings o ON t.offering_id = o.id "
        "JOIN modules m ON o.module_id = m.id "
        "LEFT JOIN teachers te ON o.teacher_id = te.id WHERE 1=1")
    params = []
    if only_published:
        sql += " AND o.is_published = 1"
    if search:
        sql += (" AND (m.name LIKE ? OR t.title LIKE ? OR s.venue LIKE ? "
                "OR m.code LIKE ?)")
        q = f"%{search}%"
        params.extend([q, q, q, q])
    if date_filter:
        sql += " AND s.planned_date = ?"
        params.append(date_filter)
    if module_id:
        sql += " AND m.id = ?"
        params.append(module_id)
    sql += " ORDER BY s.planned_date, s.start_time"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    if day_filter and day_filter != "All days":
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                "Saturday", "Sunday"]
        try:
            target = days.index(day_filter)
        except ValueError:
            return rows
        filtered = []
        for r in rows:
            try:
                d = datetime.strptime(r["planned_date"], "%Y-%m-%d")
                if d.weekday() == target:
                    filtered.append(r)
            except (ValueError, TypeError):
                continue
        return filtered
    return rows


def get_modules_with_sessions():
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT m.id, m.name, m.code FROM modules m "
        "JOIN module_offerings o ON o.module_id = m.id "
        "JOIN topics t ON t.offering_id = o.id "
        "JOIN sessions s ON s.topic_id = t.id ORDER BY m.name"
    ).fetchall()
    conn.close()
    return rows


def get_timetable_stats():
    from datetime import datetime as dt, timedelta
    today = dt.now().strftime("%Y-%m-%d")
    week_end = (dt.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    conn = get_connection()
    today_count = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE planned_date = ?",
        (today,)).fetchone()[0]
    week_count = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE planned_date >= ? AND "
        "planned_date <= ?", (today, week_end)).fetchone()[0]
    total = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE planned_date >= ?",
        (today,)).fetchone()[0]
    conn.close()
    return {"today": today_count, "week": week_count, "total": total}


# ============================================================
# MATERIALS
# ============================================================
def _uploads_dir():
    base = Path(__file__).parent / "uploads" / "materials"
    base.mkdir(parents=True, exist_ok=True)
    return base


def upload_material_file(topic_id, title, description, source_path):
    src = Path(source_path)
    if not src.exists():
        return False, None, "Source file does not exist."
    uploads = _uploads_dir()
    safe = src.name.replace(" ", "_")
    filename = f"t{topic_id}_{int(time.time())}_{safe}"
    dest = uploads / filename
    try:
        shutil.copy2(src, dest)
    except Exception as e:
        return False, None, f"Copy failed: {e}"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO materials (topic_id, title, description, file_path, "
        "is_published) VALUES (?, ?, ?, ?, 1)",
        (topic_id, title, description, filename))
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return True, mid, "Material uploaded."


def get_materials(topic_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM materials WHERE topic_id = ? ORDER BY id",
        (topic_id,)).fetchall()
    conn.close()
    return rows


def get_material_full_path(material):
    if not material or not material["file_path"]:
        return None
    p = _uploads_dir() / material["file_path"]
    return str(p) if p.exists() else None


def delete_material_with_file(material_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    if row and row["file_path"]:
        try:
            p = _uploads_dir() / row["file_path"]
            if p.exists():
                p.unlink()
        except Exception:
            pass
    conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
    conn.commit()
    conn.close()


# ============================================================
# ASSIGNMENTS
# ============================================================
def create_assignment(module_id, teacher_id, title, instructions,
                       atype, max_marks, due_at, allow_late=0,
                       allowed_file_types="pdf,docx,pptx,xlsx,zip"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO assignments (type, module_id, title, description, "
        "instructions, given_date, due_date, max_score, teacher_id, "
        "allow_late, allowed_file_types, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, date('now'), ?, ?, ?, ?, ?, 'draft', "
        "datetime('now','localtime'))",
        (atype, module_id, title, instructions, instructions, due_at,
         max_marks, teacher_id, allow_late, allowed_file_types))
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def publish_assignment(assignment_id):
    conn = get_connection()
    conn.execute(
        "UPDATE assignments SET status = 'published', "
        "published_at = datetime('now','localtime') WHERE id = ?",
        (assignment_id,))
    conn.commit()
    conn.close()


def delete_assignment(assignment_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM assignments WHERE id = ?", (assignment_id,))
    conn.commit()
    conn.close()


def get_assignments_for_teacher(teacher_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT a.*, m.name AS module_name, m.code AS module_code, "
        "(SELECT COUNT(*) FROM submissions WHERE assignment_id = a.id) "
        " AS sub_count, "
        "(SELECT COUNT(*) FROM submissions WHERE assignment_id = a.id "
        " AND score IS NOT NULL) AS graded_count FROM assignments a "
        "JOIN modules m ON a.module_id = m.id WHERE a.teacher_id = ? "
        "ORDER BY a.due_date DESC", (teacher_id,)).fetchall()
    conn.close()
    return rows


def get_published_assignments():
    conn = get_connection()
    rows = conn.execute(
        "SELECT a.*, m.name AS module_name, m.code AS module_code, "
        "t.full_name AS teacher_name FROM assignments a "
        "JOIN modules m ON a.module_id = m.id "
        "LEFT JOIN teachers t ON a.teacher_id = t.id "
        "WHERE a.status IN ('published', 'graded', 'closed') "
        "ORDER BY a.due_date DESC").fetchall()
    conn.close()
    return rows


def get_assignment(assignment_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT a.*, m.name AS module_name, m.code AS module_code, "
        "t.full_name AS teacher_name FROM assignments a "
        "JOIN modules m ON a.module_id = m.id "
        "LEFT JOIN teachers t ON a.teacher_id = t.id WHERE a.id = ?",
        (assignment_id,)).fetchone()
    conn.close()
    return row


# ============================================================
# SUBMISSIONS
# ============================================================
def _submission_files_dir():
    base = Path(__file__).parent / "uploads" / "submissions"
    base.mkdir(parents=True, exist_ok=True)
    return base


def submit_assignment(assignment_id, student_id, submission_text,
                       source_file_path=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    a = get_assignment(assignment_id)
    if not a:
        return False, None, "Assignment not found."
    try:
        due = datetime.strptime(a["due_date"], "%Y-%m-%d")
        is_late = datetime.now() > due
    except (ValueError, TypeError):
        is_late = False

    file_ref = None
    if source_file_path:
        src = Path(source_file_path)
        if src.exists():
            uploads = _submission_files_dir()
            safe = src.name.replace(" ", "_")
            filename = (
                f"a{assignment_id}_s{student_id}_"
                f"{int(time.time())}_{safe}")
            dest = uploads / filename
            try:
                shutil.copy2(src, dest)
                file_ref = filename
            except Exception as e:
                return False, None, f"File copy failed: {e}"

    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM submissions WHERE assignment_id = ? AND "
        "student_id = ?", (assignment_id, student_id)).fetchone()
    sub_status = "late" if is_late else "submitted"

    if existing:
        conn.execute(
            "UPDATE submissions SET submitted_at = ?, "
            "submission_text = ?, file_path = COALESCE(?, file_path), "
            "status = ?, updated_at = ? WHERE id = ?",
            (now, submission_text, file_ref, sub_status, now,
             existing["id"]))
        sid = existing["id"]
    else:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO submissions (assignment_id, student_id, "
            "submitted_at, submission_text, file_path, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (assignment_id, student_id, now, submission_text, file_ref,
             sub_status))
        sid = cur.lastrowid
    conn.commit()
    conn.close()

    if a["teacher_id"]:
        try:
            teacher_user = conn_user_for_teacher(a["teacher_id"])
            if teacher_user:
                add_notification(
                    teacher_user, notif_type="info",
                    category="assignment", title="New Submission",
                    message=f"New submission for {a['title']}",
                    source_type="submission", source_id=sid)
        except Exception:
            pass

    return True, sid, "Submitted successfully."


def conn_user_for_teacher(teacher_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM users WHERE teacher_id = ?",
        (teacher_id,)).fetchone()
    conn.close()
    return row["id"] if row else None


def get_submission(assignment_id, student_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM submissions WHERE assignment_id = ? AND "
        "student_id = ?", (assignment_id, student_id)).fetchone()
    conn.close()
    return row


def get_submissions_for_assignment(assignment_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT s.*, st.full_name, st.reg_number FROM submissions s "
        "JOIN students st ON s.student_id = st.id "
        "WHERE s.assignment_id = ? ORDER BY s.submitted_at DESC",
        (assignment_id,)).fetchall()
    conn.close()
    return rows


def get_submission_full_path(submission):
    if not submission or not submission["file_path"]:
        return None
    p = _submission_files_dir() / submission["file_path"]
    return str(p) if p.exists() else None


def grade_submission(submission_id, score, feedback, graded_by):
    conn = get_connection()
    conn.execute(
        "UPDATE submissions SET score = ?, comments = ?, graded_by = ?, "
        "graded_at = datetime('now','localtime'), status = 'graded', "
        "updated_at = datetime('now','localtime') WHERE id = ?",
        (score, feedback, graded_by, submission_id))
    conn.commit()
    row = conn.execute(
        "SELECT s.student_id, a.title FROM submissions s "
        "JOIN assignments a ON s.assignment_id = a.id WHERE s.id = ?",
        (submission_id,)).fetchone()
    if row:
        try:
            stu_user = conn.execute(
                "SELECT id FROM users WHERE student_id = ?",
                (row["student_id"],)).fetchone()
            if stu_user:
                conn.execute(
                    "INSERT INTO notifications (user_id, type, category, "
                    "title, message) VALUES (?, 'success', 'assignment', "
                    "'Assignment Graded', ?)",
                    (stu_user["id"],
                     f"Your submission for {row['title']} has been graded."))
        except Exception:
            pass
    conn.commit()
    conn.close()


# ============================================================
# EXAMS
# ============================================================
def create_exam(module_id, created_by_cr_id, title, etype, exam_date,
                start_time, end_time, venue, instructions=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO exams (name, type, module_id, date, start_time, "
        "end_time, venue, notes, created_by_cr_id, instructions, "
        "status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "'draft', datetime('now','localtime'))",
        (title, etype, module_id, exam_date, start_time, end_time, venue,
         instructions, created_by_cr_id, instructions))
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def publish_exam(exam_id):
    conn = get_connection()
    conn.execute(
        "UPDATE exams SET status = 'published', "
        "published_at = datetime('now','localtime') WHERE id = ?",
        (exam_id,))
    conn.commit()
    conn.close()


def cancel_exam(exam_id):
    conn = get_connection()
    conn.execute(
        "UPDATE exams SET status = 'cancelled', "
        "updated_at = datetime('now','localtime') WHERE id = ?",
        (exam_id,))
    conn.execute(
        "DELETE FROM exam_reminders WHERE exam_id = ? AND "
        "delivery_status = 'scheduled'", (exam_id,))
    conn.commit()
    conn.close()


def delete_exam(exam_id):
    conn = get_connection()
    conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    conn.commit()
    conn.close()


def get_all_exams():
    conn = get_connection()
    rows = conn.execute(
        "SELECT e.*, m.name AS module_name, m.code AS module_code, "
        "u.username AS created_by_name FROM exams e "
        "JOIN modules m ON e.module_id = m.id "
        "LEFT JOIN users u ON e.created_by_cr_id = u.id "
        "ORDER BY e.date DESC, e.start_time DESC").fetchall()
    conn.close()
    return rows


def get_published_exams():
    conn = get_connection()
    rows = conn.execute(
        "SELECT e.*, m.name AS module_name, m.code AS module_code "
        "FROM exams e JOIN modules m ON e.module_id = m.id "
        "WHERE e.status = 'published' ORDER BY e.date, e.start_time"
    ).fetchall()
    conn.close()
    return rows


def get_exam(exam_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT e.*, m.name AS module_name, m.code AS module_code "
        "FROM exams e JOIN modules m ON e.module_id = m.id "
        "WHERE e.id = ?", (exam_id,)).fetchone()
    conn.close()
    return row


def get_exams_needing_reminder():
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    conn = get_connection()
    exams = conn.execute(
        "SELECT * FROM exams WHERE status = 'published'").fetchall()
    results = []
    for e in exams:
        try:
            d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        days_until = (d - today).days
        if days_until < 0:
            continue
        should = False
        if days_until <= 7:
            should = True
        elif days_until % 7 == 0:
            should = True
        if should:
            results.append((dict(e), days_until, today_str))
    conn.close()
    return results


def mark_exam_reminder_sent(exam_id, student_id, reminder_date):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO exam_reminders (exam_id, student_id, "
            "reminder_date, sent_at, delivery_status) VALUES (?, ?, ?, "
            "datetime('now','localtime'), 'sent')",
            (exam_id, student_id, reminder_date))
        conn.commit()
    except Exception:
        pass
    conn.close()


# ============================================================
# SESSION REMINDERS
# ============================================================
def get_sessions_needing_reminder():
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        "SELECT s.*, t.title AS topic_title, m.name AS module_name, "
        "o.id AS offering_id FROM sessions s "
        "JOIN topics t ON s.topic_id = t.id "
        "JOIN module_offerings o ON t.offering_id = o.id "
        "JOIN modules m ON o.module_id = m.id "
        "WHERE s.planned_date = ? AND o.is_published = 1 "
        "ORDER BY s.start_time", (today,)).fetchall()
    results = []
    for s in rows:
        try:
            start = datetime.strptime(
                f"{s['planned_date']} {s['start_time']}",
                "%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            continue
        minutes_until = (start - now).total_seconds() / 60
        for threshold in [30, 15, 5]:
            if 0 < minutes_until <= threshold:
                sent = conn.execute(
                    "SELECT id FROM session_reminders WHERE session_id = "
                    "? AND minutes_before = ?",
                    (s["id"], threshold)).fetchone()
                if not sent:
                    results.append((dict(s), threshold, minutes_until))
                break
    conn.close()
    return results


def mark_session_reminder_sent(session_id, minutes_before):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO session_reminders (session_id, "
            "minutes_before) VALUES (?, ?)",
            (session_id, minutes_before))
        conn.commit()
    except Exception:
        pass
    conn.close()
# ============================================================
# MEETINGS
# ============================================================

def create_meeting(title, mtype, mdate, start_time, end_time, venue,
                    chairperson_id, secretary_id, opening_activity="",
                    purpose="", previous_meeting=0,
                    minutes_reader_id=None, minutes_status=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO meetings (title, meeting_type, date, start_time, "
        "end_time, venue, chairperson_id, secretary_id, status, "
        "opening_activity, purpose, previous_meeting, "
        "minutes_reader_id, minutes_status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?)",
        (title, mtype, mdate, start_time, end_time, venue,
         chairperson_id, secretary_id, opening_activity, purpose,
         previous_meeting, minutes_reader_id, minutes_status))
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return mid


def update_meeting(meeting_id, title, mtype, mdate, start_time, end_time,
                    venue, chairperson_id, secretary_id, opening_activity,
                    purpose, previous_meeting=0, minutes_reader_id=None,
                    minutes_status="", resolutions="",
                    next_meeting_date=""):
    conn = get_connection()
    conn.execute(
        "UPDATE meetings SET title=?, meeting_type=?, date=?, "
        "start_time=?, end_time=?, venue=?, chairperson_id=?, "
        "secretary_id=?, opening_activity=?, purpose=?, "
        "previous_meeting=?, minutes_reader_id=?, minutes_status=?, "
        "resolutions=?, next_meeting_date=? WHERE id=?",
        (title, mtype, mdate, start_time, end_time, venue,
         chairperson_id, secretary_id, opening_activity, purpose,
         previous_meeting, minutes_reader_id, minutes_status,
         resolutions, next_meeting_date, meeting_id))
    conn.commit()
    conn.close()


def publish_meeting(meeting_id):
    conn = get_connection()
    conn.execute(
        "UPDATE meetings SET status = 'published' WHERE id = ?",
        (meeting_id,))
    conn.commit()
    conn.close()


def delete_meeting(meeting_id):
    conn = get_connection()
    conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    conn.commit()
    conn.close()


def get_all_meetings():
    conn = get_connection()
    rows = conn.execute(
        "SELECT m.*, "
        "c.full_name AS chairperson_name, "
        "s.full_name AS secretary_name, "
        "(SELECT COUNT(*) FROM agenda WHERE meeting_id = m.id) "
        " AS agenda_count, "
        "(SELECT COUNT(*) FROM attendance WHERE meeting_id = m.id "
        " AND attended = 1) AS attendee_count "
        "FROM meetings m "
        "LEFT JOIN students c ON m.chairperson_id = c.id "
        "LEFT JOIN students s ON m.secretary_id = s.id "
        "ORDER BY m.date DESC, m.id DESC").fetchall()
    conn.close()
    return rows


def get_meeting(meeting_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT m.*, "
        "c.full_name AS chairperson_name, "
        "s.full_name AS secretary_name, "
        "mr.full_name AS minutes_reader_name "
        "FROM meetings m "
        "LEFT JOIN students c  ON m.chairperson_id = c.id "
        "LEFT JOIN students s  ON m.secretary_id = s.id "
        "LEFT JOIN students mr ON m.minutes_reader_id = mr.id "
        "WHERE m.id = ?", (meeting_id,)).fetchone()
    conn.close()
    return row


# ---------- AGENDA ----------
def add_agenda(meeting_id, title, description="", responsible_id=None,
                due_date=""):
    conn = get_connection()
    cur = conn.cursor()
    order_num = cur.execute(
        "SELECT COALESCE(MAX(order_number), 0) + 1 FROM agenda "
        "WHERE meeting_id = ?", (meeting_id,)).fetchone()[0]
    cur.execute(
        "INSERT INTO agenda (meeting_id, order_number, title, description, "
        "responsible_id, due_date) VALUES (?, ?, ?, ?, ?, ?)",
        (meeting_id, order_num, title, description, responsible_id,
         due_date))
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def get_agenda(meeting_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT a.*, s.full_name AS responsible_name FROM agenda a "
        "LEFT JOIN students s ON a.responsible_id = s.id "
        "WHERE a.meeting_id = ? ORDER BY a.order_number, a.id",
        (meeting_id,)).fetchall()
    conn.close()
    return rows


def update_agenda(agenda_id, title, description, discussion, decisions,
                   responsible_id=None, due_date=""):
    conn = get_connection()
    conn.execute(
        "UPDATE agenda SET title=?, description=?, discussion=?, "
        "decisions=?, responsible_id=?, due_date=? WHERE id=?",
        (title, description, discussion, decisions, responsible_id,
         due_date, agenda_id))
    conn.commit()
    conn.close()


def delete_agenda(agenda_id):
    conn = get_connection()
    conn.execute("DELETE FROM agenda WHERE id = ?", (agenda_id,))
    conn.commit()
    conn.close()


# ---------- ATTENDANCE ----------
def set_meeting_attendance(meeting_id, student_ids, guest_names=None):
    conn = get_connection()
    conn.execute(
        "DELETE FROM attendance WHERE meeting_id = ?", (meeting_id,))
    for sid in student_ids:
        conn.execute(
            "INSERT INTO attendance (meeting_id, student_id, attended) "
            "VALUES (?, ?, 1)", (meeting_id, sid))
    if guest_names:
        for name in guest_names:
            if name and name.strip():
                conn.execute(
                    "INSERT INTO attendance (meeting_id, guest_name, "
                    "attended) VALUES (?, ?, 1)",
                    (meeting_id, name.strip()))
    conn.commit()
    conn.close()


def get_meeting_attendance(meeting_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT a.*, s.full_name, s.reg_number, "
        "COALESCE(s.full_name, a.guest_name) AS display_name "
        "FROM attendance a "
        "LEFT JOIN students s ON a.student_id = s.id "
        "WHERE a.meeting_id = ? AND a.attended = 1 "
        "ORDER BY display_name", (meeting_id,)).fetchall()
    conn.close()
    return rows


# ============================================================
# REPORTS
# ============================================================

def create_report(rtype, period_from, period_to, meeting_id, author_id,
                   achievements="", challenges="", recommendations="",
                   conclusion=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reports (type, period_from, period_to, meeting_id, "
        "author_id, achievements, challenges, recommendations, conclusion, "
        "status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')",
        (rtype, period_from, period_to, meeting_id, author_id,
         achievements, challenges, recommendations, conclusion))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def update_report(report_id, rtype, period_from, period_to, meeting_id,
                   author_id, achievements, challenges, recommendations,
                   conclusion):
    conn = get_connection()
    conn.execute(
        "UPDATE reports SET type=?, period_from=?, period_to=?, "
        "meeting_id=?, author_id=?, achievements=?, challenges=?, "
        "recommendations=?, conclusion=? WHERE id=?",
        (rtype, period_from, period_to, meeting_id, author_id,
         achievements, challenges, recommendations, conclusion, report_id))
    conn.commit()
    conn.close()


def publish_report(report_id):
    conn = get_connection()
    conn.execute(
        "UPDATE reports SET status = 'published' WHERE id = ?",
        (report_id,))
    conn.commit()
    conn.close()


def delete_report(report_id):
    conn = get_connection()
    conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()


def get_all_reports():
    conn = get_connection()
    rows = conn.execute(
        "SELECT r.*, s.full_name AS author_name, "
        "m.title AS meeting_title FROM reports r "
        "LEFT JOIN students s ON r.author_id = s.id "
        "LEFT JOIN meetings m ON r.meeting_id = m.id "
        "ORDER BY r.created_at DESC").fetchall()
    conn.close()
    return rows


def get_report(report_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT r.*, s.full_name AS author_name, "
        "m.title AS meeting_title FROM reports r "
        "LEFT JOIN students s ON r.author_id = s.id "
        "LEFT JOIN meetings m ON r.meeting_id = m.id "
        "WHERE r.id = ?", (report_id,)).fetchone()
    conn.close()
    return row


def get_report_stats():
    conn = get_connection()
    stats = {
        "students": conn.execute(
            "SELECT COUNT(*) FROM students WHERE is_active = 1"
        ).fetchone()[0],
        "approved": conn.execute(
            "SELECT COUNT(*) FROM students WHERE membership_status = "
            "'approved'").fetchone()[0],
        "meetings": conn.execute(
            "SELECT COUNT(*) FROM meetings").fetchone()[0],
        "assignments": conn.execute(
            "SELECT COUNT(*) FROM assignments").fetchone()[0],
        "exams": conn.execute(
            "SELECT COUNT(*) FROM exams").fetchone()[0],
    }
    conn.close()
    return stats


# ============================================================
# LETTERS
# ============================================================

def create_letter(reference_no, ldate, ltype, recipient, address,
                   subject, body, closing, sender_id, sender_position=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO letters (reference_no, date, type, recipient, "
        "address, subject, body, closing, sender_id, sender_position, "
        "status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')",
        (reference_no, ldate, ltype, recipient, address, subject, body,
         closing, sender_id, sender_position))
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid


def update_letter(letter_id, reference_no, ldate, ltype, recipient,
                   address, subject, body, closing, sender_id,
                   sender_position=""):
    conn = get_connection()
    conn.execute(
        "UPDATE letters SET reference_no=?, date=?, type=?, recipient=?, "
        "address=?, subject=?, body=?, closing=?, sender_id=?, "
        "sender_position=? WHERE id=?",
        (reference_no, ldate, ltype, recipient, address, subject, body,
         closing, sender_id, sender_position, letter_id))
    conn.commit()
    conn.close()


def publish_letter(letter_id):
    conn = get_connection()
    conn.execute(
        "UPDATE letters SET status = 'published' WHERE id = ?",
        (letter_id,))
    conn.commit()
    conn.close()


def delete_letter(letter_id):
    conn = get_connection()
    conn.execute("DELETE FROM letters WHERE id = ?", (letter_id,))
    conn.commit()
    conn.close()


def get_all_letters():
    conn = get_connection()
    rows = conn.execute(
        "SELECT l.*, s.full_name AS sender_name FROM letters l "
        "LEFT JOIN students s ON l.sender_id = s.id "
        "ORDER BY l.created_at DESC").fetchall()
    conn.close()
    return rows


def get_letter(letter_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT l.*, s.full_name AS sender_name FROM letters l "
        "LEFT JOIN students s ON l.sender_id = s.id WHERE l.id = ?",
        (letter_id,)).fetchone()
    conn.close()
    return row
# ============================================================
# DASHBOARD
# ============================================================

def get_upcoming_sessions(limit=5, only_published=True):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    sql = (
        "SELECT s.*, t.title AS topic_title, m.name AS module_name, "
        "m.code AS module_code, te.full_name AS teacher_name "
        "FROM sessions s "
        "JOIN topics t ON s.topic_id = t.id "
        "JOIN module_offerings o ON t.offering_id = o.id "
        "JOIN modules m ON o.module_id = m.id "
        "LEFT JOIN teachers te ON o.teacher_id = te.id "
        "WHERE s.planned_date >= ?"
    )
    params = [today]
    if only_published:
        sql += " AND o.is_published = 1"
    sql += " ORDER BY s.planned_date, s.start_time LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_upcoming_exams(limit=5):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        "SELECT e.*, m.name AS module_name, m.code AS module_code "
        "FROM exams e JOIN modules m ON e.module_id = m.id "
        "WHERE e.date >= ? AND e.status = 'published' "
        "ORDER BY e.date, e.start_time LIMIT ?",
        (today, limit)).fetchall()
    conn.close()
    return rows


def get_recent_announcements(limit=3):
    conn = get_connection()
    rows = conn.execute(
        "SELECT a.*, s.full_name AS author_name "
        "FROM announcements a "
        "LEFT JOIN students s ON a.author_id = s.id "
        "ORDER BY a.created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def get_pending_students_count():
    conn = get_connection()
    n = conn.execute(
        "SELECT COUNT(*) FROM students WHERE membership_status = "
        "'pending' AND is_active = 1").fetchone()[0]
    conn.close()
    return n


def get_teacher_stats(teacher_id):
    conn = get_connection()
    modules = conn.execute(
        "SELECT COUNT(*) FROM module_offerings WHERE teacher_id = ?",
        (teacher_id,)).fetchone()[0]
    assignments = conn.execute(
        "SELECT COUNT(*) FROM assignments WHERE teacher_id = ?",
        (teacher_id,)).fetchone()[0]
    pending_grading = conn.execute(
        "SELECT COUNT(*) FROM submissions s "
        "JOIN assignments a ON s.assignment_id = a.id "
        "WHERE a.teacher_id = ? AND s.score IS NULL",
        (teacher_id,)).fetchone()[0]
    students = conn.execute(
        "SELECT COUNT(*) FROM students WHERE is_active = 1 AND "
        "membership_status = 'approved'").fetchone()[0]
    conn.close()
    return {
        "modules": modules,
        "assignments": assignments,
        "pending_grading": pending_grading,
        "students": students,
    }


def get_student_dashboard_stats(student_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    modules = conn.execute(
        "SELECT COUNT(DISTINCT o.id) FROM module_offerings o "
        "WHERE o.is_published = 1").fetchone()[0]
    pending_assign = conn.execute(
        "SELECT COUNT(*) FROM assignments a "
        "WHERE a.status = 'published' AND a.due_date >= ? "
        "AND NOT EXISTS (SELECT 1 FROM submissions s WHERE "
        "s.assignment_id = a.id AND s.student_id = ?)",
        (today, student_id)).fetchone()[0]
    exams = conn.execute(
        "SELECT COUNT(*) FROM exams WHERE date >= ? AND "
        "status = 'published'", (today,)).fetchone()[0]
    attended = conn.execute(
        "SELECT COUNT(*) FROM class_attendance WHERE student_id = ? "
        "AND status = 'present'", (student_id,)).fetchone()[0]
    eligible = conn.execute(
        "SELECT COUNT(*) FROM class_attendance WHERE student_id = ? "
        "AND status != 'excused'", (student_id,)).fetchone()[0]
    conn.close()
    attendance_pct = (
        round(attended / eligible * 100) if eligible > 0 else 0)
    return {
        "modules": modules,
        "pending_assignments": pending_assign,
        "exams": exams,
        "attendance": attendance_pct,
    }


def get_cr_dashboard_stats():
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) FROM students WHERE is_active = 1"
    ).fetchone()[0]
    approved = conn.execute(
        "SELECT COUNT(*) FROM students WHERE membership_status = "
        "'approved' AND is_active = 1").fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM students WHERE membership_status = "
        "'pending' AND is_active = 1").fetchone()[0]
    groups = conn.execute(
        "SELECT COUNT(*) FROM groups").fetchone()[0]
    conn.close()
    return {
        "total_students": total,
        "approved": approved,
        "pending": pending,
        "groups": groups,
    }
# ============================================================
# DAILY MESSAGES (from CR)
# ============================================================

def create_daily_message(message_text, author_id, publish_date,
                          expires_date=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO daily_messages (message_text, author_id, "
        "publish_date, expires_date, is_active) "
        "VALUES (?, ?, ?, ?, 1)",
        (message_text, author_id, publish_date, expires_date))
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return mid


def get_active_daily_message():
    """Get today's active message."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    row = conn.execute(
        "SELECT d.*, s.full_name AS author_name "
        "FROM daily_messages d "
        "LEFT JOIN students s ON d.author_id = s.id "
        "WHERE d.is_active = 1 AND d.publish_date <= ? "
        "AND (d.expires_date = '' OR d.expires_date IS NULL "
        "     OR d.expires_date >= ?) "
        "ORDER BY d.publish_date DESC, d.id DESC LIMIT 1",
        (today, today)).fetchone()
    conn.close()
    return row


def get_daily_messages_history(limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT d.*, s.full_name AS author_name "
        "FROM daily_messages d "
        "LEFT JOIN students s ON d.author_id = s.id "
        "ORDER BY d.publish_date DESC, d.id DESC LIMIT ?",
        (limit,)).fetchall()
    conn.close()
    return rows


def deactivate_daily_message(message_id):
    conn = get_connection()
    conn.execute(
        "UPDATE daily_messages SET is_active = 0 WHERE id = ?",
        (message_id,))
    conn.commit()
    conn.close()


def delete_daily_message(message_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM daily_messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
# ============================================================
# ATTENDANCE MANAGEMENT
# ============================================================

def create_or_get_class_session(session_date, module_id, session_type="Regular",
                                 start_time="", end_time="", notes="",
                                 created_by=None):
    """Create or find existing session for the same date+module+type."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM class_sessions WHERE session_date = ? AND "
        "COALESCE(module_id, 0) = COALESCE(?, 0) AND session_type = ?",
        (session_date, module_id, session_type)).fetchone()

    if existing:
        conn.close()
        return existing["id"], False  # (id, was_new)

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO class_sessions (session_date, module_id, session_type, "
        "start_time, end_time, notes, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session_date, module_id, session_type, start_time, end_time,
         notes, created_by))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid, True


def get_class_sessions(limit=100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT cs.*, m.name AS module_name, m.code AS module_code, "
        "u.username AS created_by_name, "
        "(SELECT COUNT(*) FROM class_attendance WHERE session_id = cs.id "
        " AND status = 'present') AS present_count, "
        "(SELECT COUNT(*) FROM class_attendance WHERE session_id = cs.id) "
        " AS total_count "
        "FROM class_sessions cs "
        "LEFT JOIN modules m ON cs.module_id = m.id "
        "LEFT JOIN users u ON cs.created_by = u.id "
        "ORDER BY cs.session_date DESC, cs.id DESC LIMIT ?",
        (limit,)).fetchall()
    conn.close()
    return rows


def get_class_session(session_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT cs.*, m.name AS module_name, m.code AS module_code "
        "FROM class_sessions cs "
        "LEFT JOIN modules m ON cs.module_id = m.id "
        "WHERE cs.id = ?", (session_id,)).fetchone()
    conn.close()
    return row


def delete_class_session(session_id):
    conn = get_connection()
    conn.execute("DELETE FROM class_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def get_session_attendance(session_id):
    """Return {student_id: status} for this session."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT student_id, status FROM class_attendance "
        "WHERE session_id = ?", (session_id,)).fetchall()
    conn.close()
    return {r["student_id"]: r["status"] for r in rows}


def save_class_attendance(session_id, status_dict):
    """
    Save attendance. status_dict = {student_id: 'present'|'absent'|'late'|'excused'}.
    Removes existing and inserts fresh (safe upsert via delete+insert).
    """
    conn = get_connection()
    conn.execute(
        "DELETE FROM class_attendance WHERE session_id = ?", (session_id,))
    for sid, status in status_dict.items():
        if status in ("present", "absent", "late", "excused"):
            conn.execute(
                "INSERT INTO class_attendance (session_id, student_id, status) "
                "VALUES (?, ?, ?)", (session_id, sid, status))
    conn.commit()
    conn.close()


def get_approved_students():
    """All approved, active students ordered by name."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, full_name, reg_number, phone "
        "FROM students WHERE is_active = 1 "
        "AND membership_status = 'approved' "
        "ORDER BY full_name").fetchall()
    conn.close()
    return rows


def get_student_attendance_stats():
    """Return per-student attendance stats."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT s.id, s.full_name, s.reg_number, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status = 'present') AS present, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status = 'absent') AS absent, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status = 'late') AS late, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status = 'excused') AS excused, "
        "(SELECT COUNT(*) FROM class_attendance ca WHERE "
        " ca.student_id = s.id AND ca.status != 'excused') AS eligible "
        "FROM students s WHERE s.is_active = 1 "
        "AND s.membership_status = 'approved' "
        "ORDER BY s.full_name").fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        if d["eligible"] > 0:
            d["attendance_pct"] = round(
                d["present"] / d["eligible"] * 100, 1)
        else:
            d["attendance_pct"] = None
        result.append(d)
    return result


def get_student_own_attendance(student_id):
    """Student's own attendance history."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT ca.status, cs.session_date, cs.session_type, "
        "m.name AS module_name, m.code AS module_code "
        "FROM class_attendance ca "
        "JOIN class_sessions cs ON ca.session_id = cs.id "
        "LEFT JOIN modules m ON cs.module_id = m.id "
        "WHERE ca.student_id = ? "
        "ORDER BY cs.session_date DESC", (student_id,)).fetchall()
    conn.close()
    return rows


def get_class_attendance_summary():
    """Aggregate stats for whole class."""
    conn = get_connection()
    total_sessions = conn.execute(
        "SELECT COUNT(*) FROM class_sessions").fetchone()[0]
    total_records = conn.execute(
        "SELECT COUNT(*) FROM class_attendance").fetchone()[0]
    present_count = conn.execute(
        "SELECT COUNT(*) FROM class_attendance WHERE status = 'present'"
    ).fetchone()[0]
    conn.close()

    avg_pct = (
        round(present_count / total_records * 100, 1)
        if total_records > 0 else 0)

    return {
        "total_sessions": total_sessions,
        "total_records": total_records,
        "present_count": present_count,
        "avg_attendance": avg_pct,
    }
def get_teacher_by_user(user_id):
    """Get teacher record for a LECTURER user."""
    if not user_id:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT t.* FROM teachers t "
        "JOIN users u ON u.teacher_id = t.id "
        "WHERE u.id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return row
def verify_student_code(admission_no, code):
    """Verify a student's code. Returns (ok, message)."""
    from datetime import datetime

    admission_no = (admission_no or "").strip().upper()
    code = (code or "").strip()

    print(f"[VERIFY] attempt: user={admission_no!r}, code={code!r}")

    if not admission_no or not code:
        return False, "Username and code are required."

    conn = get_connection()
    student = conn.execute(
        "SELECT id, is_verified, verification_code, "
        "verification_expires_at, full_name, email FROM students "
        "WHERE LOWER(reg_number) = LOWER(?)",
        (admission_no,)
    ).fetchone()

    if not student:
        conn.close()
        print(f"[VERIFY] user NOT found")
        return False, "Account not found."

    saved_code = student["verification_code"]
    print(f"[VERIFY] saved_code={saved_code!r}, is_verified={student['is_verified']}")

    if student["is_verified"]:
        conn.close()
        return False, "Account is already verified. Please login."

    if not saved_code:
        conn.close()
        return False, "No verification code on file. Please click 'Resend Code'."

    expires_str = student["verification_expires_at"]
    if expires_str:
        try:
            exp = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.utcnow()
            print(f"[VERIFY] expires={exp}, now={now}, expired={now > exp}")
            if now > exp:
                conn.close()
                return False, "Code has expired. Please click 'Resend Code' for a new one."
        except ValueError as e:
            print(f"[VERIFY] expiry parse error: {e}")

    if saved_code.strip() != code:
        conn.close()
        print(f"[VERIFY] MISMATCH: saved={saved_code!r}, entered={code!r}")
        return False, "Incorrect code. Please try again."

    # SUCCESS
    conn.execute(
        "UPDATE students SET is_verified = 1, membership_status = 'approved', "
        "verification_code = NULL, verification_expires_at = NULL "
        "WHERE id = ?", (student["id"],))
    conn.commit()
    conn.close()
    print(f"[VERIFY] SUCCESS for {admission_no}")
    return True, "Account verified successfully! You can now log in."
def resend_verification_code(admission_no):
    """Generate new code and return it. Returns (ok, info, message)."""
    from datetime import datetime, timedelta
    import random

    admission_no = (admission_no or "").strip().upper()
    conn = get_connection()
    student = conn.execute(
        "SELECT id, is_verified, full_name, email FROM students "
        "WHERE LOWER(reg_number) = LOWER(?)",
        (admission_no,)
    ).fetchone()

    if not student:
        conn.close()
        return False, None, "Account not found."

    if student["is_verified"]:
        conn.close()
        return False, None, "Account is already verified."

    if not student["email"]:
        conn.close()
        return False, None, "No email on file. Cannot resend."

    code = f"{random.randint(100000, 999999)}"
    expires_at = (datetime.utcnow() + timedelta(minutes=15)).strftime(
        "%Y-%m-%d %H:%M:%S")

    conn.execute(
        "UPDATE students SET verification_code = ?, "
        "verification_expires_at = ? WHERE id = ?",
        (code, expires_at, student["id"]))
    conn.commit()
    conn.close()

    info = {
        "student_id": student["id"],
        "code": code,
        "email": student["email"],
        "full_name": student["full_name"],
    }
    return True, info, "New code sent."
# ============================================================
# TIMETABLE (Standalone - CR Managed)
# ============================================================
def add_timetable_entry(day, start_time, end_time, module_id, teacher_id, venue, notes="", session_name=""):
    conn = get_connection()
    cur = conn.cursor()
    # Ensure session_name column exists
    cur.execute("PRAGMA table_info(timetable)")
    cols = [r[1] for r in cur.fetchall()]
    if "session_name" not in cols:
        try:
            cur.execute("ALTER TABLE timetable ADD COLUMN session_name TEXT")
        except Exception:
            pass
    cur.execute(
        "INSERT INTO timetable (day, start_time, end_time, module_id, teacher_id, venue, notes, session_name) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (day, start_time, end_time, module_id, teacher_id, venue, notes, session_name))
    conn.commit()
    entry_id = cur.lastrowid
    conn.close()
    return entry_id
def get_all_timetable_entries():
    conn = get_connection()
    # Ensure session_name exists
    conn.execute("PRAGMA table_info(timetable)")
    rows = conn.execute(
        "SELECT t.*, m.name AS module_name, m.code AS module_code, "
        "te.full_name AS teacher_name, te.phone AS teacher_phone, te.email AS teacher_email, m.description AS module_desc "
        "FROM timetable t "
        "LEFT JOIN modules m ON t.module_id = m.id "
        "LEFT JOIN teachers te ON t.teacher_id = te.id "
        "ORDER BY "
        "CASE t.day "
        "  WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 "
        "  WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 "
        "  WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 "
        "  WHEN 'Sunday' THEN 7 END, "
        "t.start_time").fetchall()
    conn.close()
    return rows

def get_timetable_grouped_by_day():
    rows = get_all_timetable_entries()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    grouped = {d: [] for d in days}
    for r in rows:
        if r["day"] in grouped:
            grouped[r["day"]].append(dict(r))
    return grouped


def get_timetable_entry(entry_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM timetable WHERE id = ?", (entry_id,)).fetchone()
    conn.close()
    return row


def update_timetable_entry(entry_id, day, start_time, end_time, module_id, teacher_id, venue, notes=""):
    conn = get_connection()
    conn.execute(
        "UPDATE timetable SET day = ?, start_time = ?, end_time = ?, "
        "module_id = ?, teacher_id = ?, venue = ?, notes = ? WHERE id = ?",
        (day, start_time, end_time, module_id, teacher_id, venue, notes, entry_id))
    conn.commit()
    conn.close()


def delete_timetable_entry(entry_id):
    conn = get_connection()
    conn.execute("DELETE FROM timetable WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
if __name__ == "__main__":
    init_database()
    print(f"Database: {DB_PATH}")


# ============================================================
# LECTURER MANAGEMENT (CR)
# ============================================================
# ============================================================
# SESSION ATTENDANCE MIGRATION
# ============================================================
def migrate_attendance_system():
    """Add timetable_id, status, conducted_at to class_sessions."""
    conn = get_connection()
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(class_sessions)").fetchall()]
    
    if "timetable_id" not in cols:
        try: cur.execute("ALTER TABLE class_sessions ADD COLUMN timetable_id INTEGER")
        except: pass
    if "status" not in cols:
        try: cur.execute("ALTER TABLE class_sessions ADD COLUMN status TEXT DEFAULT 'scheduled'")
        except: pass
    if "conducted_at" not in cols:
        try: cur.execute("ALTER TABLE class_sessions ADD COLUMN conducted_at TEXT")
        except: pass
    
    conn.commit()
    conn.close()


def get_todays_timetable_with_status(user_id):
    """Get today's timetable with linked session status (if CR already started)."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().strftime("%A")
    
    conn = get_connection()
    rows = conn.execute(
        "SELECT t.*, m.name AS module_name, m.code AS module_code, "
        "te.full_name AS teacher_name, "
        "cs.id AS session_id, cs.status AS session_status, cs.conducted_at "
        "FROM timetable t "
        "LEFT JOIN modules m ON t.module_id = m.id "
        "LEFT JOIN teachers te ON t.teacher_id = te.id "
        "LEFT JOIN class_sessions cs ON cs.timetable_id = t.id AND cs.session_date = ? "
        "WHERE t.day = ? "
        "ORDER BY t.start_time", (today, weekday)).fetchall()
    conn.close()
    return rows


def get_or_create_session_from_timetable(timetable_id, session_date, created_by):
    """Create or find class_session for a timetable entry on a specific date."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT id, status FROM class_sessions WHERE timetable_id = ? AND session_date = ?",
        (timetable_id, session_date)).fetchone()
    if existing:
        conn.close()
        return existing["id"], existing["status"], False
    
    t = conn.execute("SELECT * FROM timetable WHERE id = ?", (timetable_id,)).fetchone()
    if not t:
        conn.close()
        return None, None, False
    
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO class_sessions (session_date, module_id, session_type, "
        "start_time, end_time, notes, created_by, timetable_id, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'scheduled')",
        (session_date, t["module_id"], t["session_name"] or "Regular",
         t["start_time"], t["end_time"], t["notes"], created_by, timetable_id))
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid, "scheduled", True


def get_session_with_attendance(session_id):
    """Get session + attendance records."""
    conn = get_connection()
    session = conn.execute(
        "SELECT cs.*, m.name AS module_name, m.code AS module_code, "
        "t.session_name AS timetable_name, te.full_name AS teacher_name "
        "FROM class_sessions cs "
        "LEFT JOIN modules m ON cs.module_id = m.id "
        "LEFT JOIN timetable t ON cs.timetable_id = t.id "
        "LEFT JOIN teachers te ON t.teacher_id = te.id "
        "WHERE cs.id = ?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return None
    attendance = conn.execute(
        "SELECT ca.*, s.full_name, s.reg_number FROM class_attendance ca "
        "JOIN students s ON ca.student_id = s.id "
        "WHERE ca.session_id = ? ORDER BY s.full_name", (session_id,)).fetchall()
    conn.close()
    return {"session": dict(session), "attendance": [dict(a) for a in attendance]}


def update_session_status(session_id, status):
    conn = get_connection()
    if status == "conducted":
        conn.execute(
            "UPDATE class_sessions SET status = ?, conducted_at = datetime('now','localtime') WHERE id = ?",
            (status, session_id))
    else:
        conn.execute("UPDATE class_sessions SET status = ? WHERE id = ?", (status, session_id))
    conn.commit()
    conn.close()


def get_student_session_attendance(student_id, limit=100):
    """Student's attendance with session + timetable details."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT ca.status AS attendance_status, ca.notes AS attendance_notes, "
        "cs.session_date, cs.session_type, cs.status AS session_status, cs.start_time, cs.end_time, "
        "m.name AS module_name, m.code AS module_code, "
        "t.session_name AS timetable_name, t.venue, te.full_name AS teacher_name "
        "FROM class_attendance ca "
        "JOIN class_sessions cs ON ca.session_id = cs.id "
        "LEFT JOIN modules m ON cs.module_id = m.id "
        "LEFT JOIN timetable t ON cs.timetable_id = t.id "
        "LEFT JOIN teachers te ON t.teacher_id = te.id "
        "WHERE ca.student_id = ? "
        "ORDER BY cs.session_date DESC, cs.id DESC LIMIT ?",
        (student_id, limit)).fetchall()
    conn.close()
    return rows


# ============================================================
# CR MANAGEMENT (create, list, delete)
# ============================================================
def create_cr_account(username, password, full_name, phone, email=""):
    """Create a new CR user. Returns (ok, message)."""
    import hashlib, os
    username = (username or "").strip()
    if not username:
        return False, "Username is required."
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters."
    if not full_name or not full_name.strip():
        return False, "Full name is required."
    if not phone or not phone.strip():
        return False, "Phone is required."

    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM users WHERE LOWER(username) = LOWER(?)",
        (username,)).fetchone()
    if existing:
        conn.close()
        return False, f"Username '{username}' already exists."

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (full_name, reg_number, phone, email, "
        "is_active, membership_status, is_verified, date_joined) "
        "VALUES (?, ?, ?, ?, 1, 'approved', 1, date('now'))",
        (full_name.strip(), username.upper(), phone.strip(),
         (email or "").strip() or None))
    student_id = cur.lastrowid

    salt = os.urandom(16).hex()
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    cur.execute(
        "INSERT INTO users (role, student_id, username, password_hash, "
        "salt, is_admin) VALUES (?, ?, ?, ?, ?, 1)",
        ("CR", student_id, username, pwd_hash, salt))
    conn.commit()
    conn.close()
    return True, f"CR '{username}' created successfully."


def get_all_crs():
    """Return all CR users."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT u.id, u.username, s.full_name, s.phone, s.email, s.date_joined "
        "FROM users u LEFT JOIN students s ON u.student_id = s.id "
        "WHERE u.role = 'CR' ORDER BY u.username").fetchall()
    conn.close()
    return rows


def delete_cr_user(user_id):
    """Delete a CR (not 'cr' primary). Returns (ok, message)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT username, student_id FROM users WHERE id = ? AND role = 'CR'",
        (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, "User not found."
    if row["username"] == "cr":
        conn.close()
        return False, "Cannot delete primary 'cr' account."
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    if row["student_id"]:
        conn.execute("DELETE FROM students WHERE id = ?", (row["student_id"],))
    conn.commit()
    conn.close()
    return True, "CR deleted."


# ============================================================
# LECTURER MANAGEMENT (verify + add if missing)
# ============================================================
def get_teacher(teacher_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,)).fetchone()
    conn.close()
    return row


def update_teacher(teacher_id, full_name, phone="", email="", notes=""):
    conn = get_connection()
    conn.execute(
        "UPDATE teachers SET full_name = ?, phone = ?, email = ?, notes = ? WHERE id = ?",
        (full_name, phone, email, notes, teacher_id))
    conn.commit()
    conn.close()


def delete_teacher(teacher_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as n FROM modules WHERE teacher_id = ?", (teacher_id,)).fetchone()
    if row and row["n"] > 0:
        conn.close()
        return False, f"Teacher ana modules {row['n']}. Reassign kwanza."
    conn.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
    conn.commit()
    conn.close()
    return True, "Deleted"


# ============================================================
# CR PROMOTION (promote students to CR, demote back)
# ============================================================
def promote_student_to_cr(student_id):
    """Promote an existing approved student to CR. Returns (ok, message)."""
    conn = get_connection()
    student = conn.execute(
        "SELECT s.id, s.full_name, s.reg_number, u.id AS user_id, u.role "
        "FROM students s JOIN users u ON u.student_id = s.id "
        "WHERE s.id = ?", (student_id,)).fetchone()
    if not student:
        conn.close()
        return False, "Student hana account ya user."
    if student["role"] == "CR":
        conn.close()
        return False, f"{student['full_name']} ni CR tayari."
    if student["role"] != "STUDENT":
        conn.close()
        return False, f"Role ya {student['full_name']} si STUDENT."
    conn.execute("UPDATE users SET role = 'CR', is_admin = 1 WHERE id = ?",
                 (student["user_id"],))
    conn.commit()
    conn.close()
    return True, f"{student['full_name']} amepandishwa kuwa CR (anaweza kuingia kwa student credentials zake)."


def demote_cr_to_student(user_id):
    """Demote CR back to student. Returns (ok, message)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT username, student_id FROM users WHERE id = ? AND role = 'CR'",
        (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, "CR haipo."
    if row["username"] == "cr":
        conn.close()
        return False, "Primary 'cr' haipaswi ku-demote. Tumia 'Delete' (kama kuna CR mwingine)."
    conn.execute("UPDATE users SET role = 'STUDENT', is_admin = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True, "CR imerudishwa kuwa student (anaendelea kusoma)."


def get_students_eligible_for_cr():
    """Students approved, with account, not CRs yet."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT s.id AS student_id, s.full_name, s.reg_number, s.phone, "
        "s.email, u.username "
        "FROM students s JOIN users u ON u.student_id = s.id "
        "WHERE u.role = 'STUDENT' AND s.is_active = 1 "
        "AND s.membership_status = 'approved' "
        "ORDER BY s.full_name").fetchall()
    conn.close()
    return rows


def get_all_crs_with_student_info():
    """All CRs with their linked student info (they are students too)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT u.id AS user_id, u.username, "
        "s.id AS student_id, s.full_name, s.reg_number, s.phone, s.email, "
        "s.membership_status, s.date_joined "
        "FROM users u LEFT JOIN students s ON u.student_id = s.id "
        "WHERE u.role = 'CR' ORDER BY (u.username = 'cr') DESC, u.username").fetchall()
    conn.close()
    return rows


def delete_cr_with_safety(user_id):
    """Delete CR. If primary 'cr', require another CR exists."""
    conn = get_connection()
    row = conn.execute(
        "SELECT username, student_id FROM users WHERE id = ? AND role = 'CR'",
        (user_id,)).fetchone()
    if not row:
        conn.close()
        return False, "CR haipo."
    if row["username"] == "cr":
        # Must have at least 2 CRs (one other besides primary)
        count = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'CR'").fetchone()[0]
        if count < 2:
            conn.close()
            return False, "Huwezi kufuta 'cr' ukiwa CR pekee. Promote student kuwa CR kwanza."
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    if row["student_id"]:
        conn.execute("DELETE FROM students WHERE id = ?", (row["student_id"],))
    conn.commit()
    conn.close()
    return True, f"CR '{row['username']}' imefutwa."


# ============================================================
# TIMETABLE: Postpone/Cancel support
# ============================================================
def migrate_timetable_status():
    """Add status, postponed_to, postponed_reason, postponed_at to timetable."""
    conn = get_connection()
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(timetable)").fetchall()]
    
    for col_name, col_type in [
        ("status", "TEXT DEFAULT 'scheduled'"),
        ("postponed_to", "TEXT"),
        ("postponed_reason", "TEXT"),
        ("postponed_at", "TEXT"),
    ]:
        if col_name not in cols:
            try:
                cur.execute(f"ALTER TABLE timetable ADD COLUMN {col_name} {col_type}")
                print(f"✅ timetable.{col_name} added")
            except Exception as e:
                print(f"⚠️ {col_name}: {e}")
    
    conn.commit()
    conn.close()


def postpone_timetable_entry(entry_id, postponed_to, reason=""):
    """Mark timetable entry as postponed with new date/time suggestion."""
    from datetime import datetime
    conn = get_connection()
    conn.execute(
        "UPDATE timetable SET status = 'postponed', postponed_to = ?, "
        "postponed_reason = ?, postponed_at = datetime('now','localtime') WHERE id = ?",
        (postponed_to, reason, entry_id))
    conn.commit()
    conn.close()


def restore_timetable_entry(entry_id):
    """Restore postponed/cancelled timetable entry back to scheduled."""
    conn = get_connection()
    conn.execute(
        "UPDATE timetable SET status = 'scheduled', postponed_to = NULL, "
        "postponed_reason = NULL, postponed_at = NULL WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def cancel_timetable_entry(entry_id, reason=""):
    """Mark timetable entry as cancelled."""
    conn = get_connection()
    conn.execute(
        "UPDATE timetable SET status = 'cancelled', postponed_reason = ?, "
        "postponed_at = datetime('now','localtime') WHERE id = ?",
        (reason, entry_id))
    conn.commit()
    conn.close()


def get_all_modules_for_timetable():
    """All modules with teacher info for dropdown."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT m.id, m.name, m.code, m.teacher_id, "
        "t.full_name AS teacher_name, t.phone AS teacher_phone "
        "FROM modules m LEFT JOIN teachers t ON m.teacher_id = t.id "
        "ORDER BY m.name").fetchall()
    conn.close()
    return rows


# ============================================================
# SEED MODULE CLEANUP (remove unused samples)
# ============================================================
SEED_MODULE_NAMES = [
    "Programming in Java",
    "Programming in Python",
    "Database Management Systems",
    "Computer Networking",
    "Web Technologies",
    "Computer Hardware",
    "Software Engineering",
    "System Analysis & Design",
    "ICT Ethics & Law",
    "Mathematics for ICT",
    "Business Communication",
    "Final Year Project",
]


def cleanup_unused_seed_modules():
    """Delete seed modules that have NO offerings. Returns (deleted_count, kept_count)."""
    conn = get_connection()
    deleted = 0
    kept = 0
    try:
        for name in SEED_MODULE_NAMES:
            row = conn.execute(
                "SELECT id FROM modules WHERE name = ?", (name,)).fetchone()
            if not row:
                continue
            mid = row["id"]
            # Check if used by any offering
            usage = conn.execute(
                "SELECT COUNT(*) as n FROM module_offerings WHERE module_id = ?",
                (mid,)).fetchone()
            count = usage["n"] if usage else 0
            if count == 0:
                conn.execute("DELETE FROM modules WHERE id = ?", (mid,))
                deleted += 1
                print(f"🗑 Deleted unused seed: {name}")
            else:
                kept += 1
                print(f"✓ Kept (in use): {name} ({count} offering(s))")
        conn.commit()
    finally:
        conn.close()
    return deleted, kept


# ============================================================
# LESSON MATERIALS (Base64 in DB — works on Render)
# ============================================================
def init_materials_table():
    """Create lesson_materials table."""
    conn = get_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS lesson_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offering_id INTEGER NOT NULL,
        topic_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        file_name TEXT,
        file_type TEXT,
        file_size INTEGER DEFAULT 0,
        file_content TEXT,
        uploaded_by INTEGER,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    conn.commit()
    conn.close()


def add_material(offering_id, topic_id, title, description, file_name,
                 file_type, file_content_b64, uploaded_by):
    """Add material with base64 file content."""
    import base64 as _b64
    size = 0
    try:
        size = len(_b64.b64decode(file_content_b64))
    except Exception:
        pass
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO lesson_materials "
        "(offering_id, topic_id, title, description, file_name, file_type, "
        "file_size, file_content, uploaded_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (offering_id, topic_id, title, description, file_name, file_type,
         size, file_content_b64, uploaded_by))
    conn.commit()
    mid = cur.lastrowid
    conn.close()
    return mid


def get_materials_for_offering(offering_id):
    """Get all materials for a module (with topic names if linked)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT m.*, t.title AS topic_title "
        "FROM lesson_materials m "
        "LEFT JOIN topics t ON m.topic_id = t.id "
        "WHERE m.offering_id = ? "
        "ORDER BY m.created_at DESC", (offering_id,)).fetchall()
    conn.close()
    return rows


def get_material(material_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM lesson_materials WHERE id = ?", (material_id,)).fetchone()
    conn.close()
    return row


def delete_material(material_id):
    conn = get_connection()
    conn.execute("DELETE FROM lesson_materials WHERE id = ?", (material_id,))
    conn.commit()
    conn.close()


def get_material_stats(offering_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) as count, COALESCE(SUM(file_size), 0) as total_size "
        "FROM lesson_materials WHERE offering_id = ?", (offering_id,)).fetchone()
    conn.close()
    return {"count": row["count"] if row else 0, "size": row["total_size"] if row else 0}

# ============================================================
# ADMIN ADD STUDENT + AUTO-GROUPING
# ============================================================
def admin_add_student(full_name, admission_no, phone, email="", gender="", password="it2026"):
    """Admin (CR) adds student directly. No email verification. Returns (ok, msg)."""
    import hashlib
    admission_no = (admission_no or "").strip().upper()
    if not admission_no:
        return False, "Admission number inahitajika"
    if not full_name or not full_name.strip():
        return False, "Jina linahitajika"
    if not password or len(password) < 4:
        return False, "Password ni fupi sana (min 4)"
    
    conn = get_connection()
    if conn.execute("SELECT id FROM students WHERE LOWER(reg_number)=LOWER(?)",
                    (admission_no,)).fetchone():
        conn.close()
        return False, f"Admission {admission_no} tayari imesajiliwa"
    if conn.execute("SELECT id FROM users WHERE LOWER(username)=LOWER(?)",
                    (admission_no,)).fetchone():
        conn.close()
        return False, f"Username {admission_no} tayari upo"
    
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (full_name, reg_number, gender, phone, email, "
        "membership_status, is_active, is_verified, date_joined) "
        "VALUES (?, ?, ?, ?, ?, 'approved', 1, 1, date('now'))",
        (full_name.strip(), admission_no, gender or None,
         (phone or "").strip() or None, (email or "").strip() or None))
    student_id = cur.lastrowid
    
    import os as _os
    salt = _os.urandom(16).hex()
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    cur.execute(
        "INSERT INTO users (role, student_id, username, password_hash, salt, is_admin) "
        "VALUES ('STUDENT', ?, ?, ?, ?, 0)",
        (student_id, admission_no, pwd_hash, salt))
    conn.commit()
    conn.close()
    return True, f"{full_name} ameongezwa (username: {admission_no}, password: {password})"


def get_ungrouped_students():
    """Approved students NOT yet in any group."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT s.* FROM students s "
        "WHERE s.is_active = 1 AND s.membership_status = 'approved' "
        "AND s.id NOT IN (SELECT student_id FROM group_members) "
        "ORDER BY s.gender, s.full_name").fetchall()
    conn.close()
    return rows


def add_group_member(group_id, student_id):
    """Add one student to a group (idempotent)."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO group_members (group_id, student_id) VALUES (?, ?)",
            (group_id, student_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def _is_male(student):
    g = (student["gender"] or "").lower().strip()
    return g in ("male", "m", "me", "mwanaume", "mvulana")


def _is_female(student):
    g = (student["gender"] or "").lower().strip()
    return g in ("female", "f", "ke", "mwanamke", "msichana")


def get_next_group_number():
    """Find next Auto Group number."""
    import re
    conn = get_connection()
    rows = conn.execute(
        "SELECT name FROM groups WHERE name LIKE 'Auto Group%'").fetchall()
    conn.close()
    max_num = 0
    for r in rows:
        m = re.search(r'Auto Group (\d+)', r["name"] or "")
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num + 1


def auto_group_ungrouped_students():
    """Auto-group ungrouped students. Target 10/group, 5M+5F, adjust +/-1 if needed."""
    ungrouped = get_ungrouped_students()
    if not ungrouped:
        return {"ok": True, "created": 0, "groups": [], "remaining": 0,
                "message": "Hakuna wanafunzi wasio kwenye group"}
    
    males = [s for s in ungrouped if _is_male(s)]
    females = [s for s in ungrouped if _is_female(s)]
    others = [s for s in ungrouped if not _is_male(s) and not _is_female(s)]
    
    created_groups = []
    next_num = get_next_group_number()
    
    while True:
        total = len(males) + len(females) + len(others)
        if total < 9:
            break
        
        group_size = 10 if total > 11 else total
        
        # Gender split logic
        if len(males) >= 5 and len(females) >= 5 and group_size >= 10:
            m_take, f_take = 5, 5
        elif len(males) >= 6 and len(females) >= 4 and group_size >= 10:
            m_take, f_take = 6, 4
        elif len(males) >= 4 and len(females) >= 6 and group_size >= 10:
            m_take, f_take = 4, 6
        else:
            half = group_size // 2
            m_take = min(len(males), half)
            f_take = min(len(females), half)
            while m_take + f_take < group_size and m_take < len(males):
                m_take += 1
            while m_take + f_take < group_size and f_take < len(females):
                f_take += 1
        
        u_take = 0
        while m_take + f_take + u_take < group_size and u_take < len(others):
            u_take += 1
        
        batch = males[:m_take] + females[:f_take] + others[:u_take]
        if len(batch) < 9:
            break
        
        gname = "Auto Group " + str(next_num)
        m_count = sum(1 for s in batch if _is_male(s))
        f_count = sum(1 for s in batch if _is_female(s))
        desc = "Auto-generated: " + str(m_count) + "M + " + str(f_count) + "F = " + str(len(batch)) + " members"
        
        group_id = create_group(gname, desc, None)
        for s in batch:
            add_group_member(group_id, s["id"])
        
        created_groups.append({
            "id": group_id, "name": gname,
            "total": len(batch), "male": m_count, "female": f_count,
        })
        
        males = males[m_take:]
        females = females[f_take:]
        others = others[u_take:]
        next_num += 1
    
    return {
        "ok": True,
        "created": len(created_groups),
        "groups": created_groups,
        "remaining": len(males) + len(females) + len(others),
    }

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


# ============================================================
# DELETE STUDENT (safe - removes user + related records)
# ============================================================
def delete_student_full(student_id):
    """Delete a student and their user account + related records safely."""
    conn = get_connection()
    try:
        # Find user_id first
        user_row = conn.execute(
            "SELECT id FROM users WHERE student_id = ?", (student_id,)
        ).fetchone()
        
        # Delete related records (order matters for FK)
        try:
            conn.execute("DELETE FROM group_members WHERE student_id = ?", (student_id,))
        except Exception:
            pass
        
        try:
            conn.execute("DELETE FROM class_attendance WHERE student_id = ?", (student_id,))
        except Exception:
            pass
        
        try:
            conn.execute("DELETE FROM lesson_progress WHERE user_id IN "
                         "(SELECT id FROM users WHERE student_id = ?)", (student_id,))
        except Exception:
            pass
        
        try:
            conn.execute("DELETE FROM push_subscriptions WHERE user_id IN "
                         "(SELECT id FROM users WHERE student_id = ?)", (student_id,))
        except Exception:
            pass
        
        try:
            conn.execute("DELETE FROM notifications WHERE user_id IN "
                         "(SELECT id FROM users WHERE student_id = ?)", (student_id,))
        except Exception:
            pass
        
        try:
            conn.execute("DELETE FROM course_enrolments WHERE user_id IN "
                         "(SELECT id FROM users WHERE student_id = ?)", (student_id,))
        except Exception:
            pass
        
        # Delete user (ON DELETE CASCADE handles most)
        if user_row:
            try:
                conn.execute("DELETE FROM users WHERE id = ?", (user_row["id"],))
            except Exception as e:
                print(f"Delete user failed: {e}")
        
        # Delete student
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        return True, "Mwanafunzi amefutwa kabisa"
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)
    finally:
        conn.close()