from pathlib import Path
import ast

p = Path("academy_db.py")
content = p.read_text(encoding="utf-8")
original = content

old = 'lesson["duration"], li,'
new = 'lesson["duration"],'
count = content.count(old)
if count > 0:
    content = content.replace(old, new)
    print(f"FIX 1: Removed {count} extra 'li' occurrences")
else:
    print("FIX 1: Not found")

bt = content.count('\\`')
content = content.replace('\\`', '`')
print(f"FIX 2: Cleaned {bt} backslash-backticks")

if content != original:
    backup = p.with_suffix(".py.bak_seeds")
    backup.write_text(original, encoding="utf-8")
    p.write_text(content, encoding="utf-8")
    try:
        ast.parse(content)
        print("Syntax OK")
    except SyntaxError as e:
        print(f"Syntax error line {e.lineno}: {e.msg}")
else:
    print("No changes made — pattern not found")