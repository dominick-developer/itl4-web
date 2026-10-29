from pathlib import Path
import glob

files = glob.glob("*.py") + glob.glob("templates/*.html")
fixed_count = 0

for fp in files:
    p = Path(fp)
    try:
        content = p.read_text(encoding="utf-8")
    except Exception:
        continue

    lines = content.split("\n")
    changed = False

    if lines and lines[0].strip() == "@'":
        lines = lines[1:]
        changed = True

    # Remove trailing " '@ | Out-File ..." line
    if lines:
        for i in range(len(lines) - 1, max(len(lines) - 5, -1), -1):
            if lines[i].strip().startswith("'@") or "'@ |" in lines[i]:
                lines = lines[:i]
                changed = True
                break

    if changed:
        p.write_text("\n".join(lines), encoding="utf-8")
        print(f"✅ Fixed: {fp}")
        fixed_count += 1

print(f"\nTotal fixed: {fixed_count} files")
