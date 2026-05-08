"""
BailBridge — Unified Logic Audit (Consolidated)
"""
import asyncio
import datetime
from agents import jatayu_agent, bail_agent, intake_agent
from db import get_db

async def run_audit():
    db = get_db()
    print(">>> Starting Consolidated Logic Audit...")
    
    # Scenario 1: First-time Offender (Mandatory Bail)
    case_id = "AUDIT-PASS"
    db.collection("cases").document(case_id).set({
        "case_id": case_id,
        "preferred_language": "Hindi",
        "intake_data": {
            "defendant_name": "Aman", "date_of_arrest": "01-01-2024",
            "is_first_offender": "Yes", "punishment_severity": "3 years"
        },
        "status": "intake_complete"
    })
    
    await bail_agent.analyze_strategy(case_id)
    print(f"[Audit] {case_id} complete.")

if __name__ == "__main__":
    asyncio.run(run_audit())
