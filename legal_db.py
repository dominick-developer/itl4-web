# legal_db.py — Legal documents and acceptances
from pathlib import Path
from database import get_connection

LEGAL_DIR = Path(__file__).parent / "templates" / "legal"

CURRENT_VERSIONS = {
    "terms": "1.0",
    "privacy": "1.0",
}

DOCUMENT_META = {
    "terms": {
        "title": "Terms & Conditions",
        "slug": "terms-and-conditions",
        "effective": "2026-11-03",
    },
    "privacy": {
        "title": "Privacy Policy",
        "slug": "privacy-policy",
        "effective": "2026-11-03",
    },
}


def init_legal_tables():
    """Create legal tables and seed current documents."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS legal_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_type TEXT NOT NULL,
        title TEXT NOT NULL,
        slug TEXT NOT NULL,
        version TEXT NOT NULL,
        status TEXT DEFAULT 'published',
        effective_at TEXT,
        published_at TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(document_type, version)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS legal_acceptances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        document_id INTEGER NOT NULL,
        document_type TEXT NOT NULL,
        document_version TEXT NOT NULL,
        acceptance_type TEXT DEFAULT 'signup',
        accepted_at TEXT DEFAULT (datetime('now','localtime')),
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS legal_document_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        action TEXT NOT NULL,
        previous_version TEXT,
        new_version TEXT,
        performed_by INTEGER,
        performed_at TEXT DEFAULT (datetime('now','localtime')),
        metadata TEXT
    )""")

    conn.commit()
    _seed_documents(cur)
    conn.commit()
    conn.close()


def _seed_documents(cur):
    """Seed current documents if they don't exist."""
    for doc_type, version in CURRENT_VERSIONS.items():
        existing = cur.execute(
            "SELECT id FROM legal_documents WHERE document_type = ? AND version = ?",
            (doc_type, version)).fetchone()
        if existing:
            continue
        meta = DOCUMENT_META[doc_type]
        cur.execute(
            "INSERT INTO legal_documents (document_type, title, slug, version, "
            "status, effective_at, published_at) VALUES (?, ?, ?, ?, 'published', ?, datetime('now','localtime'))",
            (doc_type, meta["title"], meta["slug"], version, meta["effective"]))
        print(f"✅ Seeded {doc_type} v{version}")


def get_current_document(doc_type):
    """Get current published document metadata."""
    version = CURRENT_VERSIONS.get(doc_type)
    if not version:
        return None
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM legal_documents WHERE document_type = ? AND version = ? AND status = 'published'",
        (doc_type, version)).fetchone()
    conn.close()
    return row


def get_document_content(doc_type, version):
    """Read the HTML file for a document version."""
    filename = f"{doc_type}_v{version}.html"
    path = LEGAL_DIR / filename
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def record_acceptance(user_id, document_id, document_type, document_version,
                       acceptance_type="signup"):
    """Record a legal acceptance (idempotent — updates if exists)."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM legal_acceptances WHERE user_id = ? AND document_id = ?",
            (user_id, document_id)).fetchone()
        if existing:
            conn.execute(
                "UPDATE legal_acceptances SET accepted_at = datetime('now','localtime'), "
                "acceptance_type = ? WHERE id = ?",
                (acceptance_type, existing["id"]))
        else:
            conn.execute(
                "INSERT INTO legal_acceptances (user_id, document_id, document_type, "
                "document_version, acceptance_type) VALUES (?, ?, ?, ?, ?)",
                (user_id, document_id, document_type, document_version, acceptance_type))
        conn.commit()
        return True
    except Exception as e:
        print(f"⚠️ record_acceptance failed: {e}")
        return False
    finally:
        conn.close()


def get_user_acceptances(user_id):
    """Get all legal acceptances for a user."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM legal_acceptances WHERE user_id = ? "
        "ORDER BY accepted_at DESC", (user_id,)).fetchall()
    conn.close()
    return rows


def has_accepted_current(user_id, doc_type):
    """Check if user has accepted the current version of a document."""
    version = CURRENT_VERSIONS.get(doc_type)
    if not version:
        return False
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM legal_acceptances "
        "WHERE user_id = ? AND document_type = ? AND document_version = ?",
        (user_id, doc_type, version)).fetchone()
    conn.close()
    return row is not None