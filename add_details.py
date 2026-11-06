# add_details.py — Ongeza Details button + modal kwa timetable.html
from pathlib import Path
import re

p = Path("templates/timetable.html")
content = p.read_text(encoding="utf-8")

if "ℹ️ Details" in content or "showDetails" in content:
    print("✅ Details code already exists — skipping")
    exit(0)

# Read entire file, find entries loop, add Details button
# Check if file is the "grouped" template
if "{% for e in grouped[d] %}" not in content:
    print("⚠️ Template structure not found (grouped[d] loop)")
    print("Current file has:", "entries" if "entries" in content else "unknown structure")
    exit(1)

# 1. Add Details button after venue div in the session loop
old_venue = '''{% if e.venue %}
                        <div style="font-size:13px;color:var(--muted);font-weight:600;padding:4px 10px;background:#f1f5f9;border-radius:6px;">
                            📍 {{ e.venue }}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}'''

new_venue = '''{% if e.venue %}
                        <div style="font-size:13px;color:var(--muted);font-weight:600;padding:4px 10px;background:#f1f5f9;border-radius:6px;">
                            📍 {{ e.venue }}
                        </div>
                        {% endif %}
                        <div>
                            <button onclick='showDetails({{ e.id }})' style="background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;padding:8px 16px;border-radius:8px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;">ℹ️ Details</button>
                        </div>
                    </div>
                    <div id="data-{{ e.id }}" style="display:none;"
                         data-session-name="{{ (e.session_name or e.module_name or 'Session')|e }}"
                         data-module-name="{{ (e.module_name or '')|e }}"
                         data-module-code="{{ (e.module_code or '')|e }}"
                         data-module-desc="{{ (e.module_desc or '')|e }}"
                         data-teacher-name="{{ (e.teacher_name or '')|e }}"
                         data-teacher-phone="{{ (e.teacher_phone or '')|e }}"
                         data-teacher-email="{{ (e.teacher_email or '')|e }}"
                         data-venue="{{ (e.venue or '')|e }}"
                         data-notes="{{ (e.notes or '')|e }}"
                         data-status="{{ e.status or 'scheduled' }}"
                         data-day="{{ d }}"
                         data-start="{{ e.start_time or '' }}"
                         data-end="{{ e.end_time or '' }}"
                         data-postponed-to="{{ (e.postponed_to or '')|e }}"
                         data-postponed-reason="{{ (e.postponed_reason or '')|e }}"></div>
                    {% endfor %}'''

if old_venue in content:
    content = content.replace(old_venue, new_venue)
    print("✅ Added Details button + data divs")
else:
    print("⚠️ Venue pattern not found — checking alternative")
    # Try simpler pattern
    if "</div>\n                    {% endfor %}" in content:
        content = content.replace(
            "</div>\n                    {% endfor %}",
            "</div>\n                        <div><button onclick='showDetails({{ e.id }})' style=\"background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;padding:8px 16px;border-radius:8px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;\">ℹ️ Details</button></div>\n                    </div>\n                    {% endfor %}",
            count=1
        )
        print("✅ Added Details button (alternative pattern)")

# 2. Add modal + JS before {% endblock %}
modal_code = '''

<!-- DETAILS MODAL -->
<div id="detailsModal" style="display:none;position:fixed;inset:0;background:rgba(11,31,51,.75);z-index:99999;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(4px);" onclick="if(event.target===this)closeDetails();">
    <div style="background:white;border-radius:18px;max-width:560px;width:100%;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.4);">
        <div style="background:linear-gradient(135deg,#0B1F33,#1e40af);color:white;padding:22px 24px;border-radius:18px 18px 0 0;display:flex;justify-content:space-between;align-items:flex-start;gap:14px;">
            <div style="flex:1;">
                <div id="dTitle" style="font-size:20px;font-weight:900;margin-bottom:6px;line-height:1.2;"></div>
                <div id="dTime" style="font-size:13px;color:#cbd5e1;"></div>
            </div>
            <button onclick="closeDetails()" style="background:rgba(255,255,255,.15);color:white;border:none;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:16px;flex-shrink:0;">✕</button>
        </div>
        <div style="padding:24px;" id="dContent"></div>
        <div style="padding:16px 24px;background:#f8fafc;border-radius:0 0 18px 18px;border-top:1px solid #E2E8F0;text-align:right;">
            <button onclick="closeDetails()" class="btn btn-outline" style="padding:10px 24px;">Close</button>
        </div>
    </div>
</div>

<script>
function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>"']/g, function(c) {
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
}

function showDetails(entryId) {
    var el = document.getElementById('data-' + entryId);
    if (!el) { alert('Data not found for entry ' + entryId); return; }
    
    var d = el.dataset;
    var dayNames = {Monday:'Jumatatu', Tuesday:'Jumanne', Wednesday:'Jumatano', Thursday:'Alhamisi', Friday:'Ijumaa', Saturday:'Jumamosi', Sunday:'Jumapili'};
    
    document.getElementById('dTitle').textContent = d.sessionName || 'Session';
    document.getElementById('dTime').textContent = (dayNames[d.day] || d.day) + ' · ' + d.start + (d.end ? ' – ' + d.end : '');
    
    var html = '';
    
    if (d.status === 'postponed') {
        html += '<div style="background:#fffbeb;border-left:4px solid #F59E0B;padding:12px 16px;border-radius:8px;margin-bottom:14px;">';
        html += '<div style="font-weight:800;color:#92400e;font-size:13px;margin-bottom:4px;">⏸ KIPINDI KIME AHIRISHWA</div>';
        if (d.postponedTo) html += '<div style="color:#78350f;font-size:14px;"><strong>Mpya:</strong> ' + escapeHtml(d.postponedTo) + '</div>';
        if (d.postponedReason) html += '<div style="color:#78350f;font-size:13px;margin-top:4px;font-style:italic;">Sababu: ' + escapeHtml(d.postponedReason) + '</div>';
        html += '</div>';
    } else if (d.status === 'cancelled') {
        html += '<div style="background:#fef2f2;border-left:4px solid #DC2626;padding:12px 16px;border-radius:8px;margin-bottom:14px;">';
        html += '<div style="font-weight:800;color:#DC2626;font-size:13px;">✗ KIPINDI KIMEFUTWA</div>';
        if (d.postponedReason) html += '<div style="color:#7f1d1d;font-size:13px;margin-top:4px;">Sababu: ' + escapeHtml(d.postponedReason) + '</div>';
        html += '</div>';
    }
    
    function row(icon, label, value) {
        if (!value) return '';
        return '<div style="padding:10px 0;border-bottom:1px solid #E2E8F0;display:flex;gap:10px;align-items:flex-start;">' +
               '<div style="font-size:18px;flex-shrink:0;">' + icon + '</div>' +
               '<div style="flex:1;"><div style="font-size:11px;color:#64748B;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px;">' + label + '</div>' +
               '<div style="font-size:14px;color:#0F172A;font-weight:600;line-height:1.5;">' + value + '</div></div></div>';
    }
    
    if (d.moduleName && d.moduleName !== d.sessionName) {
        html += row('📚', 'Module', escapeHtml(d.moduleName) + (d.moduleCode ? ' <span style="color:#64748B;">(' + escapeHtml(d.moduleCode) + ')</span>' : ''));
    }
    if (d.venue) html += row('📍', 'Mahali', escapeHtml(d.venue));
    if (d.teacherName) {
        var teacherInfo = escapeHtml(d.teacherName);
        if (d.teacherPhone) teacherInfo += ' · 📞 ' + escapeHtml(d.teacherPhone);
        if (d.teacherEmail) teacherInfo += ' · ✉️ ' + escapeHtml(d.teacherEmail);
        html += row('👨‍🏫', 'Mwalimu', teacherInfo);
    }
    if (d.moduleDesc) {
        html += '<div style="margin-top:14px;padding:14px 16px;background:#f8fafc;border-radius:8px;border-left:4px solid #2563EB;">' +
                '<div style="font-size:11px;color:#2563EB;font-weight:800;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">📝 Maelezo ya Module</div>' +
                '<div style="font-size:14px;color:#334155;line-height:1.6;white-space:pre-wrap;">' + escapeHtml(d.moduleDesc) + '</div></div>';
    }
    if (d.notes) {
        html += '<div style="margin-top:14px;padding:14px 16px;background:#fffbeb;border-radius:8px;border-left:4px solid #F59E0B;">' +
                '<div style="font-size:11px;color:#92400e;font-weight:800;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">📌 Maelekezo Maalumu</div>' +
                '<div style="font-size:14px;color:#78350f;line-height:1.6;white-space:pre-wrap;">' + escapeHtml(d.notes) + '</div></div>';
    }
    if (!html) html = '<p style="text-align:center;color:#64748B;padding:20px;">Hakuna taarifa za ziada.</p>';
    
    document.getElementById('dContent').innerHTML = html;
    document.getElementById('detailsModal').style.display = 'flex';
}

function closeDetails() {
    document.getElementById('detailsModal').style.display = 'none';
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeDetails();
});
</script>
'''

# Insert before {% endblock %}
if "{% endblock %}" in content and "detailsModal" not in content:
    content = content.replace("{% endblock %}", modal_code + "\n{% endblock %}", 1)
    print("✅ Added modal + JS")

# Save
p.write_text(content, encoding="utf-8")
print(f"📁 Wrote {p}")
print(f"   Size: {len(content)} bytes")
print(f"   Has Details: {'ℹ️ Details' in content}")
print(f"   Has modal: {'detailsModal' in content}")