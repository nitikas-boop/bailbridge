"""
BailBridge — PDF Generation Engine (Consolidated)
"""
import io, os, datetime, logging
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from utils import get_detailed_enclosures

logger = logging.getLogger("bailbridge.pdf")

def _build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontSize=16, textColor=colors.navy),
        "body": ParagraphStyle("Body", parent=base["Normal"], fontSize=10, leading=14),
        "justified": ParagraphStyle("Justified", parent=base["Normal"], fontSize=10, leading=14, alignment=4)
    }

def generate_bail_application(case_id, defendant_name, strategy_type, legal_grounds, **kwargs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=80)
    styles = _build_styles()
    story = []
    
    # Header
    story.append(Paragraph(f"IN THE COURT OF SESSIONS", styles["title"]))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"<b>Applicant:</b> {defendant_name}", styles["body"]))
    story.append(Paragraph(f"<b>Strategy:</b> {strategy_type}", styles["body"]))
    story.append(Paragraph(f"<b>Grounds:</b> {legal_grounds}", styles["justified"]))
    
    # Enclosures
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("<b><u>LIST OF ENCLOSURES</u></b>", styles["body"]))
    for enc in get_detailed_enclosures(case_id):
        story.append(Paragraph(f"• {enc['name']} ({enc['status']})", styles["body"]))
        
    # Regional Summary (Translation Placeholder)
    lang = kwargs.get("preferred_language", "English")
    if lang.lower() != "english":
        story.append(PageBreak())
        story.append(Paragraph(f"Regional Summary ({lang})", styles["title"]))
        story.append(Paragraph("Translation of key grounds would appear here.", styles["body"]))

    doc.build(story)
    
    path = os.path.join("storage", f"bail_draft_{case_id}.pdf")
    if not os.path.exists("storage"): os.makedirs("storage")
    with open(path, "wb") as f: f.write(buffer.getvalue())
    return os.path.abspath(path)
