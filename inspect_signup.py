# inspect_signup.py — Onyesha signatures kamili za signup_student
from pathlib import Path

path = Path("database.py")
lines = path.read_text(encoding="utf-8").split("\n")

# Tafuta mistari yenye "def signup_student"
positions = []
for i, line in enumerate(lines):
    if line.strip().startswith("def signup_student"):
        positions.append(i)

print(f"Found {len(positions)} function(s):\n")

for idx, start in enumerate(positions):
    # Pata mwisho (line inayofuata ya "def " au "if __name__")
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].strip().startswith("def ") or lines[j].strip().startswith("if __name__"):
            end = j
            break

    print(f"=== FUNCTION {idx+1} ===")
    print(f"Starts at line: {start + 1}")
    print(f"Ends at line: {end}")
    print(f"Length: {end - start} lines")
    print("First 8 lines:")
    for k in range(start, min(start + 8, end)):
        print(f"  {lines[k]}")
    print("Last 3 lines:")
    for k in range(max(start, end - 3), end):
        print(f"  {lines[k]}")
    print()
