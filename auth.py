"""
auth.py - User authentication
IT LEVEL 4 CONNECT
Roles: CR, LECTURER, STUDENT
"""
import hashlib
import os
from database import get_connection


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def create_account(username, password, role,
                   student_id=None, teacher_id=None, is_admin=0):
    if role not in ("CR", "LECTURER", "STUDENT"):
        return False, "Invalid role."
    if role in ("CR", "STUDENT") and not student_id:
        return False, "Student ID required for CR/STUDENT role."
    if role == "LECTURER" and not teacher_id:
        return False, "Teacher ID required for LECTURER role."

    salt = os.urandom(16).hex()
    pwd_hash = _hash_password(password, salt)
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (role, student_id, teacher_id, username, "
            "password_hash, salt, is_admin) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (role, student_id, teacher_id, username, pwd_hash, salt, is_admin)
        )
        conn.commit()
        return True, "Account created successfully."
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()


def login(username: str, password: str):
    """
    Verify login (no role needed — system detects from username).
    Returns (True, user_dict) on success.
    Returns (False, message_string) on failure.
    Returns (False, {"verify_needed": True, "username": ...}) if verify needed.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT u.*, "
        "COALESCE(s.full_name, t.full_name) AS full_name, "
        "COALESCE(s.phone, t.phone) AS phone, "
        "s.membership_status AS membership_status, "
        "s.is_verified AS is_verified "
        "FROM users u "
        "LEFT JOIN students s ON u.student_id = s.id "
        "LEFT JOIN teachers t ON u.teacher_id = t.id "
        "WHERE u.username = ?",
        (username,)
    ).fetchone()

    if not row:
        conn.close()
        return False, "No user with this username."

    if _hash_password(password, row["salt"]) != row["password_hash"]:
        conn.close()
        return False, "Incorrect password."

    role = row["role"]

    # Verification check for STUDENT and CR
    if role in ("STUDENT", "CR"):
        is_verified = row["is_verified"] if row["is_verified"] is not None else 1
        if not is_verified:
            conn.close()
            return False, {
                "verify_needed": True,
                "username": username,
                "message": "Please verify your email first.",
            }

    # Membership status for STUDENT only
    if role == "STUDENT":
        status = row["membership_status"]
        if status == "pending":
            conn.close()
            return False, "Your account is pending approval. Please wait."
        elif status == "rejected":
            conn.close()
            return False, "Your account was rejected."
        elif status == "suspended":
            conn.close()
            return False, "Your account is suspended."

    conn.close()
    result = {key: row[key] for key in row.keys()}
    return True, result


def change_password(user_id, current_password, new_password):
    conn = get_connection()
    row = conn.execute(
        "SELECT salt, password_hash FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if not row:
        return False, "Account not found."
    if _hash_password(current_password, row["salt"]) != row["password_hash"]:
        return False, "Current password is incorrect."
    if len(new_password) < 4:
        return False, "New password must be at least 4 characters."

    new_salt = os.urandom(16).hex()
    new_hash = _hash_password(new_password, new_salt)
    conn = get_connection()
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
        (new_hash, new_salt, user_id)
    )
    conn.commit()
    conn.close()
    return True, "Password changed successfully."


def has_users() -> bool:
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return n > 0