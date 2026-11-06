# fix_students2.py
from pathlib import Path

HTML = '''{% extends "base.html" %}
{% block title %}Students{% endblock %}
{% block page_title %}Students{% endblock %}

{% block body %}
<div class="container">

    <div class="toolbar">
        <div>
            <h1 style="color:var(--navy);font-size:22px;font-weight:800;">Students ({{ students|length }})</h1>
            <p style="color:var(--muted);font-size:13px;margin-top:4px;">
                {% if role == 'CR' %}Manage students - approve, suspend, or add directly
                {% else %}Wanafunzi wa darasa{% endif %}
            </p>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
            {% if role == 'CR' %}
            <a href="/students/add" class="btn btn-primary" style="padding:10px 20px;">+ Add Student</a>
            {% endif %}
        </div>
    </div>

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
        <details>
            <summary style="cursor:pointer;font-weight:800;color:var(--navy);font-size:16px;">
                + Add Student Directly (Admin - no email verification)
            </summary>
            <div style="margin-top:14px;">
                <p style="color:#166534;font-size:13px;margin:0 0 14px;">
                    Default password: <strong>it2026</strong>. Student ataingia moja kwa moja.
                </p>
                <form method="post" action="/students/admin-add">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Full Name *</label>
                            <input type="text" name="full_name" required placeholder="e.g. John Mwakitalu">
                        </div>
                        <div class="form-group">
                            <label>Admission No *</label>
                            <input type="text" name="admission_no" required placeholder="ITL4/STU/010" style="text-transform:uppercase;">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Phone *</label>
                            <input type="text" name="phone" required placeholder="0712345678">
                        </div>
                        <div class="form-group">
                            <label>Email (optional)</label>
                            <input type="email" name="email" placeholder="john@example.com">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Gender</label>
                            <select name="gender">
                                <option value="">Select</option>
                                <option value="Male">Male</option>
                                <option value="Female">Female</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="text" name="password" value="it2026">
                        </div>
                    </div>
                    <button type="submit" class="btn btn-success" style="padding:12px 24px;background:#16A34A;color:white;font-weight:800;">
                        Add Student
                    </button>
                </form>
            </div>
        </details>
    </div>
    {% endif %}

    <form method="get" style="margin-bottom:16px;display:flex;gap:8px;">
        <input type="text" name="q" value="{{ query or '' }}" placeholder="Search by name or reg number..." style="flex:1;padding:10px 14px;border:1px solid var(--border);border-radius:8px;font-size:14px;">
        <button type="submit" class="btn btn-secondary" style="padding:10px 20px;">Search</button>
    </form>

    {% if students %}
    <div class="card" style="overflow-x:auto;padding:0;">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="background:var(--navy);color:white;">
                    <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;">#</th>
                    <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;">Full Name</th>
                    <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;">Admission</th>
                    <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;">Phone</th>
                    <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:700;">Status</th>
                    {% if role == 'CR' %}
                    <th style="padding:12px 14px;text-align:right;font-size:13px;font-weight:700;">Actions</th>
                    {% endif %}
                </tr>
            </thead>
            <tbody>
                {% for s in students %}
                <tr style="border-bottom:1px solid var(--border);">
                    <td style="padding:10px 14px;font-size:13px;color:var(--muted);">{{ loop.index }}</td>
                    <td style="padding:10px 14px;font-weight:700;color:var(--navy);font-size:14px;">{{ s.full_name or '—' }}</td>
                    <td style="padding:10px 14px;font-size:13px;color:var(--muted);">{{ s.reg_number or '—' }}</td>
                    <td style="padding:10px 14px;font-size:13px;color:var(--muted);">{{ s.phone or '—' }}</td>
                    <td style="padding:10px 14px;">
                        {% if s.membership_status == 'approved' %}
                        <span style="background:#dcfce7;color:#16A34A;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;">✓ Approved</span>
                        {% elif s.membership_status == 'pending' %}
                        <span style="background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;">⏳ Pending</span>
                        {% elif s.membership_status == 'suspended' %}
                        <span style="background:#fee2e2;color:#DC2626;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;">⚠ Suspended</span>
                        {% else %}
                        <span style="background:#f1f5f9;color:#64748B;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;">{{ s.membership_status or '—' }}</span>
                        {% endif %}
                    </td>
                    {% if role == 'CR' %}
                    <td style="padding:10px 14px;text-align:right;">
                        <div style="display:flex;gap:6px;justify-content:flex-end;">
                            <a href="/students/{{ s.id }}/edit" class="btn btn-outline" style="padding:5px 12px;font-size:12px;">Edit</a>
                            {% if s.membership_status == 'pending' %}
                            <form method="post" action="/students/{{ s.id }}/approve" style="display:inline;">
                                <button class="btn btn-success" style="padding:5px 12px;font-size:12px;background:#16A34A;color:white;">Approve</button>
                            </form>
                            {% endif %}
                        </div>
                    </td>
                    {% endif %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="card" style="text-align:center;padding:60px 20px;">
        <div style="font-size:48px;margin-bottom:12px;">👥</div>
        <h3 style="color:var(--navy);font-size:18px;font-weight:800;margin-bottom:8px;">Hakuna wanafunzi bado</h3>
        {% if role == 'CR' %}
        <p style="color:var(--muted);margin-bottom:20px;">Anza kuongeza mwanafunzi wa kwanza.</p>
        <a href="/students/add" class="btn btn-primary">+ Add First Student</a>
        {% endif %}
    </div>
    {% endif %}

</div>
{% endblock %}
'''

p = Path("templates/students.html")
p.parent.mkdir(exist_ok=True)
p.write_text(HTML, encoding="utf-8")
print(f"[OK] Wrote {p}")
print(f"   Size: {len(HTML)} bytes")
print(f"   Has admin-add: {'admin-add' in HTML}")
print(f"   Balanced Jinja: {{ = ", HTML.count('{%'), ", }} = ", HTML.count('%}'))