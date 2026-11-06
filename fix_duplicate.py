# fix_duplicate.py - Futa get_connection ya pili (ya zamani)
from pathlib import Path

p = Path("database.py")
lines = p.read_text(encoding="utf-8").split("\n")

# Find all "def get_connection" lines
positions = []
for i, line in enumerate(lines):
    if line.strip().startswith("def get_connection"):
        positions.append(i)

print(f"Found {len(positions)} get_connection definitions")
for pos in positions:
    print(f"  Line {pos + 1}: {lines[pos]}")

if len(positions) < 2:
    print("Only one definition — no fix needed")
    exit(0)

# Remove the SECOND one (keep first, which is the correct one)
# Find where second one ends (next def at column 0, or EOF)
second_start = positions[1]
second_end = len(lines)
for i in range(second_start + 1, len(lines)):
    # Stop at next top-level def/class
    if lines[i] and not lines[i].startswith((" ", "\t")) and (
        lines[i].startswith("def ") or lines[i].startswith("class ")
        or lines[i].startswith("# ===")
    ):
        second_end = i
        break

print(f"\nRemoving second get_connection: lines {second_start + 1} to {second_end}")
print(f"First line: {lines[second_start]}")
print(f"Last line:  {lines[second_end - 1]}")

# Remove it
new_lines = lines[:second_start] + lines[second_end:]
new_content = "\n".join(new_lines)

# Save
backup = p.with_suffix(".py.bak_dup")
backup.write_text("\n".join(lines), encoding="utf-8")
p.write_text(new_content, encoding="utf-8")
print(f"\n📁 Backup: {backup}")
print(f"✅ Wrote database.py ({len(new_lines)} lines, was {len(lines)})")

# Verify
import ast
try:
    ast.parse(new_content)
    print("✅ Syntax OK")
except SyntaxError as e:
    print(f"❌ Syntax error at line {e.lineno}: {e.msg}")