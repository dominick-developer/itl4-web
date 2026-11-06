# fix_pdf.py
from pathlib import Path

# ============================================================
# 1. Create pdf_export.py if missing
# ============================================================
pdf_file = Path("pdf_export.py")

PDF_CODE = '''# pdf_export.py - Group Distribution PDF generator
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


NAVY = colors.HexColor("#0B1F33")
ORANGE = colors.HexColor("#F47721")
LIGHT_BG = colors.HexColor("#F5F7FA")
BORDER = colors.HexColor("#E2E8F0")


def _fmt_gender(g):
    if not g:
        return "-"
    g = g.strip().lower()
    if g in ("male", "m", "me", "mwanaume"):
        return "Me"
    if g in ("female", "f", "ke", "mwanamke"):
        return "Ke"
    return g.title()


def generate_groups_pdf(groups_data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title="Group Distributions 2026",
        author="Chuo Cha Fundi Arusha",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleHeader", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=20, textColor=NAVY,
        alignment=TA_CENTER, spaceAfter=6, leading=24,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleHeader", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=13, textColor=NAVY,
        alignment=TA_CENTER, spaceAfter=3, leading=17,
    )
    section_style = ParagraphStyle(
        "SectionHeader", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=14, textColor=ORANGE,
        alignment=TA_CENTER, spaceBefore=6, spaceAfter=14, leading=18,
    )
    group_name_style = ParagraphStyle(
        "GroupName", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=13,
        textColor=colors.white, alignment=TA_LEFT,
    )
    cell_style = ParagraphStyle(
        "Cell", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10,
        textColor=colors.HexColor("#0F172A"), leading=13,
    )
    cell_bold = ParagraphStyle(
        "CellBold", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10,
        textColor=colors.HexColor("#0F172A"), leading=13,
    )
    header_cell_style = ParagraphStyle(
        "HeaderCell", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10,
        textColor=colors.white, alignment=TA_LEFT,
    )

    story = []

    # HEADER
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("CHUO CHA FUNDI ARUSHA", title_style))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("INFORMATION TECHNOLOGY NTA LEVEL 4", subtitle_style))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("GROUP DISTRIBUTIONS (2026)", section_style))

    divider = Table([[""]], colWidths=[180 * mm], rowHeights=[3])
    divider.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ORANGE),
    ]))
    story.append(divider)
    story.append(Spacer(1, 8 * mm))

    # GROUPS
    if not groups_data:
        story.append(Paragraph(
            "<i>Hakuna groups zilizoundwa bado.</i>",
            ParagraphStyle("Empty", parent=styles["Normal"],
                           alignment=TA_CENTER, textColor=colors.grey)
        ))
    else:
        for idx, group in enumerate(groups_data, start=1):
            members = group.get("members", [])
            total = len(members)
            male_count = sum(1 for m in members
                             if (m.get("gender") or "").strip().lower()
                             in ("male", "m", "me", "mwanaume"))
            female_count = total - male_count

            group_block = []
            group_title = "GROUP " + str(idx)
            if group.get("name"):
                group_title = str(group["name"]).upper()

            header_data = [[
                Paragraph(group_title, group_name_style),
                Paragraph(
                    str(total) + " members - " + str(male_count) + "M + " + str(female_count) + "F",
                    ParagraphStyle("GroupMetaWhite", parent=styles["Normal"],
                                   fontName="Helvetica", fontSize=9,
                                   textColor=colors.white, alignment=2),
                ),
            ]]
            header_table = Table(header_data, colWidths=[110 * mm, 60 * mm])
            header_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            group_block.append(header_table)

            if members:
                rows = [[
                    Paragraph("#", header_cell_style),
                    Paragraph("MAJINA", header_cell_style),
                    Paragraph("GENDER", header_cell_style),
                    Paragraph("NAMBA YA SIMU", header_cell_style),
                ]]
                for i, m in enumerate(members, start=1):
                    rows.append([
                        Paragraph(str(i), cell_style),
                        Paragraph((m.get("full_name") or "-").upper(), cell_bold),
                        Paragraph(_fmt_gender(m.get("gender")), cell_style),
                        Paragraph(m.get("phone") or "-", cell_style),
                    ])

                member_table = Table(
                    rows,
                    colWidths=[12 * mm, 88 * mm, 25 * mm, 45 * mm],
                    repeatRows=1,
                )
                member_style = [
                    ("BACKGROUND", (0, 0), (-1, 0), ORANGE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ]
                for r in range(1, len(rows)):
                    if r % 2 == 0:
                        member_style.append(("BACKGROUND", (0, r), (-1, r), LIGHT_BG))
                member_table.setStyle(TableStyle(member_style))
                group_block.append(member_table)

            group_block.append(Spacer(1, 8 * mm))

            if total <= 12:
                story.append(KeepTogether(group_block))
            else:
                story.extend(group_block)

    # FOOTER
    story.append(Spacer(1, 6 * mm))
    ts = datetime.now().strftime("%d %B %Y, %H:%M")
    story.append(Paragraph(
        "Generated by IT Level 4 Connect - " + ts,
        ParagraphStyle("Footer", parent=styles["Normal"],
                       fontName="Helvetica-Oblique", fontSize=8,
                       textColor=colors.HexColor("#94A3B8"), alignment=TA_CENTER),
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
'''

if pdf_file.exists():
    print("[OK] pdf_export.py already exists")
else:
    pdf_file.write_text(PDF_CODE, encoding="utf-8")
    print("[OK] Created pdf_export.py")

# ============================================================
# 2. Add reportlab to requirements.txt if missing
# ============================================================
req = Path("requirements.txt")
if req.exists():
    content = req.read_text(encoding="utf-8")
    if "reportlab" not in content:
        content = content.rstrip() + "\nreportlab\n"
        req.write_text(content, encoding="utf-8")
        print("[OK] Added reportlab to requirements.txt")
    else:
        print("[OK] reportlab already in requirements.txt")
else:
    print("[WARN] requirements.txt not found")

# ============================================================
# 3. Verify syntax
# ============================================================
import ast
try:
    ast.parse(PDF_CODE)
    print("[OK] pdf_export.py syntax OK")
except SyntaxError as e:
    print("[ERROR] Line " + str(e.lineno) + ": " + str(e.msg))

# ============================================================
# 4. Check main.py route uses /export/groups-pdf (not /groups/export-pdf)
# ============================================================
mp = Path("main.py")
content = mp.read_text(encoding="utf-8")
if '@app.get("/groups/export-pdf")' in content:
    content = content.replace(
        '@app.get("/groups/export-pdf")',
        '@app.get("/export/groups-pdf")'
    )
    mp.write_text(content, encoding="utf-8")
    print("[OK] Updated route to /export/groups-pdf")
elif '@app.get("/export/groups-pdf")' in content:
    print("[OK] Route already /export/groups-pdf")
else:
    print("[WARN] PDF route not found in main.py")

# ============================================================
# 5. Check groups.html uses /export/groups-pdf
# ============================================================
gp = Path("templates/groups.html")
if gp.exists():
    gcontent = gp.read_text(encoding="utf-8")
    if 'href="/groups/export-pdf"' in gcontent:
        gcontent = gcontent.replace('href="/groups/export-pdf"', 'href="/export/groups-pdf"')
        gp.write_text(gcontent, encoding="utf-8")
        print("[OK] Updated groups.html link to /export/groups-pdf")
    elif '/export/groups-pdf' in gcontent:
        print("[OK] groups.html link already /export/groups-pdf")
    else:
        print("[WARN] PDF link not found in groups.html")

print("")
print("NEXT: pip install reportlab")
print("      git add pdf_export.py requirements.txt main.py templates/groups.html")
print("      git commit -m 'Fix PDF export'")
print("      git push")