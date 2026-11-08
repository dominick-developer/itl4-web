# pdf_export.py - Group Distribution PDF generator
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
        bottomMargin=20 * mm,
        title="Group Distributions 2026",
        author="Chuo Cha Ufundi Arusha",
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
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontName="Helvetica-Oblique", fontSize=8,
        textColor=colors.HexColor("#94A3B8"), alignment=TA_CENTER,
    )
    cr_style = ParagraphStyle(
        "CRFooter", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10,
        textColor=NAVY, alignment=TA_CENTER, leading=13,
    )
    cr_contacts_style = ParagraphStyle(
        "CRContacts", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9,
        textColor=colors.HexColor("#475569"), alignment=TA_CENTER,
    )

    story = []

    # ============ HEADER ============
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("CHUO CHA UFUNDI ARUSHA", title_style))
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

    # ============ GROUPS ============
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

    # ============ FOOTER ============
    story.append(Spacer(1, 10 * mm))

    ts = datetime.now().strftime("%d %B %Y, %H:%M")

    story.append(Paragraph("PROVIDED BY CR: DOMINICK MWENDA", cr_style))
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(
        "0614236148  |  NORMAL CALL: 0661253815",
        cr_contacts_style))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Generated by IT Level 4 Connect - " + ts,
        footer_style))

    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
