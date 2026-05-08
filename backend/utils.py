"""
BailBridge — Unified Utilities (Consolidated)

Includes:
1. Evidence Checker (Vault Validation)
2. Court Utils (e-Seva Bridge & Hearing Tracker Regex)
3. Internal Notifications
"""

import os
import re
import datetime
from typing import Optional, List, Dict

# ── 1. EVIDENCE CHECKER ───────────────────────────────────────────────────────

def check_missing_evidence(case_id: str) -> List[str]:
    """
    Checks the storage vault for missing FIR and ID documents.
    """
    evidence_path = os.path.join("storage", case_id)
    if not os.path.exists(evidence_path):
        return ["FIR Copy", "ID Proof"]
    
    files = os.listdir(evidence_path)
    missing = []
    if not any("fir" in f.lower() for f in files):
        missing.append("FIR Copy")
    if not any(f.lower().startswith("id") or "aadhar" in f.lower() for f in files):
        missing.append("ID Proof")
    
    return missing

def get_evidence_prompt(case_id: str) -> str:
    """
    Returns an urgent prompt if zero documents are found, or a checklist if some are missing.
    """
    missing = check_missing_evidence(case_id)
    if not missing:
        return ""
    
    evidence_path = os.path.join("storage", case_id)
    if not os.path.exists(evidence_path) or not os.listdir(evidence_path):
        return "Warning: Without an FIR copy or ID Proof, this bail draft cannot be submitted to the court. Please use the upload button below."
        
    return f"To finalize your official bail draft, please upload your: {', '.join(missing)}."

def get_enclosures_list(case_id: str) -> List[str]:
    """Returns a simple list of files in the vault."""
    evidence_path = os.path.join("storage", case_id)
    if not os.path.exists(evidence_path):
        return ["(No documents uploaded)"]
    files = os.listdir(evidence_path)
    return [f"• {f}" for f in files] if files else ["(No documents uploaded)"]

def get_detailed_enclosures(case_id: str) -> List[Dict]:
    """Returns a detailed list for the PDF table."""
    evidence_path = os.path.join("storage", case_id)
    files = os.listdir(evidence_path) if os.path.exists(evidence_path) else []
    
    items = [
        {"name": "FIR Copy / Complaint", "status": "Attached" if any("fir" in f.lower() for f in files) else "MISSING"},
        {"name": "Identity Proof (Aadhar/Voter)", "status": "Attached" if any(f.lower().startswith("id") or "aadhar" in f.lower() for f in files) else "MISSING"},
        {"name": "Custody Certificate", "status": "AI-Generated (Included)"}
    ]
    return items

# ── 2. COURT & HEARING UTILS ──────────────────────────────────────────────────

def find_nearest_court(location_query: str) -> Dict[str, str]:
    """e-Seva Bridge: Maps a Police Station or query to the nearest District Court."""
    query = location_query.lower()
    mapping = {
        "tihar": "Patiala House Court / Rohini District Court",
        "hauz khas": "Saket District Court",
        "connaught place": "Patiala House Court",
        "chandni chowk": "Tis Lazari Court",
        "dwarka": "Dwarka District Court",
    }
    for key, court in mapping.items():
        if key in query:
            return {"nearest_court": court, "link": f"https://www.google.com/maps/search/{court.replace(' ', '+')}"}
    return {"nearest_court": "District Court (Verify Jurisdiction)", "link": "#"}

def extract_hearing_details(text: str) -> Optional[Dict[str, str]]:
    """Hearing Tracker: Scans text for dates/times."""
    date_pattern = r'(\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b)'
    month_pattern = r'(\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b)'
    time_pattern = r'(\b\d{1,2}:\d{2}(?:\s?[AaPp][Mm])?\b)'
    
    date_match = re.search(date_pattern, text, re.IGNORECASE) or re.search(month_pattern, text, re.IGNORECASE)
    time_match = re.search(time_pattern, text, re.IGNORECASE)
    
    if date_match:
        return {"date": date_match.group(1), "time": time_match.group(1) if time_match else "10:00 AM"}
    return None

# ── 3. INTERNAL NOTIFICATIONS ─────────────────────────────────────────────────

def send_internal_notification(user_id: str, title: str, message: str, msg_type: str = "general"):
    """
    Simulates sending an internal push notification or dashboard alert.
    """
    print(f"[Notify] [{msg_type.upper()}] To User {user_id}: {title} - {message}")
