# diagnose.py — Check recent STUDENT users
import database as db

conn = db.get_connection()
rows = conn.execute(
    "SELECT u.id, u.username, u.role, s.full_name, "
    "s.membership_status, s.is_verified, "
    "substr(u.password_hash, 1, 15) as hash_preview "
    "FROM users u "
    "LEFT JOIN students s ON u.student_id = s.id "
    "WHERE u.role = 'STUDENT' "
    "ORDER BY u.id DESC LIMIT 10"
).fetchall()

print("=" * 70)
print("Recent STUDENT users (last 10):")
print("=" * 70)

if not rows:
    print("  NONE FOUND — no STUDENT users in database!")
else:
    for r in rows:
        d = dict(r)
        print(f"\nID: {d['id']}")
        print(f"  Username:    {d['username']!r}")
        print(f"  Role:        {d['role']}")
        print(f"  Full Name:   {d['full_name']!r}")
        print(f"  Status:      {d['membership_status']}")
        print(f"  Verified:    {d['is_verified']}")
        print(f"  Hash:        {d['hash_preview']}...")

# Count totals
print("\n" + "=" * 70)
print("COUNTS:")
print("=" * 70)
total = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'STUDENT'").fetchone()[0]
print(f"Total STUDENT users: {total}")

total_students = conn.execute("SELECT COUNT(*) FROM students WHERE is_active = 1").fetchone()[0]
print(f"Total active students: {total_students}")

# Find admin-added (verified = 1, no email verification needed)
admin_added = conn.execute(
    "SELECT COUNT(*) FROM students WHERE is_active = 1 AND is_verified = 1"
).fetchone()[0]
print(f"Students with is_verified=1: {admin_added}")

conn.close()