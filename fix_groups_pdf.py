# fix_groups_pdf.py
from pathlib import Path
import re

# ============================================================
# FIX 1: main.py — move export-pdf to /export/groups-pdf (no conflict)
# ============================================================
p = Path("main.py")
content = p.read_text(encoding="utf-8")

# Change URL in route
if '@app.get("/groups/export-pdf")' in content:
    content = content.replace(
        '@app.get("/groups/export-pdf")',
        '@app.get("/export/groups-pdf")'
    )
    print("[OK] Changed route to /export/groups-pdf")

# Verify delete route
if '/groups/{gid}/delete' not in content:
    # Add delete route
    delete_route = '''

@app.post("/groups/{gid}/delete")
def group_delete(request: Request, gid: int):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    try:
        conn = db.get_connection()
        conn.execute("DELETE FROM groups WHERE id = ?", (gid,))
        conn.commit()
        conn.close()
        from urllib.parse import quote
        return RedirectResponse("/groups?success=" + quote("Group imefutwa"), 303)
    except Exception as e:
        from urllib.parse import quote
        return RedirectResponse("/groups?error=" + quote(str(e)), 303)
'''
    content = content.rstrip() + delete_route
    print("[OK] Added delete route")
else:
    print("[OK] Delete route already exists")

# Approve-all route check
if '/students/approve-all-pending' not in content:
    approve_route = '''

@app.post("/students/approve-all-pending")
def students_approve_all_pending(request: Request):
    require_login(request)
    if request.session.get("role") != "CR":
        raise HTTPException(403)
    try:
        count = db.approve_all_pending()
        from urllib.parse import quote
        return RedirectResponse("/students?success=" + quote("Wanafunzi " + str(count) + " wamekubaliwa"), 303)
    except Exception as e:
        from urllib.parse import quote
        return RedirectResponse("/students?error=" + quote(str(e)), 303)
'''
    content = content.rstrip() + approve_route
    print("[OK] Added approve-all route")

p.write_text(content, encoding="utf-8")

# Verify
import ast
try:
    ast.parse(content)
    print("[OK] main.py syntax OK")
except SyntaxError as e:
    print("[ERROR] main.py line " + str(e.lineno) + ": " + str(e.msg))


# ============================================================
# FIX 2: groups.html — update PDF link + add delete button
# ============================================================
p = Path("templates/groups.html")
content = p.read_text(encoding="utf-8")

# Update PDF link
if 'href="/groups/export-pdf"' in content:
    content = content.replace('href="/groups/export-pdf"', 'href="/export/groups-pdf"')
    print("[OK] Updated PDF link to /export/groups-pdf")

# Verify delete button exists
if 'groups/{{ g.id }}/delete' in content or "groups/{{g.id}}/delete" in content:
    print("[OK] Delete button already in template")
else:
    print("[WARN] Delete button NOT in template — rewriting groups.html")

    NEW_HTML = '''{% extends "base.html" %}
{% block title %}Groups{% endblock %}
{% block page_title %}Groups{% endblock %}

{% block body %}
<div class="container">

    <div style="background:linear-gradient(135deg,#0B1F33 0%,#1e40af 100%);border-radius:16px;padding:24px;color:white;margin-bottom:22px;">
        <h1 style="font-size:22px;font-weight:900;margin:0 0 6px;">Groups ({{ groups|length }})</h1>
        <p style="color:#cbd5e1;margin:0;font-size:14px;">Vikundi vya wanafunzi - auto au manual</p>
    </div>

    {% if role == 'CR' or role == 'LECTURER' %}
    <div style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap;">
        <a href="/export/groups-pdf"
           style="display:inline-flex;align-items:center;gap:8px;padding:12px 24px;background:linear-gradient(135deg,#0B1F33,#1e40af);color:white;border-radius:10px;font-weight:800;font-size:14px;text-decoration:none;">
            Export Groups to PDF
        </a>
    </div>
    {% endif %}

    {% if request.query_params.get('success') %}
    <div style="background:#dcfce7;color:#16A34A;padding:14px;border-radius:8px;margin-bottom:16px;">
        {{ request.query_params.get('success') }}
    </div>
    {% endif %}
    {% if request.query_params.get('error') %}
    <div style="background:#fee2e2;color:#DC2626;padding:14px;border-radius:8px;margin-bottom:16px;">
        {{ request.query_params.get('error') }}
    </div>
    {% endif %}

    {% if role == 'CR' %}
    <div class="card" style="margin-bottom:18px;border-left:4px solid #16A34A;background:#f0fdf4;">
        <h2 style="font-size:18px;font-weight:800;color:var(--navy);margin-bottom:6px;">Auto-Group Wanafunzi</h2>
        <p style="color:#166534;font-size:13px;margin:0 0 14px;">
            Wanafunzi 10 kwa group. Wanafunzi waliokwisha kwenye group hawaguswi.
        </p>
        <form method="post" action="/groups/auto-group" onsubmit="return confirm('Unda groups mpya kwa wanafunzi wasio kwenye group?');">
            <button type="submit" style="padding:12px 24px;background:#16A34A;color:white;border:none;border-radius:8px;font-weight:800;cursor:pointer;font-family:inherit;">
                Auto-Group Sasa
            </button>
        </form>
    </div>

    <div class="card" style="margin-bottom:18px;">
        <h3 style="font-size:16px;font-weight:800;color:var(--navy);margin-bottom:12px;">Create Group Manually</h3>
        <form method="post" action="/groups/create">
            <div class="form-row">
                <div class="form-group">
                    <label>Group Name *</label>
                    <input type="text" name="name" required placeholder="e.g. Project Team A">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <input type="text" name="description" placeholder="Optional">
                </div>
            </div>
            <button type="submit" class="btn btn-primary" style="padding:10px 24px;">Create Group</button>
        </form>
    </div>
    {% endif %}

    {% if groups %}
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;">
        {% for g in groups %}
        <div class="card" style="padding:18px;display:flex;flex-direction:column;gap:10px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
                <a href="/groups/{{ g.id }}" style="text-decoration:none;flex:1;min-width:0;">
                    <h3 style="font-size:16px;font-weight:800;color:var(--navy);margin:0;word-break:break-word;">{{ g.name }}</h3>
                </a>
                <span style="background:#EFF6FF;color:#2563EB;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;white-space:nowrap;">
                    {{ g.member_count }} members
                </span>
            </div>
            {% if g.description %}
            <p style="color:var(--muted);font-size:12px;margin:0;">{{ g.description }}</p>
            {% endif %}
            <div style="display:flex;gap:6px;margin-top:auto;padding-top:8px;border-top:1px solid var(--border);">
                <a href="/groups/{{ g.id }}" class="btn btn-outline" style="padding:6px 14px;font-size:12px;flex:1;text-align:center;text-decoration:none;border:1px solid var(--border);border-radius:6px;">View</a>
                {% if role == 'CR' %}
                <form method="post" action="/groups/{{ g.id }}/delete" onsubmit="return confirm('Delete {{ g.name }}? Members watarudi ungrouped.');" style="display:inline;">
                    <button type="submit" style="padding:6px 14px;font-size:12px;background:#FEE2E2;color:#DC2626;border:1px solid #FCA5A5;border-radius:6px;font-weight:700;cursor:pointer;font-family:inherit;">
                        Delete
                    </button>
                </form>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="card" style="text-align:center;padding:60px 20px;">
        <div style="font-size:48px;margin-bottom:12px;">Groups</div>
        <h3 style="color:var(--navy);font-size:18px;font-weight:800;margin-bottom:8px;">Hakuna groups bado</h3>
        {% if role == 'CR' %}
        <p style="color:var(--muted);margin-bottom:20px;">Tumia Auto-Group au Create Manual juu.</p>
        {% endif %}
    </div>
    {% endif %}

</div>
{% endblock %}
'''
    p.write_text(NEW_HTML, encoding="utf-8")
    print("[OK] Rewrote groups.html with delete button")

p.write_text(content, encoding="utf-8") if 'NEW_HTML' not in dir() else None
print("[OK] groups.html finalized")