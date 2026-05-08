"""
BailBridge — NALSA / India-specific Legal Document Templates  (Developer 4 · Phase 1)

Provides generate_nalsa_form() which produces a pre-filled PDF replicating the
National Legal Services Authority (NALSA) bail-assistance application form.

The function is intentionally self-contained: it requires only ReportLab and the
caller-supplied defendant data dict, making it easy to invoke from any agent or
webhook handler.
"""

import io
import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


# ── Brand / colour constants ───────────────────────────────────────────────────

_SAFFRON   = colors.HexColor("#FF9933")   # Indian flag saffron
_NAVY      = colors.HexColor("#000080")   # Indian flag navy / NALSA blue
_LIGHT_BG  = colors.HexColor("#FFF8F0")
_MID_GRAY  = colors.HexColor("#CCCCCC")
_DARK_TEXT = colors.HexColor("#1A1A1A")


# ── Style factory ─────────────────────────────────────────────────────────────

def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "form_title": ParagraphStyle(
            "NalsaTitle",
            parent=base["Title"],
            fontSize=16,
            textColor=_NAVY,
            spaceAfter=2,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        ),
        "form_subtitle": ParagraphStyle(
            "NalsaSubtitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=_SAFFRON,
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName="Helvetica-Oblique",
        ),
        "section_heading": ParagraphStyle(
            "NalsaSection",
            parent=base["Normal"],
            fontSize=11,
            textColor=_NAVY,
            spaceBefore=10,
            spaceAfter=4,
            fontName="Helvetica-Bold",
            backColor=_LIGHT_BG,
            leftIndent=4,
        ),
        "body": ParagraphStyle(
            "NalsaBody",
            parent=base["Normal"],
            fontSize=10,
            textColor=_DARK_TEXT,
            leading=15,
            fontName="Helvetica",
        ),
        "justified": ParagraphStyle(
            "NalsaJustified",
            parent=base["Normal"],
            fontSize=10,
            textColor=_DARK_TEXT,
            leading=15,
            alignment=TA_JUSTIFY,
            fontName="Helvetica",
        ),
        "label": ParagraphStyle(
            "NalsaLabel",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.gray,
            fontName="Helvetica-Oblique",
        ),
        "value": ParagraphStyle(
            "NalsaValue",
            parent=base["Normal"],
            fontSize=10,
            textColor=_DARK_TEXT,
            fontName="Helvetica",
        ),
        "footer": ParagraphStyle(
            "NalsaFooter",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER,
            fontName="Helvetica-Oblique",
        ),
        "declaration": ParagraphStyle(
            "NalsaDecl",
            parent=base["Normal"],
            fontSize=9,
            textColor=_DARK_TEXT,
            leading=14,
            alignment=TA_JUSTIFY,
            fontName="Helvetica",
        ),
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _kv_table(rows_data: list[tuple[str, str]], styles: dict) -> Table:
    """
    Render a two-column label / value table from a list of (label, value) tuples.
    """
    table_rows = [
        [
            Paragraph(label, styles["label"]),
            Paragraph(str(value) if value else "—", styles["value"]),
        ]
        for label, value in rows_data
    ]
    tbl = Table(table_rows, colWidths=[5.5 * cm, 11.5 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _LIGHT_BG]),
                ("GRID",          (0, 0), (-1, -1), 0.25, _MID_GRAY),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return tbl


def _divider(color=_SAFFRON, thickness: float = 1.5) -> HRFlowable:
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=6)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_nalsa_form(
    # Mandatory identifiers
    case_id: str,
    defendant_name: str,
    # Personal details
    father_or_spouse_name: Optional[str] = None,
    dob: Optional[str] = None,
    gender: Optional[str] = None,
    address: Optional[str] = None,
    district: Optional[str] = None,
    state: Optional[str] = None,
    phone: Optional[str] = None,
    aadhaar_last4: Optional[str] = None,
    # Arrest / custody details
    fir_number: Optional[str] = None,
    police_station: Optional[str] = None,
    date_of_arrest: Optional[str] = None,
    charge_section: Optional[str] = None,
    charge_description: Optional[str] = None,
    court_name: Optional[str] = None,
    next_hearing_date: Optional[str] = None,
    bail_amount: Optional[float] = None,
    # Legal aid details
    legal_aid_requested: bool = True,
    reason_for_aid: Optional[str] = None,
    # Detaining authority
    jail_name: Optional[str] = None,
    superintendent_name: Optional[str] = None,
    # BailBridge metadata
    agent_name: Optional[str] = None,
    agent_phone: Optional[str] = None,
) -> bytes:
    """
    Generate a NALSA Bail-Assistance Application Form as a PDF.

    This form is modelled on the National Legal Services Authority (NALSA)
    standard bail application format required by legal aid clinics and
    District Legal Services Authorities (DLSAs) across India.

    Args:
        case_id:              BailBridge case identifier.
        defendant_name:       Full name of the applicant / under-trial prisoner.
        father_or_spouse_name: Father's or spouse's name (as on Aadhaar / court records).
        dob:                  Date of birth (DD-MM-YYYY or YYYY-MM-DD).
        gender:               'Male' | 'Female' | 'Other'.
        address:              Permanent / current residential address.
        district:             District of residence.
        state:                State of residence.
        phone:                Contact number (own or family member's).
        aadhaar_last4:        Last 4 digits of Aadhaar for partial identification.
        fir_number:           FIR / case number registered at police station.
        police_station:       Name of registering police station.
        date_of_arrest:       Date of arrest (DD-MM-YYYY).
        charge_section:       IPC / BNS section numbers (e.g. '302, 34 IPC').
        charge_description:   Brief description of alleged offence.
        court_name:           Name of the trial / magistrate court.
        next_hearing_date:    Next scheduled hearing date.
        bail_amount:          Bail amount set by court (INR), if any.
        legal_aid_requested:  Whether applicant is requesting free legal aid.
        reason_for_aid:       Reason for legal aid (indigent, SC/ST, juvenile, etc.).
        jail_name:            Name of the jail / detention centre.
        superintendent_name:  Superintendent / jailor name.
        agent_name:           BailBridge agent assigned to the case.
        agent_phone:          BailBridge agent contact number.

    Returns:
        PDF document as raw bytes, ready for upload or HTTP streaming.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )
    styles = _build_styles()
    story: list = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("NATIONAL LEGAL SERVICES AUTHORITY", styles["form_title"]))
    story.append(Paragraph("Bail Application Form — Under-Trial Prisoner Legal Aid", styles["form_subtitle"]))
    story.append(_divider(_SAFFRON, 2))
    story.append(Paragraph(
        f"BailBridge Case Reference: <b>{case_id}</b> &nbsp;|&nbsp; "
        f"Generated: {datetime.datetime.utcnow().strftime('%d-%m-%Y %H:%M UTC')}",
        styles["footer"],
    ))
    story.append(Spacer(1, 0.3 * cm))

    # ── Part A: Personal Information ──────────────────────────────────────────
    story.append(KeepTogether([
        Paragraph("PART A — Personal Information of Applicant", styles["section_heading"]),
        _kv_table(
            [
                ("Full Name",                 defendant_name),
                ("Father's / Spouse's Name",  father_or_spouse_name),
                ("Date of Birth",             dob),
                ("Gender",                    gender),
                ("Permanent Address",          address),
                ("District",                  district),
                ("State",                     state),
                ("Contact Phone",             phone),
                ("Aadhaar (last 4 digits)",   f"XXXX-XXXX-{aadhaar_last4}" if aadhaar_last4 else None),
            ],
            styles,
        ),
    ]))
    story.append(Spacer(1, 0.3 * cm))

    # ── Part B: Arrest & Custody Details ─────────────────────────────────────
    story.append(KeepTogether([
        Paragraph("PART B — Arrest and Custody Details", styles["section_heading"]),
        _kv_table(
            [
                ("FIR / Case Number",         fir_number),
                ("Registering Police Station", police_station),
                ("Date of Arrest",            date_of_arrest),
                ("Charge / Section",          charge_section),
                ("Offence Description",       charge_description),
                ("Detaining Jail / Centre",   jail_name),
                ("Superintendent / Jailor",   superintendent_name),
            ],
            styles,
        ),
    ]))
    story.append(Spacer(1, 0.3 * cm))

    # ── Part C: Court Information ─────────────────────────────────────────────
    story.append(KeepTogether([
        Paragraph("PART C — Court and Bail Information", styles["section_heading"]),
        _kv_table(
            [
                ("Court Name",            court_name),
                ("Next Hearing Date",     next_hearing_date),
                ("Bail Amount (INR)",     f"₹ {bail_amount:,.2f}" if bail_amount else "Not set / Awaiting order"),
            ],
            styles,
        ),
    ]))
    story.append(Spacer(1, 0.3 * cm))

    # ── Part D: Legal Aid Request ─────────────────────────────────────────────
    story.append(KeepTogether([
        Paragraph("PART D — Legal Aid Request", styles["section_heading"]),
        _kv_table(
            [
                ("Legal Aid Requested",  "Yes — Free Legal Aid under Section 12 NALSA Act" if legal_aid_requested else "No"),
                ("Ground / Reason",      reason_for_aid or ("Insufficient means / indigent applicant" if legal_aid_requested else "—")),
            ],
            styles,
        ),
    ]))
    story.append(Spacer(1, 0.3 * cm))

    # ── Part E: BailBridge Agent ──────────────────────────────────────────────
    if agent_name or agent_phone:
        story.append(KeepTogether([
            Paragraph("PART E — BailBridge Assigned Agent", styles["section_heading"]),
            _kv_table(
                [
                    ("Agent Name",    agent_name),
                    ("Agent Contact", agent_phone),
                ],
                styles,
            ),
        ]))
        story.append(Spacer(1, 0.3 * cm))

    # ── Declaration ───────────────────────────────────────────────────────────
    story.append(_divider(_NAVY, 0.5))
    story.append(Paragraph("DECLARATION BY APPLICANT", styles["section_heading"]))
    story.append(
        Paragraph(
            "I, the undersigned, do hereby solemnly declare that the information furnished above "
            "is true and correct to the best of my knowledge and belief. I understand that "
            "furnishing false information may render me liable to prosecution under applicable law. "
            "I further request the Hon'ble Legal Services Authority to consider my application for "
            "free legal aid and bail assistance under the Legal Services Authorities Act, 1987.",
            styles["declaration"],
        )
    )
    story.append(Spacer(1, 0.8 * cm))

    sig_table = Table(
        [
            ["_" * 35, "", "_" * 25, "", "_" * 20],
            ["Applicant / Guardian Signature", "", "Place", "", "Date"],
        ],
        colWidths=[6 * cm, 0.8 * cm, 5 * cm, 0.8 * cm, 4 * cm],
    )
    sig_table.setStyle(
        TableStyle([
            ("FONTSIZE",   (0, 1), (-1, 1), 8),
            ("TEXTCOLOR",  (0, 1), (-1, 1), colors.gray),
            ("FONTNAME",   (0, 1), (-1, 1), "Helvetica-Oblique"),
        ])
    )
    story.append(sig_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(_divider(_MID_GRAY, 0.5))
    story.append(
        Paragraph(
            "Generated by BailBridge · Powered by NALSA Legal Aid Framework · "
            "Confidential Legal Document — Not for Public Distribution",
            styles["footer"],
        )
    )

    doc.build(story)
    return buffer.getvalue()
