# fix_academy.py — Ondoa @' na '@ zisizohitajika
from pathlib import Path

p = Path("academy_db.py")
content = p.read_text(encoding="utf-8")

print("=== MISTARI 3 YA KWANZA ===")
for i, line in enumerate(content.split("\n")[:3], 1):
    print(f"{i}: {line!r}")

print("\n=== MISTARI 3 YA MWISHO ===")
for line in content.split("\n")[-4:]:
    print(f"{line!r}")

# Fix
lines = content.split("\n")
if lines and lines[0].strip() == "@'":
    lines = lines[1:]
    print("\n✅ Removed @' from top")
if lines and "'@" in lines[-1]:
    lines = lines[:-1]
    print("✅ Removed '@ | Out-File from bottom")

fixed = "\n".join(lines)
p.write_text(fixed, encoding="utf-8")
print(f"\n✅ academy_db.py fixed — {len(lines)} lines")
