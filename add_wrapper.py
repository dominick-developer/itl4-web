# add_wrapper.py - Ongeza Turso wrapper kwenye database.py
from pathlib import Path
import re

p = Path("database.py")
content = p.read_text(encoding="utf-8")

WRAPPER_CODE = '''

# ============================================================
# TURSO WRAPPER: Geuza tuples kuwa dict-like rows
# ============================================================
class DictRow:
    """Row inayofanya kazi kama sqlite3.Row (dict-like access)."""
    def __init__(self, keys, values):
        self._keys = list(keys)
        self._values = tuple(values)
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        try:
            return self._values[self._keys.index(key)]
        except ValueError:
            raise KeyError(key)
    def __getattr__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        try:
            return self._values[self._keys.index(key)]
        except ValueError:
            raise AttributeError(key)
    def keys(self):
        return self._keys
    def values(self):
        return self._values
    def __iter__(self):
        return iter(self._values)
    def __len__(self):
        return len(self._values)
    def __repr__(self):
        return f"DictRow({dict(zip(self._keys, self._values))})"


class TursoCursor:
    def __init__(self, cursor):
        self._cursor = cursor
    def execute(self, sql, params=()):
        self._cursor.execute(sql, params)
        return self
    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, tuple) and self._cursor.description:
            keys = [d[0] for d in self._cursor.description]
            return DictRow(keys, row)
        return row
    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], tuple) and self._cursor.description:
            keys = [d[0] for d in self._cursor.description]
            return [DictRow(keys, r) for r in rows]
        return rows
    def __getattr__(self, name):
        return getattr(self._cursor, name)


class TursoConnection:
    def __init__(self, conn):
        object.__setattr__(self, '_conn', conn)
    def cursor(self):
        return TursoCursor(self._conn.cursor())
    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return TursoCursor(cur)
    def commit(self):
        return self._conn.commit()
    def rollback(self):
        return self._conn.rollback()
    def close(self):
        return self._conn.close()
    def __getattr__(self, name):
        return getattr(self._conn, name)
'''

# Replace get_connection with wrapper version
old_func = '''def get_connection():
    if USE_TURSO:
        conn = turso_serverless.connect(
            TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN,
        )
        try:
            conn.row_factory = turso_serverless.Row
        except Exception:
            pass
        return conn
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
'''

new_func = '''def get_connection():
    if USE_TURSO:
        raw_conn = turso_serverless.connect(
            TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN,
        )
        return TursoConnection(raw_conn)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
'''

# Insert wrapper before get_connection
if "class DictRow" not in content:
    # Find get_connection position
    idx = content.find("def get_connection():")
    if idx == -1:
        print("ERROR: Cannot find get_connection")
        exit(1)
    content = content[:idx] + WRAPPER_CODE + "\n\n" + content[idx:]
    print("✅ Inserted DictRow + TursoCursor + TursoConnection")
else:
    print("⚠️ Wrapper already exists")

# Replace get_connection function
if old_func in content:
    content = content.replace(old_func, new_func)
    print("✅ Replaced get_connection() to use wrapper")
else:
    # Try regex fallback
    pattern = r"def get_connection\(\):.*?return conn"
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_func.rstrip(), content, count=1, flags=re.DOTALL)
        print("✅ Replaced get_connection() (regex)")
    else:
        print("⚠️ Could not replace get_connection()")

# Save
backup = p.with_suffix(".py.bak_wrapper")
backup.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
p.write_text(content, encoding="utf-8")
print(f"📁 Backup: {backup}")

# Verify syntax
import ast
try:
    ast.parse(content)
    print("✅ Syntax OK")
except SyntaxError as e:
    print(f"❌ Syntax error at line {e.lineno}: {e.msg}")