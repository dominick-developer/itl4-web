# fix_files.py — Safisha PowerShell contamination kwenye files zote
from pathlib import Path
import ast


def clean_file(filepath):
    p = Path(filepath)
    if not p.exists():
        print(f"  {filepath}: HAIpo")
        return
    lines = p.read_text(encoding="utf-8").split("\n")
    original = len(lines)
    changed = False

    # Ondoa mistari ya mwisho yenye '@ au tupu
    while lines and ("'@" in lines[-1] or lines[-1].strip() == ""):
        if "'@" in lines[-1]:
            print(f"  {filepath}: Ondoa mwisho -> {lines[-1][:60]!r}")
            changed = True
        lines.pop()

    # Ondoa @' mwanzoni
    while lines and lines[0].strip() in ("@'", ""):
        if lines[0].strip() == "@'":
            print(f"  {filepath}: Ondoa mwanzo -> @'")
            changed = True
        lines.pop(0)

    if changed:
        p.write_text("\n".join(lines), encoding="utf-8")
        print(f"  {filepath}: {original} -> {len(lines)} mistari")
    else:
        print(f"  {filepath}: Sawa (hakuna mabadiliko)")


print("=== KUSAFISHA FILES ===")
for f in ["academy_db.py", "main.py", "database.py", "auth.py", "email_service.py"]:
    clean_file(f)

print("\n=== SYNTAX CHECK ===")
all_ok = True
for f in ["academy_db.py", "main.py", "database.py", "auth.py", "email_service.py"]:
    p = Path(f)
    if not p.exists():
        print(f"  {f}: HAIpo")
        continue
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  {f}: OK")
    except SyntaxError as e:
        all_ok = False
        print(f"  {f}: KOSA line {e.lineno}: {e.msg}")
        print(f"      >>> {e.text}")

print()
if all_ok:
    print("HITIMISHO: Files zote ziko sawa. Sasa: git add . && git commit -m 'Fix' && git push")
else:
    print("HITIMISHO: Kuna makosa. Paste output hapa.")