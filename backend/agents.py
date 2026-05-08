"""
BailBridge — Unified Agent Squad (Consolidated)

Contains all specialized legal agents:
1. Base Agent (Foundation)
2. Jatayu (Classifier & Multilingual)
3. Intake Agent (Interview & Normalization)
4. Bail Architect (Statutory Reasoning)
5. Ethics Guardian (Compliance Interceptor)
6. Hearing Tracker & e-Seva Bridge
"""

import asyncio
import logging
import json
import datetime
import google.generativeai as genai
from config import settings
from db.firebase_config import get_db
from websocket_handler import sio
from utils import (
    get_evidence_prompt, 
    find_nearest_court, 
    extract_hearing_details, 
    send_internal_notification
)

logger = logging.getLogger("bailbridge.agents")

# ── 1. BASE AGENT ─────────────────────────────────────────────────────────────

class BailBridgeAgent:
    def __init__(self):
        self.db = get_db()
        self.sio = sio

    async def _translate_if_needed(self, case_id: str, text: str) -> str:
        """Translates AI messages to the user's preferred language."""
        case_doc = self.db.collection("cases").document(case_id).get()
        preferred_lang = case_doc.to_dict().get("preferred_language", "English") if case_doc.exists else "English"
        
        if preferred_lang.lower() == "english":
            return text
            
        try:
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"Translate the following legal assistant message into {preferred_lang}. Maintain the tone and all specific section numbers (e.g., BNSS 479). Message: {text}"
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return text

    async def send_message(self, case_id: str, text: str, sender_type: str = "ai"):
        from websocket_handler import _persist_message, _case_room
        final_text = await self._translate_if_needed(case_id, text) if sender_type == "ai" else text
        await _persist_message(case_id, "bailbridge_ai", final_text, sender_type)
        room = _case_room(case_id)
        await self.sio.emit("new_message", {
            "case_id": case_id, "text": final_text, "from": "BailBridge AI", "sender_type": sender_type
        }, room=room)
        logger.info(f"[Agent] Sent {sender_type} message to {case_id}")

# ── 2. JATAYU (CLASSIFIER & SAHAYAK) ──────────────────────────────────────────

class JatayuAgent(BailBridgeAgent):
    async def classify_and_route(self, case_id: str, message: str):
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"Analyze user message: '{message}'. Return JSON with 'category' (NEW_ARREST, ESEVA_HELP, HEARING_TRACKER, GENERAL_CHAT) and 'language' (User language)."
        
        try:
            res = model.generate_content(prompt)
            data = json.loads(res.text.replace("```json", "").replace("```", "").strip())
            category, lang = data.get("category", "GENERAL_CHAT"), data.get("language", "English")
            self.db.collection("cases").document(case_id).update({"preferred_language": lang})
            
            if "NEW_ARREST" in category: await intake_agent.process_answer(case_id, message)
            elif "ESEVA_HELP" in category: await eseva_bridge.handle_query(case_id, message)
            elif "HEARING_TRACKER" in category: await hearing_tracker.update_hearing_date(case_id, message)
            else: await self.send_message(case_id, "I'm here to help. Are you reporting a new arrest or looking for a court?")
        except Exception as e:
            logger.error(f"Jatayu routing error: {e}")

    async def generate_sahayak_script(self, case_id: str) -> str:
        case_data = self.db.collection("cases").document(case_id).get().to_dict() or {}
        lang = case_data.get("preferred_language", "English")
        prompt = f"Generate a 3-point bail hearing script in English and a phonetic version in {lang} based on strategy: {case_data.get('bail_strategy')}."
        try:
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            script = model.generate_content(prompt).text.strip()
            self.db.collection("cases").document(case_id).update({"sahayak_script": script})
            return script
        except: return "Script generation failed."

# ── 3. INTAKE AGENT (INTERVIEW) ───────────────────────────────────────────────

class IntakeAgent(BailBridgeAgent):
    QUESTIONS = [
        "Full name of person in custody?", "Police Station?", "FIR Number?", 
        "Date of arrest? (DD-MM-YYYY)", "First-time offender? (Yes/No)", 
        "Special Grounds? (Woman/Child/Sick)", "Max Punishment?", "Incident Description?"
    ]

    async def _normalize_answer(self, case_id: str, answer: str, field: str) -> str:
        lang = self.db.collection("cases").document(case_id).get().to_dict().get("preferred_language", "English")
        if lang.lower() == "english": return answer
        try:
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"Convert '{answer}' from {lang} to English for legal field '{field}'. Return only the value."
            return model.generate_content(prompt).text.strip()
        except: return answer

    async def process_answer(self, case_id: str, answer: str):
        case_ref = self.db.collection("cases").document(case_id)
        data = case_ref.get().to_dict()
        step = data.get("intake_step", 0)
        fields = ["defendant_name", "police_station", "fir_number", "date_of_arrest", "is_first_offender", "special_grounds", "punishment_severity", "incident_description"]
        
        if step < len(fields):
            norm = await self._normalize_answer(case_id, answer, fields[step])
            intake = data.get("intake_data", {})
            intake[fields[step]] = norm
            case_ref.update({"intake_data": intake, "intake_step": step + 1})
            
            if step + 1 < len(self.QUESTIONS):
                await self.send_message(case_id, self.QUESTIONS[step + 1])
            else:
                await self.send_message(case_id, "Intake complete. Analyzing strategy...")
                case_ref.update({"status": "intake_complete"})
                asyncio.create_task(bail_agent.analyze_strategy(case_id))

# ── 4. BAIL ARCHITECT (REASONING) ─────────────────────────────────────────────

class BailArchitectAgent(BailBridgeAgent):
    async def analyze_strategy(self, case_id: str):
        from pdf_gen import generate_bail_application
        case_data = self.db.collection("cases").document(case_id).get().to_dict()
        intake = case_data.get("intake_data", {})
        
        # Statutory Logic (Sec 479/480 BNSS)
        severity = intake.get("punishment_severity", "").lower()
        is_severe = "life" in severity or "death" in severity
        strategy = "Non-Bailable (Judicial Discretion)"
        
        if not is_severe and "date_of_arrest" in intake:
            # Simplified math for brevity
            strategy = "Mandatory Bail (Section 479 BNSS)"
            
        # Refine with Special Grounds
        if any(kw in intake.get("special_grounds", "").lower() for kw in ["woman", "sick", "child"]):
            strategy = "Special Grounds (Section 480 BNSS)"

        # Generate PDF
        pdf_path = generate_bail_application(
            case_id=case_id, defendant_name=intake.get("defendant_name", "Applicant"),
            strategy_type=strategy, legal_grounds=f"Eligibility under {strategy}.",
            preferred_language=case_data.get("preferred_language", "English")
        )
        
        self.db.collection("cases").document(case_id).update({
            "bail_strategy": strategy, "bail_pdf_url": f"file:///{pdf_path}", "status": "bail_strategy_ready"
        })
        
        msg = f"Bail Strategy Determined: **{strategy}**.\n{get_evidence_prompt(case_id)}"
        await ethics_guardian.intercept_and_send(case_id, msg)

# ── 5. ETHICS GUARDIAN (COMPLIANCE) ───────────────────────────────────────────

class EthicsGuardianAgent(BailBridgeAgent):
    DISCLAIMER = "\n\n--- LEGAL DISCLAIMER ---\nThis is an AI-generated draft. Not legal advice."
    async def intercept_and_send(self, case_id: str, text: str):
        await self.send_message(case_id, text + self.DISCLAIMER)

# ── 6. SQUAD MEMBERS ──────────────────────────────────────────────────────────

class ESevaBridge(BailBridgeAgent):
    async def handle_query(self, case_id: str, text: str):
        info = find_nearest_court(text)
        await self.send_message(case_id, f"Nearest Court: {info['nearest_court']}\nMaps: {info['link']}")

class HearingTracker(BailBridgeAgent):
    async def update_hearing_date(self, case_id: str, text: str):
        info = extract_hearing_details(text)
        if info:
            self.db.collection("cases").document(case_id).update({"next_hearing": info["date"]})
            await self.send_message(case_id, f"Hearing updated to {info['date']}.")
        else: await self.send_message(case_id, "Could not detect date.")

# Singletons
jatayu_agent = JatayuAgent()
intake_agent = IntakeAgent()
bail_agent = BailArchitectAgent()
ethics_guardian = EthicsGuardianAgent()
eseva_bridge = ESevaBridge()
hearing_tracker = HearingTracker()
