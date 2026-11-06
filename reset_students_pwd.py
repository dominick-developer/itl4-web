# reset_students_pwd.py — Reset password to "it2026" for all admin-added students
import hashlib
import os
from database import get_connection

TARGET_PASSWORD = "it2026"

conn = get_connection()
# Get all STUDENT users
rows = conn.execute(
    "SELECT u.id, u.username FROM users u WHERE u.role = 'STUDENT'"
).fetchall()

print(f"Found {len(rows)} STUDENT accounts")
reset_count = 0

for r in rows:
    salt = os.urandom(16).hex()
    pwd_hash = hashlib.sha256((salt + TARGET_PASSWORD).encode("utf-8")).hexdigest()
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
        (pwd_hash, salt, r["id"]))
    reset_count += 1

conn.commit()
conn.close()
print(f"[OK] Reset {reset_count} student password(s) to '{TARGET_PASSWORD}'")
print()
print("Now they can login with:")
print(f"  Username: admission number (case-insensitive)")
print(f"  Password: {TARGET_PASSWORD}")