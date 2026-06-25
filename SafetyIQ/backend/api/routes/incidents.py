"""
SafetyIQ — Incidents Routes
============================
REST endpoints for incident history and pattern intelligence.

Endpoints:
  GET  /api/v1/incidents               — Incident history + stats
  GET  /api/v1/incidents/patterns      — RAG-powered pattern analysis
  GET  /api/v1/incidents/{incident_id} — Single incident detail
  POST /api/v1/incidents/analyze       — Trigger pattern analysis for current conditions

Author: SafetyIQ Team
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents"])


# ─── Models ───────────────────────────────────────────────────────────────────

class PatternAnalysisRequest(BaseModel):
    zone: str
    active_permit_types: list[str] = []
    sensor_anomalies: list[dict] = []
    maintenance_gaps: list[str] = []
    time_of_day: str = "MORNING"
    workforce_size: int = 50


# ─── Static incident corpus (mirrors incident_rag_agent.py seed data) ─────────

INCIDENT_HISTORY: list[dict[str, Any]] = [
    {
        "incident_id": "INC-2025-001",
        "date": "2025-01-15",
        "plant": "Visakhapatnam Steel Plant",
        "zone": "Coke Oven Battery",
        "type": "FATALITY",
        "description": (
            "Eight workers killed when entrapped gases triggered explosion in coke oven battery. "
            "Gas pressure sensor warnings existed but were not acted upon. Workers were conducting "
            "routine maintenance during abnormal process conditions."
        ),
        "root_causes": [
            "Absence of intelligent alert correlation",
            "Manual handoff failure during gas pressure warning",
            "Inadequate pre-entry gas testing protocol",
        ],
        "contributing_factors": [
            "Active work permit during abnormal operations",
            "Shift changeover 15 minutes prior",
            "Gas detector calibration 45 days overdue",
            "No confined space rescue plan",
        ],
        "regulations_violated": [
            "OISD 105 Section 4.3",
            "Factory Act 1948 Section 36A",
            "OISD 116 Section 5.2",
        ],
        "fatalities": 8,
        "injuries": 2,
        "recurrence_count": 3,
    },
    {
        "incident_id": "INC-2024-047",
        "date": "2024-08-22",
        "plant": "Bhilai Steel Plant",
        "zone": "Blast Furnace Zone",
        "type": "NEAR_MISS",
        "description": (
            "Near-miss: hot work welding commenced 8 metres from area with elevated CO readings (340ppm). "
            "Worker noticed sparks near gas measurement point and halted work. "
            "Isolation barrier had not been formally confirmed in permit."
        ),
        "root_causes": [
            "Permit issued without verifying adjacent zone sensor status",
            "No automated proximity check between permit zones and live sensor data",
        ],
        "contributing_factors": [
            "Incomplete isolation verification",
            "Supervisor busy with shift handover",
            "CO sensor alarm set at 400ppm (above OISD recommended 200ppm)",
        ],
        "regulations_violated": [
            "OISD 105 Section 6.1",
            "Factory Act 1948 Section 36",
        ],
        "fatalities": 0,
        "injuries": 0,
        "recurrence_count": 7,
    },
    {
        "incident_id": "INC-2024-018",
        "date": "2024-03-11",
        "plant": "Rourkela Steel Plant",
        "zone": "Chemical Storage",
        "type": "INJURY",
        "description": (
            "Pressure relief valve (PRV) on acid storage tank failed during routine operations. "
            "Tank pressure had been trending upward for 6 hours. PRV was 34 days overdue for inspection. "
            "Three workers suffered chemical burns during emergency depressurisation."
        ),
        "root_causes": [
            "Overdue PRV inspection not flagged as critical risk",
            "No automated alert correlating sensor trend with maintenance backlog",
        ],
        "contributing_factors": [
            "Maintenance schedule not integrated with process monitoring",
            "Pressure trend visible in SCADA but not correlated to inspection due date",
            "Weekend skeleton crew on site",
        ],
        "regulations_violated": [
            "OISD 118 Section 8.4",
            "Factory Act 1948 Section 31",
        ],
        "fatalities": 0,
        "injuries": 3,
        "recurrence_count": 5,
    },
    {
        "incident_id": "INC-2023-092",
        "date": "2023-11-05",
        "plant": "IISCO Steel Plant",
        "zone": "Confined Space",
        "type": "FATALITY",
        "description": (
            "One worker asphyxiated during cleaning of gas duct. Oxygen reading at duct entry was 17.8%. "
            "Worker entered without SCBA despite oxygen deficiency reading. "
            "Permit-to-work did not explicitly mandate SCBA for O2 levels below 19.5%."
        ),
        "root_causes": [
            "PTW did not translate oxygen reading into mandatory PPE requirement",
            "No automated PPE mandate trigger on O2 deficiency",
        ],
        "contributing_factors": [
            "SCBA availability (2 units for 8 workers)",
            "Worker not trained on oxygen deficiency signs",
            "Supervisor signed off PTW without verifying O2 level against OISD standard",
        ],
        "regulations_violated": [
            "OISD 116 Section 4.1",
            "Factory Act 1948 Section 36A",
            "DGMS Circular 2019-03",
        ],
        "fatalities": 1,
        "injuries": 0,
        "recurrence_count": 4,
    },
    {
        "incident_id": "INC-2023-031",
        "date": "2023-04-18",
        "plant": "Tata Steel Jamshedpur",
        "zone": "Hot Strip Mill",
        "type": "DANGEROUS_OCCURRENCE",
        "description": (
            "Simultaneous hot work (welding) and confined space entry permits active in adjacent zones "
            "separated by 12 metres. Flash fire occurred when welding sparks ignited vapors from confined "
            "space cleaning solvents. Full evacuation required."
        ),
        "root_causes": [
            "No SIMOPs assessment conducted",
            "Permit issuing officers for two operations had no cross-communication",
        ],
        "contributing_factors": [
            "No centralised permit visibility system",
            "12-metre separation considered adequate without atmospheric testing",
            "Wind direction not factored into SIMOPs assessment",
        ],
        "regulations_violated": [
            "OISD 105 Section 7.2",
            "Factory Act 1948 Section 40",
        ],
        "fatalities": 0,
        "injuries": 5,
        "recurrence_count": 6,
    },
]

# Pre-computed patterns for demo (Production: generated by IncidentPatternAgent)
PRECOMPUTED_PATTERNS: list[dict[str, Any]] = [
    {
        "pattern_id": "PAT-A3F2B1C0",
        "pattern_name": "PTW-Sensor Disconnect: Permits Issued Without Live Sensor Verification",
        "description": (
            "Across 7 incidents, permits were issued without cross-checking live sensor readings "
            "in the target or adjacent zones. The PTW system and sensor data exist in separate silos "
            "with no automated integration layer."
        ),
        "recurrence_count": 7,
        "severity_potential": "FATAL",
        "similar_incidents": ["INC-2025-001", "INC-2024-047", "INC-2023-092"],
        "current_condition_match": 0.91,
        "regulatory_gaps": [
            "OISD 105 Section 6.1: Isolation verification not automated against live sensor state",
            "OISD 116 Section 4.1: SCBA mandate not triggered by O2 sensor reading in PTW system",
        ],
        "prevention_priorities": [
            "Block PTW issuance if target or adjacent zone sensors are in WARNING/CRITICAL state",
            "Auto-mandate SCBA in PTW whenever O2 reading < 19.5% in the entry zone",
            "Integrate CMMS inspection records with PTW — block permits when safety-critical equipment is overdue",
        ],
        "ai_analysis": (
            "This pattern persists because PTW issuance is a human workflow and sensor monitoring is a "
            "separate digital system with no enforcement linkage. Safety officers rely on manual checks "
            "that are easily skipped under time pressure, shift changeovers, or workload peaks. "
            "The fix is technical: PTW systems must programmatically query live sensor state before "
            "generating a permit. Current conditions at Vizag Steel Complex show 91% similarity to "
            "this pattern: PTW-2847 (confined space) active in a zone where O2 is below threshold, "
            "PTW-2851 (hot work) active with elevated CO and H2S in zone."
        ),
        "timestamp": datetime.utcnow().isoformat(),
    },
    {
        "pattern_id": "PAT-B8D4E2F1",
        "pattern_name": "Shift Changeover Safety Gap",
        "description": (
            "Critical safety information — active permits, sensor anomalies, and near-miss events — "
            "is not reliably transferred during shift handovers. The 15-minute changeover window "
            "consistently appears as a contributing factor in 5 of the retrieved incidents."
        ),
        "recurrence_count": 5,
        "severity_potential": "SERIOUS_INJURY",
        "similar_incidents": ["INC-2025-001", "INC-2024-047", "INC-2023-031"],
        "current_condition_match": 0.78,
        "regulatory_gaps": [
            "DGMS Circular 2019-03: No standardised digital handover checklist requirement",
            "OISD 105 Section 4.3: Permit re-validation not required after shift change",
        ],
        "prevention_priorities": [
            "Mandatory digital handover checklist with incoming officer sign-off on all active permits",
            "Block shift changeover in SCADA if any sensor is in CRITICAL state without acknowledged action plan",
            "Auto-generate shift handover safety brief from live sensor + permit state",
        ],
        "ai_analysis": (
            "The shift changeover gap is a known organisational vulnerability in process safety. "
            "Incoming shift workers lack situational awareness built up by departing workers over hours. "
            "This is compounded when handovers are rushed, verbal-only, or occur during active sensor alerts. "
            "Current plant state shows shift changeover is imminent with O2 deficiency in B7 and elevated "
            "H2S/CO in Coke Oven Battery A — exactly the compound condition that preceded INC-2025-001."
        ),
        "timestamp": datetime.utcnow().isoformat(),
    },
    {
        "pattern_id": "PAT-C1A9D7E3",
        "pattern_name": "Overdue Maintenance Under Elevated Process Load",
        "description": (
            "Equipment continues to operate beyond its inspection interval while process parameters "
            "(pressure, temperature) are elevated. The combination of degraded equipment + high load "
            "has caused 5 incidents ranging from near-misses to serious injuries."
        ),
        "recurrence_count": 5,
        "severity_potential": "DANGEROUS_OCCURRENCE",
        "similar_incidents": ["INC-2024-018"],
        "current_condition_match": 0.82,
        "regulatory_gaps": [
            "OISD 118 Section 8.4: No automated enforcement of 75% pressure limit when inspection is overdue",
            "Factory Act 1948 Section 31: Pressure plant register not integrated with SCADA",
        ],
        "prevention_priorities": [
            "Auto-alert when overdue equipment is operating above 75% design capacity",
            "Integrate CMMS inspection schedules with real-time SCADA process readings",
            "Mandatory SCADA setpoint reduction when equipment exceeds inspection overdue threshold",
        ],
        "ai_analysis": (
            "PRV-004 in Chemical Storage is currently 17 days overdue for inspection with pressure "
            "at 8.5 bar and rising — a direct match to INC-2024-018 (34 days overdue, PRV failure, "
            "3 injured). OISD 118 Section 8.4 requires operation at ≤75% design pressure when "
            "inspection is overdue, but this is not being enforced. SCADA shows a rising pressure trend "
            "with no active corrective action."
        ),
        "timestamp": datetime.utcnow().isoformat(),
    },
]


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def get_incident_history():
    """Historical incident statistics and recent incident log."""
    fatalities_ytd = sum(i["fatalities"] for i in INCIDENT_HISTORY if i["date"].startswith("2025"))
    injuries_ytd   = sum(i["injuries"]   for i in INCIDENT_HISTORY if i["date"].startswith("2025"))
    near_misses    = sum(1 for i in INCIDENT_HISTORY if i["type"] == "NEAR_MISS")
    dangerous_occ  = sum(1 for i in INCIDENT_HISTORY if i["type"] == "DANGEROUS_OCCURRENCE")

    top_patterns = [
        {"pattern": p["pattern_name"][:50], "recurrence": p["recurrence_count"], "last_occurrence": "2025-01-15"}
        for p in sorted(PRECOMPUTED_PATTERNS, key=lambda x: x["recurrence_count"], reverse=True)[:3]
    ]

    recent = [
        {
            "id": i["incident_id"],
            "date": i["date"],
            "type": i["type"],
            "zone": i["zone"],
            "description": i["description"][:120] + "...",
            "fatalities": i["fatalities"],
            "injuries": i["injuries"],
        }
        for i in sorted(INCIDENT_HISTORY, key=lambda x: x["date"], reverse=True)[:5]
    ]

    return {
        "total_incidents": len(INCIDENT_HISTORY),
        "fatalities_ytd": fatalities_ytd,
        "injuries_ytd": injuries_ytd,
        "near_misses_ytd": near_misses,
        "dangerous_occurrences_ytd": dangerous_occ,
        "top_patterns": top_patterns,
        "recent_incidents": recent,
    }


@router.get("/patterns")
async def get_incident_patterns():
    """Pre-computed incident patterns from RAG corpus."""
    return {
        "total_patterns": len(PRECOMPUTED_PATTERNS),
        "high_match_patterns": sum(1 for p in PRECOMPUTED_PATTERNS if p["current_condition_match"] >= 0.75),
        "patterns": sorted(PRECOMPUTED_PATTERNS, key=lambda x: x["current_condition_match"], reverse=True),
    }


@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """Full incident detail including root causes and corrective actions."""
    incident = next((i for i in INCIDENT_HISTORY if i["incident_id"] == incident_id), None)
    if not incident:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return incident


@router.post("/analyze")
async def analyze_patterns(request: PatternAnalysisRequest):
    """
    Trigger RAG-powered pattern analysis for current plant conditions.
    Production: calls IncidentPatternAgent.analyze_patterns().
    Demo: returns pre-computed patterns filtered by condition match.
    """
    # Filter patterns by relevance to requested zone/conditions
    relevant = [
        p for p in PRECOMPUTED_PATTERNS
        if p["current_condition_match"] >= 0.5
    ]

    return {
        "analysis_id": f"PAT-ANA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.utcnow().isoformat(),
        "conditions_analyzed": {
            "zone": request.zone,
            "active_permits": request.active_permit_types,
            "sensor_anomalies": len(request.sensor_anomalies),
            "maintenance_gaps": request.maintenance_gaps,
            "time_of_day": request.time_of_day,
        },
        "total_patterns": len(relevant),
        "high_match_patterns": sum(1 for p in relevant if p["current_condition_match"] >= 0.75),
        "patterns": sorted(relevant, key=lambda x: x["current_condition_match"], reverse=True),
    }