# fix_startup_v2.py — Rebuild startup() from scratch
from pathlib import Path
import re
import ast

p = Path("main.py")
content = p.read_text(encoding="utf-8")

# Find startup() function
pattern = re.compile(
    r'(@app\.on_event\("startup"\)\s*\ndef startup\(\):)(.*?)(?=\n@app\.|\n# ={3,}|\n\ndef |\Z)',
    re.DOTALL
)

match = pattern.search(content)
if not match:
    print("❌ Cannot find startup() function")
    exit(1)

print("Found startup() function — replacing with clean version")

new_body = '''    # 1. Init databases
    db.init_database()
    print("✅ Database ready")
    
    try:
        db.migrate_attendance_system()
        print("✅ Attendance migration ready")
    except Exception as _e:
        print(f"⚠️ Attendance migration: {_e}")
    
    try:
        db.migrate_timetable_status()
        print("✅ Timetable migration ready")
    except Exception as _e:
        print(f"⚠️ Timetable migration: {_e}")
    
    try:
        db.init_materials_table()
        print("✅ Materials table ready")
    except Exception as _e:
        print(f"⚠️ Materials init: {_e}")
    
    try:
        import coding_lab_db as _coding
        _coding.init_coding_tables()
        print("✅ Coding lab tables ready")
    except Exception as _e:
        print(f"⚠️ Coding init: {_e}")
    
    academy.init_academy()
    print("✅ Academy ready")
    
    try:
        academy.init_ai_tables()
        print("✅ AI tables ready")
    except Exception as _e:
        print(f"⚠️ AI init: {_e}")
    
    try:
        academy.init_coding_tables()
        print("✅ Coding tables ready")
    except Exception as _e:
        print(f"⚠️ Coding init: {_e}")
    
    try:
        academy.init_career_tables()
        print("✅ Career seeds complete")
    except Exception as _e:
        print(f"⚠️ Career init: {_e}")
    
    try:
        if hasattr(academy, "init_phase6_tables"):
            academy.init_phase6_tables()
            print("✅ Phase 6 tables complete")
    except Exception as _e:
        print(f"⚠️ Phase 6 init: {_e}")
    
    try:
        import legal_db as legal
        legal.init_legal_tables()
        print("✅ Legal tables ready")
    except Exception as _e:
        print(f"⚠️ Legal init: {_e}")
    
    try:
        import push_service
        push_service.init_push_table()
        print("✅ Push tables ready")
    except Exception as _e:
        print(f"⚠️ Push init: {_e}")
    
    # 3. Ensure CR 'cr' exists (NEVER reset password)
    import hashlib
    import os as _os
    try:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT u.id FROM users u WHERE u.username = 'cr'"
        ).fetchone()
        
        if not row:
            salt = _os.urandom(16).hex()
            pwd_hash = hashlib.sha256((salt + "123456").encode()).hexdigest()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO students (full_name, reg_number, phone, is_active, "
                "membership_status, date_joined, is_verified) "
                "VALUES (?, ?, ?, 1, 'approved', date('now'), 1)",
                ("Class Representative", "ITL4/CR/001", "0700111111"))
            sid = cur.lastrowid
            cur.execute(
                "INSERT INTO users (role, student_id, username, password_hash, salt, is_admin) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                ("CR", sid, "cr", pwd_hash, salt))
            conn.commit()
            print("✅ CR created: cr / 123456")
        else:
            print("✅ CR exists")
        conn.close()
    except Exception as _e:
        print(f"⚠️ CR ensure: {_e}")
    
    try:
        deleted, kept = db.cleanup_unused_seed_modules()
        if deleted > 0:
            print(f"✅ Cleaned {deleted} unused sample modules")
    except Exception as _e:
        print(f"⚠️ Cleanup: {_e}")
'''

new_startup = '@app.on_event("startup")\ndef startup():\n' + new_body

content = content[:match.start()] + new_startup + content[match.end():]

# Save
backup = p.with_suffix(".py.bak_startupv2")
backup.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
p.write_text(content, encoding="utf-8")
print(f"📁 Backup: {backup}")

# Verify
try:
    ast.parse(content)
    print("✅ Syntax OK")
except SyntaxError as e:
    print(f"❌ Syntax error at line {e.lineno}: {e.msg}")
    print(f"   Text: {e.text}")