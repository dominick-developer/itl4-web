# fix_duplicate.py — Ondoa signup_student ya zamani
import re
from pathlib import Path

path = Path("database.py")
content = path.read_text(encoding="utf-8")

# Tafuta namba za mistari yenye "def signup_student"
lines = content.split("\n")
positions = []
for i, line in enumerate(lines):
    if line.strip().startswith("def signup_student"):
        positions.append((i, line.strip()))

print(f"Found {len(positions)} signup_student function(s):")
for i, (lineno, signature) in enumerate(positions):
    print(f"  {i+1}. Line {lineno+1}: {signature}")

if len(positions) < 2:
    print("\nOK - Only one function. No fix needed.")
    exit()

# Chagua ile ya zamani (bila neno "password" kwenye signature)
old_start = None
new_start = None
for lineno, signature in positions:
    if "password" not in signature:
        old_start = lineno
    else:
        new_start = lineno

if old_start is None:
    print("\nCould not find old function. Manual check needed.")
    exit()

# Pata mwisho wa function ya zamani (line inayofuata ya "def " au mwisho wa file)
old_end = None
for i in range(old_start + 1, len(lines)):
    if lines[i].strip().startswith("def ") or lines[i].strip().startswith("if __name__"):
        old_end = i
        break

if old_end is None:
    old_end = len(lines)

# Ondoa block
print(f"\nRemoving old function: lines {old_start+1} to {old_end}")
new_lines = lines[:old_start] + lines[old_end:]
new_content = "\n".join(new_lines)

# Andika backup kwanza
backup = path.with_suffix(".py.bak")
backup.write_text(content, encoding="utf-8")
print(f"Backup saved: {backup}")

# Andika mpya
path.write_text(new_content, encoding="utf-8")
print(f"Done! Removed {old_end - old_start} lines from database.py")
print("\nNow run: python check_signup.py")
