# update_students.py
from pathlib import Path

# Read existing, insert admin form after toolbar
p = Path("templates/students.html")
content = p.read_text(encoding="utf-8")

# Check if already added
if 'students/admin-add' in content:
    print("[OK] Admin add form already exists — skipping")
else:
    # Find the toolbar div and insert after
    marker = '</div>\n\n    {% if students %}'
    admin_form = '''
    {% if role == 'CR' %}
    <!-- ADMIN ADD STUDENT -->
    <div class="card" style="margin-bottom:18px;border-left:4px solid #16A34A;background:#f0fdf4;">
        <details>
            <summary style="cursor:pointer;font-weight:800;color:var(--navy);font-size:16px;">+ Add Student Directly (Admin)</summary>
            <div style="margin-top:14px;">
                <p style="color:#166534;font-size:13px;margin:0 0 14px;">
                    Student ameongezwa moja kwa moja (no email verification). Password default: <strong>it2026</strong>
                </p>
                <form method="post" action="/students/admin-add">
                    <div class="form-row">
                        <div class="form-group">
                            <label>Full Name *</label>
                            <input type="text" name="full_name" required placeholder="e.g. John Mwakitalu">
                        </div>
                        <div class="form-group">
                            <label>Admission No *</label>
                            <input type="text" name="admission_no" required placeholder="e.g. ITL4/STU/010" style="text-transform:uppercase;">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Phone *</label>
                            <input type="text" name="phone" required placeholder="e.g. 0712345678">
                        </div>
                        <div class="form-group">
                            <label>Email (optional)</label>
                            <input type="email" name="email" placeholder="e.g. john@example.com">
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
                            <input type="text" name="password" value="it2026" placeholder="it2026">
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

    {% if students %}'''
    
    if marker in content:
        content = content.replace(marker, admin_form, 1)
        p.write_text(content, encoding="utf-8")
        print("[OK] Added admin add form to students.html")
    else:
        print("[WARN] Marker not found — trying alternative")
        # Try simpler: insert before {% if students %}
        if '{% if students %}' in content:
            content = content.replace('{% if students %}', admin_form.replace('\n    {% if students %}', ''), 1)
            p.write_text(content, encoding="utf-8")
            print("[OK] Added (alternative pattern)")
        else:
            print("[ERROR] Cannot find {% if students %}")

print(f"[OK] Size: {len(content)} bytes")