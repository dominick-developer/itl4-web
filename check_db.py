# check_db.py — Angalia hali ya verification
from database import get_connection
from datetime import datetime

conn = get_connection()

print("=" * 60)
print("STUDENTS TABLE — Verification Status")
print("=" * 60)

rows = conn.execute(
    "SELECT id, full_name, reg_number, email, is_verified, "
    "verification_code, verification_expires_at, membership_status "
    "FROM students ORDER BY id DESC LIMIT 10"
).fetchall()

if not rows:
    print("No students in database!")
else:
    for r in rows:
        print(f"\nID: {r['id']}")
        print(f"  Name: {r['full_name']}")
        print(f"  Reg#: {r['reg_number']}")
        print(f"  Email: {r['email']}")
        print(f"  is_verified: {r['is_verified']}")
        print(f"  code: {r['verification_code']!r}")
        print(f"  expires_at: {r['verification_expires_at']!r}")
        print(f"  status: {r['membership_status']}")

print(f"\n{'=' * 60}")
print(f"Current UTC time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Current local time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

conn.close()
