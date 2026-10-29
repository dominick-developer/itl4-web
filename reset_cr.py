# reset_cr.py — Set CR password to 123456
import hashlib
import os
from database import get_connection

conn = get_connection()

row = conn.execute(
    "SELECT u.id, u.username, u.student_id FROM users u WHERE u.username = 'cr'"
).fetchone()

if not row:
    print("'cr' user haipo. Inaunda...")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (full_name, reg_number, phone, is_active, "
        "membership_status, date_joined, is_verified) "
        "VALUES (?, ?, ?, 1, 'approved', date('now'), 1)",
        ("Class Representative", "ITL4/CR/001", "0700111111"))
    cr_student_id = cur.lastrowid

    salt = os.urandom(16).hex()
    pwd_hash = hashlib.sha256((salt + "123456").encode()).hexdigest()
    cur.execute(
        "INSERT INTO users (role, student_id, username, password_hash, "
        "salt, is_admin) VALUES (?, ?, ?, ?, ?, 1)",
        ("CR", cr_student_id, "cr", pwd_hash, salt))
    conn.commit()
    print("CR created: cr / 123456")
else:
    salt = os.urandom(16).hex()
    pwd_hash = hashlib.sha256((salt + "123456").encode()).hexdigest()
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
        (pwd_hash, salt, row["id"]))
    conn.commit()
    print("Password reset for 'cr' -> 123456")

conn.close()
