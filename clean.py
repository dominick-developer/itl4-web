# clean.py — Ondoa mistari ya PowerShell here-string
from pathlib import Path

for filename in ["academy_db.py", "main.py", "database.py", "auth.py", "email_service.py"]:
    p = Path(filename)
    if not p.exists():
        print(f"{filename}: HAIPO")
        continue

    lines = p.read_text(encoding="utf-8").split("\n")
    original = len(lines)

    # Ondoa mistari ya mwisho yenye '@ au tupu
    while lines and ("'@" in lines[-1] or lines[-1].strip() == ""):
        lines.pop()

    # Ondoa @' mwanzoni
    while lines and (lines[0].strip() == "@'" or lines[0].strip() == ""):
        lines.pop(0)

    if len(lines) != original:
        p.write_text("\n".join(lines), encoding="utf-8")
        print(f"{filename}: {original} -> {len(lines)} mistari (IMESAFISHWA)")
    else:
        print(f"{filename}: {original} mistari (sawa)")

print()
print("=== SYNTAX CHECK ===")
import ast
ok = True
for filename in ["academy_db.py", "main.py", "database.py", "auth.py", "email_service.py"]:
    p = Path(filename)
    if not p.exists():
        continue
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"{filename}: OK")
    except SyntaxError as e:
        ok = False
        print(f"{filename}: KOSA line {e.lineno}: {e.msg}")
        print(f"   Text: {e.text}")

print()
print("HITIMISHO:", "FILES ZOTE SAWA" if ok else "KUNA MAKOSA - paste output hapo juu")