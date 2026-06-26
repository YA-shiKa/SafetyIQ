#!/usr/bin/env python3
"""
SafetyIQ — Mock Data Seed Script
==================================
Seeds the development environment with:
  1. Simulated plant state (matches plant_state.json)
  2. Incident corpus for RAG agent
  3. OISD/Factory Act regulatory clause corpus
  4. Runs a quick smoke-test of all agents

Usage:
    python scripts/seed_mock_data.py [--run-agents]

Author: SafetyIQ Team
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("seed")


# ─── Plant State ──────────────────────────────────────────────────────────────

def load_plant_state() -> dict:
    state_path = ROOT / "data" / "mock" / "plant_state.json"
    with open(state_path) as f:
        return json.load(f)


# ─── Regulatory Corpus ────────────────────────────────────────────────────────

REGULATORY_CORPUS = [
    {
        "id": "OISD105-4.3",
        "source": "OISD_105",
        "section": "4.3",
        "title": "Permit to Work — Confined Space Entry",
        "content": (
            "No person shall enter a confined space without a valid permit. "
            "The permit shall specify: (a) atmospheric testing results for O2, H2S, CO, and combustibles; "
            "(b) isolation status; (c) rescue equipment location; (d) communication protocol. "
            "Atmospheric testing must be repeated every 2 hours during occupancy."
        ),
        "applies_to": ["CONFINED_SPACE", "PTW"],
    },
    {
        "id": "OISD105-6.1",
        "source": "OISD_105",
        "section": "6.1",
        "title": "Isolation Verification",
        "content": (
            "Before commencing any hot work, electrical, or confined space operation, the area shall be "
            "physically isolated. The issuing authority shall verify and sign off isolation. "
            "Permit shall not be issued until isolation certificate is attached."
        ),
        "applies_to": ["HOT_WORK", "CONFINED_SPACE", "ELECTRICAL_ISOLATION"],
    },
    {
        "id": "OISD105-7.2",
        "source": "OISD_105",
        "section": "7.2",
        "title": "Simultaneous Operations (SIMOPs)",
        "content": (
            "A formal SIMOPs assessment must be conducted when high-risk permits (confined space, hot work, "
            "electrical isolation) are issued within 25 metres of each other. Assessment must identify "
            "hazardous interactions and establish minimum separation or temporal offset."
        ),
        "applies_to": ["SIMOPS", "HOT_WORK", "CONFINED_SPACE"],
    },
    {
        "id": "OISD116-4.1",
        "source": "OISD_116",
        "section": "4.1",
        "title": "Respiratory Protective Equipment",
        "content": (
            "Breathing apparatus (SCBA) is mandatory when O2 concentration is below 19.5% "
            "or H2S exceeds 10ppm or CO exceeds 200ppm. Minimum 2 standby persons must be present "
            "at entry point when SCBA is in use."
        ),
        "applies_to": ["OXYGEN_DEFICIENCY", "GAS_HAZARD", "CONFINED_SPACE"],
    },
    {
        "id": "OISD116-5.2",
        "source": "OISD_116",
        "section": "5.2",
        "title": "Gas Detector Calibration",
        "content": (
            "All portable and fixed gas detectors shall be calibrated at intervals not exceeding 90 days. "
            "Calibration records shall be maintained. Detectors overdue for calibration shall be taken "
            "out of service immediately."
        ),
        "applies_to": ["GAS_DETECTOR", "MAINTENANCE"],
    },
    {
        "id": "OISD118-8.4",
        "source": "OISD_118",
        "section": "8.4",
        "title": "Pressure Vessel Inspection",
        "content": (
            "All pressure vessels including pressure relief valves shall be inspected at intervals not "
            "exceeding: (a) External: 12 months; (b) Internal: 24 months; (c) Hydraulic test: 60 months. "
            "Where inspection is overdue, the vessel shall be operated at reduced pressure (max 75% design) "
            "pending inspection."
        ),
        "applies_to": ["PRESSURE_VESSEL", "MAINTENANCE"],
    },
    {
        "id": "FA1948-36A",
        "source": "FACTORY_ACT_1948",
        "section": "36A",
        "title": "Precautions Against Dangerous Fumes",
        "content": (
            "In any factory where any operation may produce dangerous fumes, the occupier shall provide: "
            "(a) means of testing atmosphere before entry; (b) reviving apparatus; "
            "(c) trained first-aid attendant. No person shall be required to enter any chamber where "
            "dangerous fumes may be present unless wearing breathing apparatus."
        ),
        "applies_to": ["GAS_HAZARD", "CONFINED_SPACE", "FUMES"],
    },
    {
        "id": "FA1948-31",
        "source": "FACTORY_ACT_1948",
        "section": "31",
        "title": "Pressure Plant",
        "content": (
            "Where in any factory, any plant or machinery or any part thereof is operated at a pressure "
            "above atmospheric pressure, effective measures shall be taken to ensure that the safe working "
            "pressure of such plant or machinery or part is not exceeded."
        ),
        "applies_to": ["PRESSURE_VESSEL", "MAINTENANCE"],
    },
    {
        "id": "DGMS-2019-03",
        "source": "DGMS",
        "section": "Circular 2019-03",
        "title": "Emergency Rescue Drill Frequency",
        "content": (
            "Emergency rescue drills shall be conducted at intervals not exceeding 6 months. "
            "Drills shall cover confined space rescue, gas leak response, and fire evacuation scenarios. "
            "Attendance records and outcomes shall be documented for DGMS inspection."
        ),
        "applies_to": ["EMERGENCY", "RESCUE", "DRILL"],
    },
]


# ─── Smoke Tests ──────────────────────────────────────────────────────────────

async def smoke_test_compliance_agent():
    """Quick smoke test of ComplianceAgent."""
    try:
        from backend.agents.compliance_agent import ComplianceAgent
        agent = ComplianceAgent()
        report = agent.run_checks()
        logger.info(f"✅ ComplianceAgent: score={report.overall_score}, findings={report.open_findings}")
        return True
    except Exception as e:
        logger.error(f"❌ ComplianceAgent failed: {e}")
        return False


async def smoke_test_compound_risk_agent():
    """Quick smoke test of CompoundRiskAgent with demo plant state."""
    try:
        from backend.agents.compound_risk_agent import CompoundRiskAgent, PlantState, SensorReading, PermitToWork, MaintenanceRecord
        now = datetime.utcnow()

        state = PlantState(
            timestamp=now,
            sensors=[
                SensorReading("S001", "Coke Oven Battery A", "H2S", 18.4, "ppm", 10, 20, now, "rising", 0.3),
                SensorReading("S005", "Confined Space B7", "O2", 17.2, "%", 19.5, 16.0, now, "falling", -0.15),
            ],
            active_permits=[
                PermitToWork("PTW-2847", "CONFINED_SPACE", "Confined Space B7",
                             now - timedelta(hours=1), now + timedelta(hours=3),
                             ["Worker A", "Worker B"], "SO-Sharma", isolation_confirmed=True),
            ],
            maintenance_records=[],
            shift_changeover_in_minutes=12,
            workers_on_site=53,
            last_incident_days=287,
        )

        agent = CompoundRiskAgent()
        events = await agent.analyze(state)
        logger.info(f"✅ CompoundRiskAgent: {len(events)} event(s) detected")
        for e in events:
            logger.info(f"   [{e.risk_level.value}] {e.title}")
        return True
    except Exception as e:
        logger.error(f"❌ CompoundRiskAgent failed: {e}")
        return False


async def smoke_test_permit_agent():
    """Quick smoke test of PermitIntelAgent."""
    try:
        from backend.agents.permit_intel_agent import PermitIntelAgent, PermitRequest, PermitType, LiveCondition

        agent = PermitIntelAgent()
        request = PermitRequest(
            permit_id="PTW-TEST-001",
            permit_type=PermitType.CONFINED_SPACE,
            zone="Confined Space B7",
            work_description="Routine gas duct cleaning",
            planned_workers=4,
            start_time=datetime.utcnow(),
            duration_hours=4.0,
            isolation_plan="LOTO applied on inlet valve",
            rescue_plan="2 standby with SCBA at entry",
            requested_by="Test Officer",
            checklist_items={"atmospheric_testing_o2": True, "atmospheric_testing_h2s": True},
        )
        condition = LiveCondition(
            zone="Confined Space B7",
            sensor_readings=[{"sensor_type": "O2", "value": 17.2, "threshold_warning": 19.5, "threshold_critical": 16.0, "trend": "falling"}],
            adjacent_zone_readings=[],
            active_permits_same_zone=[],
            active_permits_adjacent=[{"permit_id": "PTW-2851", "permit_type": "HOT_WORK", "zone": "Coke Oven Battery A"}],
            maintenance_alerts=[],
            shift_info={"changeover_in_minutes": 12},
        )
        validation = await agent.validate(request, condition)
        logger.info(f"✅ PermitIntelAgent: decision={validation.decision.value}, risk={validation.risk_score}")
        return True
    except Exception as e:
        logger.error(f"❌ PermitIntelAgent failed: {e}")
        return False


async def smoke_test_incident_rag_agent():
    """Quick smoke test of IncidentPatternAgent."""
    try:
        from backend.agents.incident_rag_agent import IncidentPatternAgent, CurrentCondition

        agent = IncidentPatternAgent()
        condition = CurrentCondition(
            zone="Coke Oven Battery A",
            active_permit_types=["CONFINED_SPACE", "HOT_WORK"],
            sensor_anomalies=[{"type": "H2S", "value": 18.4, "trend": "rising"}],
            maintenance_gaps=["PRV-004 inspection overdue 17 days"],
            time_of_day="SHIFT_CHANGE",
            workforce_size=53,
        )
        patterns = await agent.analyze_patterns(condition)
        logger.info(f"✅ IncidentPatternAgent: {len(patterns)} pattern(s) found")
        return True
    except Exception as e:
        logger.error(f"❌ IncidentPatternAgent failed: {e}")
        return False


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="SafetyIQ seed script")
    parser.add_argument("--run-agents", action="store_true", help="Run agent smoke tests")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("SafetyIQ — Development Seed Script")
    logger.info("=" * 60)

    # Load and validate plant state
    state = load_plant_state()
    logger.info(f"✅ Plant state loaded: {len(state['sensors'])} sensors, {len(state['permits'])} permits")
    logger.info(f"   Plant: {state['plant_config']['name']}")
    logger.info(f"   Workers on site: {state['plant_config']['total_workers_on_site']}")
    logger.info(f"   Shift changeover in: {state['plant_config']['shift_changeover_in_minutes']} minutes")

    logger.info(f"\n✅ Regulatory corpus: {len(REGULATORY_CORPUS)} clauses across OISD/Factory Act/DGMS")
    for r in REGULATORY_CORPUS:
        logger.info(f"   {r['source']} Section {r['section']}: {r['title']}")

    if args.run_agents:
        logger.info("\n--- Running agent smoke tests ---")
        logger.info("Note: Set ANTHROPIC_API_KEY env var for full AI feature tests.\n")

        results = await asyncio.gather(
            smoke_test_compliance_agent(),
            smoke_test_compound_risk_agent(),
            smoke_test_permit_agent(),
            smoke_test_incident_rag_agent(),
        )

        passed = sum(results)
        logger.info(f"\n{'='*60}")
        logger.info(f"Smoke tests: {passed}/{len(results)} passed")
        if passed < len(results):
            logger.warning("Some agents failed. Ensure all dependencies are installed.")
    else:
        logger.info("\nRun with --run-agents to smoke-test all agents.")

    logger.info("\n✅ Seed complete. Start the backend:")
    logger.info("   cd backend && uvicorn main:app --reload --port 8000")
    logger.info("\n✅ Then start the frontend:")
    logger.info("   cd frontend && npm install && npm run dev")
    logger.info("\n📊 Open: http://localhost:5173")


if __name__ == "__main__":
    asyncio.run(main())