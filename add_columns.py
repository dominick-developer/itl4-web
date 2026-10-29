# add_columns.py — Add missing verification columns to students table
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "itl4.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Get existing columns
existing = [row[1] for row in cur.execute("PRAGMA table_info(students)").fetchall()]
print(f"Existing columns in students: {existing}")
print()

columns_to_add = [
    ("is_verified", "INTEGER DEFAULT 0"),
    ("verification_code", "TEXT"),
    ("verification_expires_at", "TEXT"),
]

for name, ctype in columns_to_add:
    if name in existing:
        print(f"OK  Column '{name}' already exists")
    else:
        try:
            cur.execute(f"ALTER TABLE students ADD COLUMN {name} {ctype}")
            print(f"++  Added column '{name}'")
        except sqlite3.OperationalError as e:
            print(f"!!  Failed to add '{name}': {e}")

# Grandfather existing students so they can still log in
cur.execute("SELECT COUNT(*) FROM students").fetchone()
cur.execute("UPDATE students SET is_verified = 1 WHERE is_verified IS NULL OR is_verified = 0")
print(f"OK  Set is_verified = 1 for existing students")

conn.commit()
conn.close()
print()
print("Done! Now run: python check_db.py")
