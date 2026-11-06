# add_group_funcs.py
from pathlib import Path

ADD = '''

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
        m = re.search(r'Auto Group (\\d+)', r["name"] or "")
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
'''

p = Path("database.py")
content = p.read_text(encoding="utf-8")

if "admin_add_student" in content and "auto_group_ungrouped_students" in content:
    print("[OK] Functions already exist — skipping")
else:
    content = content.rstrip() + ADD
    p.write_text(content, encoding="utf-8")
    print("[OK] Added functions to database.py")

# Verify
import importlib
import sys
if 'database' in sys.modules:
    importlib.reload(sys.modules['database'])
import database
print(f"[OK] admin_add_student: {'admin_add_student' in dir(database)}")
print(f"[OK] auto_group_ungrouped_students: {'auto_group_ungrouped_students' in dir(database)}")
print(f"[OK] get_ungrouped_students: {'get_ungrouped_students' in dir(database)}")