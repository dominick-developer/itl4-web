# remove_old_signup.py — Futa signup_student ya pili (bila role)
from pathlib import Path

path = Path("database.py")
lines = path.read_text(encoding="utf-8").split("\n")

# Tafuta functions zote za signup_student
positions = []
for i, line in enumerate(lines):
    if line.strip().startswith("def signup_student"):
        positions.append(i)

print(f"Found {len(positions)} function(s)")

if len(positions) < 2:
    print("Only one function. No fix needed.")
    exit()

# Chagua ile ya pili (index 1) — ndiyo ya zamani
old_start = positions[1]

# Pata mwisho wake (def inayofuata au if __name__)
old_end = len(lines)
for j in range(old_start + 1, len(lines)):
    stripped = lines[j].strip()
    if stripped.startswith("def ") or stripped.startswith("if __name__"):
        old_end = j
        break

print(f"Removing function 2: lines {old_start+1} to {old_end}")
print(f"First line: {lines[old_start]}")
print(f"Last line:  {lines[old_end - 1]}")

# Backup
backup = path.with_suffix(".py.bak")
backup.write_text("\n".join(lines), encoding="utf-8")
print(f"Backup saved: {backup}")

# Futa
new_lines = lines[:old_start] + lines[old_end:]
path.write_text("\n".join(new_lines), encoding="utf-8")
print(f"Done! Removed {old_end - old_start} lines from database.py")
print()
print("Now run: python -c \"from database import signup_student; import inspect; print(inspect.signature(signup_student))\"")
