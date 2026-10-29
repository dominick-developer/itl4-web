# migrate_db.py — Run ONCE after deploy to add verification columns
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "itl4.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    columns = [
        ("is_verified", "INTEGER DEFAULT 0"),
        ("verification_code", "TEXT"),
        ("verification_expires_at", "TEXT"),
    ]

    for name, ctype in columns:
        try:
            cur.execute(f"ALTER TABLE students ADD COLUMN {name} {ctype}")
            print(f"✅ Added column: {name}")
        except sqlite3.OperationalError as e:
            print(f"⚠️  {name}: {e}")

    # Grandfather existing students (so they can still log in)
    cur.execute("UPDATE students SET is_verified = 1")
    print(f"✅ Grandfathered existing students → is_verified = 1")

    conn.commit()
    conn.close()
    print("\n🎉 Migration complete!")


if __name__ == "__main__":
    migrate()