# update_groups_btn.py
from pathlib import Path

p = Path("templates/groups.html")
content = p.read_text(encoding="utf-8")

if "groups/export-pdf" in content:
    print("[OK] PDF button already exists — skipping")
else:
    # Insert after the header block, before {% if request.query_params.get('success') %}
    marker = """    {% if request.query_params.get('success') %}"""
    
    btn = """    {% if role == 'CR' or role == 'LECTURER' %}
    <div style="margin-bottom:16px;">
        <a href="/groups/export-pdf" 
           style="display:inline-flex;align-items:center;gap:8px;padding:12px 24px;background:linear-gradient(135deg,#0B1F33,#1e40af);color:white;border-radius:10px;font-weight:800;font-size:14px;text-decoration:none;box-shadow:0 4px 12px rgba(11,31,51,.2);">
            📄 Export Groups to PDF
        </a>
    </div>
    {% endif %}

    {% if request.query_params.get('success') %}"""
    
    if marker in content:
        content = content.replace(marker, btn, 1)
        p.write_text(content, encoding="utf-8")
        print("[OK] Added PDF download button")
    else:
        print("[WARN] Marker not found — trying fallback")
        if "<div class=\"container\">" in content:
            content = content.replace(
                "<div class=\"container\">",
                "<div class=\"container\">\n\n    {% if role == 'CR' or role == 'LECTURER' %}\n    <div style=\"margin-bottom:16px;\">\n        <a href=\"/groups/export-pdf\" style=\"display:inline-flex;align-items:center;gap:8px;padding:12px 24px;background:linear-gradient(135deg,#0B1F33,#1e40af);color:white;border-radius:10px;font-weight:800;font-size:14px;text-decoration:none;\">📄 Export Groups to PDF</a>\n    </div>\n    {% endif %}\n",
                1
            )
            p.write_text(content, encoding="utf-8")
            print("[OK] Added (fallback)")
        else:
            print("[ERROR] Cannot find insertion point")

print(f"[OK] Size: {len(content)} bytes")