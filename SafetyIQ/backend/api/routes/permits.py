"""
SafetyIQ — Permits Routes
==========================
REST endpoints for Permit-to-Work management.

Endpoints:
  GET  /api/v1/permits/active          — All active permits
  GET  /api/v1/permits/{permit_id}     — Single permit detail
  POST /api/v1/permits/validate        — AI validation against live conditions
  POST /api/v1/permits/{id}/suspend    — Suspend an active permit
  POST /api/v1/permits/{id}/close      — Close a completed permit
  GET  /api/v1/permits/simops          — Current SIMOPs assessment

Author: SafetyIQ Team
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/permits", tags=["Permits"])


# ─── Models ───────────────────────────────────────────────────────────────────

class PermitValidationRequest(BaseModel):
    permit_id: str
    permit_type: str
    zone: str
    requested_by: str
    planned_workers: int
    start_time: str
    duration_hours: float
    work_description: str = ""
    isolation_plan: str = ""
    rescue_plan: str = ""
    checklist_items: dict[str, bool] = {}


class PermitActionRequest(BaseModel):
    actioned_by: str
    reason: str = ""


# ─── Mock permit store (Production: PostgreSQL) ───────────────────────────────

_now = datetime.utcnow()

ACTIVE_PERMITS: list[dict[str, Any]] = [
    {
        "permit_id": "PTW-2847",
        "type": "CONFINED_SPACE",
        "zone": "Confined Space B7",
        "workers": 4,
        "worker_names": ["Rajesh Kumar", "Suresh Patel", "Anil Singh", "Vijay Rao"],
        "issued_by": "SO-Sharma",
        "issuing_officer": "Rajan Sharma",
        "start_time": (_now - timedelta(hours=1)).isoformat(),
        "end_time": (_now + timedelta(hours=3)).isoformat(),
        "status": "ACTIVE",
        "isolation_confirmed": True,
        "isolation_cert_attached": False,
        "atmospheric_test_done": True,
        "retest_interval_compliant": False,
        "rescue_plan": True,
        "scba_units_available": 2,
        "checklist_completion": 0.67,
        "risk_level": "CRITICAL",
    },
    {
        "permit_id": "PTW-2851",
        "type": "HOT_WORK",
        "zone": "Coke Oven Battery A",
        "workers": 2,
        "worker_names": ["Mohan Welder", "Ram Helper"],
        "issued_by": "SO-Patel",
        "issuing_officer": "Deepak Patel",
        "start_time": (_now - timedelta(minutes=30)).isoformat(),
        "end_time": (_now + timedelta(hours=2)).isoformat(),
        "status": "ACTIVE",
        "isolation_confirmed": False,
        "isolation_cert_attached": False,
        "atmospheric_test_done": True,
        "retest_interval_compliant": True,
        "rescue_plan": True,
        "scba_units_available": 0,
        "checklist_completion": 0.50,
        "risk_level": "HIGH",
    },
    {
        "permit_id": "PTW-2849",
        "type": "ELECTRICAL_ISOLATION",
        "zone": "Hot Strip Mill",
        "workers": 2,
        "worker_names": ["Electrical Tech A", "Electrical Tech B"],
        "issued_by": "SO-Kumar",
        "issuing_officer": "Sunil Kumar",
        "start_time": (_now - timedelta(hours=2)).isoformat(),
        "end_time": (_now + timedelta(hours=1)).isoformat(),
        "status": "ACTIVE",
        "isolation_confirmed": True,
        "isolation_cert_attached": True,
        "atmospheric_test_done": True,
        "retest_interval_compliant": True,
        "rescue_plan": True,
        "scba_units_available": 0,
        "checklist_completion": 1.0,
        "risk_level": "MEDIUM",
    },
    {
        "permit_id": "PTW-2853",
        "type": "CONFINED_SPACE",
        "zone": "Raw Material Bay",
        "workers": 3,
        "worker_names": ["Worker X", "Worker Y", "Worker Z"],
        "issued_by": "SO-Singh",
        "issuing_officer": "Pradeep Singh",
        "start_time": (_now - timedelta(minutes=15)).isoformat(),
        "end_time": (_now + timedelta(hours=4)).isoformat(),
        "status": "SUSPENDED",
        "isolation_confirmed": False,
        "isolation_cert_attached": False,
        "atmospheric_test_done": False,
        "retest_interval_compliant": False,
        "rescue_plan": False,
        "scba_units_available": 1,
        "checklist_completion": 0.17,
        "risk_level": "CRITICAL",
        "suspension_reason": "Missing pre-entry atmospheric test and rescue plan (OISD 105 Section 4.3)",
    },
]

_permit_history: list[dict] = []


# ─── Sensor state helper (mirrors main.py simulator) ──────────────────────────

ZONE_SENSOR_STATE: dict[str, list[dict]] = {
    "Coke Oven Battery A": [
        {"sensor_type": "H2S",  "value": 18.4, "unit": "ppm", "threshold_warning": 10,  "threshold_critical": 20,  "trend": "rising"},
        {"sensor_type": "CO",   "value": 312,  "unit": "ppm", "threshold_warning": 200, "threshold_critical": 400, "trend": "rising"},
    ],
    "Confined Space B7": [
        {"sensor_type": "O2",   "value": 17.2, "unit": "%",   "threshold_warning": 19.5,"threshold_critical": 16.0,"trend": "falling"},
    ],
    "Chemical Storage": [
        {"sensor_type": "PRESSURE", "value": 8.5, "unit": "bar", "threshold_warning": 10, "threshold_critical": 12, "trend": "rising"},
    ],
    "Hot Strip Mill": [
        {"sensor_type": "TEMP", "value": 820, "unit": "°C", "threshold_warning": 900, "threshold_critical": 1000, "trend": "stable"},
    ],
    "Raw Material Bay": [
        {"sensor_type": "CO", "value": 45, "unit": "ppm", "threshold_warning": 200, "threshold_critical": 400, "trend": "stable"},
    ],
}

SIMOPS_RISK_MATRIX: dict[tuple[str, str], str] = {
    ("HOT_WORK", "CONFINED_SPACE"): "CRITICAL",
    ("HOT_WORK", "CHEMICAL_HANDLING"): "HIGH",
    ("ELECTRICAL_ISOLATION", "CONFINED_SPACE"): "HIGH",
    ("RADIOGRAPHY", "HEIGHT_WORK"): "MEDIUM",
    ("EXCAVATION", "HEIGHT_WORK"): "MEDIUM",
}


def _check_sensor_blocking(permit_type: str, zone: str) -> tuple[list[str], list[str]]:
    """Deterministic sensor-based blocking and condition checks."""
    sensors = ZONE_SENSOR_STATE.get(zone, [])
    blocking, conditions = [], []

    sensor_map = {s["sensor_type"]: s for s in sensors}

    if permit_type == "CONFINED_SPACE":
        if "O2" in sensor_map:
            o2 = sensor_map["O2"]["value"]
            if o2 < 16.0:
                blocking.append(f"O₂ critically low: {o2}% — entry PROHIBITED below 16% (OISD 116)")
            elif o2 < 19.5:
                blocking.append(f"O₂ below safe minimum: {o2}% — SCBA mandatory, standby required (OISD 116 Section 4.1)")
        if "H2S" in sensor_map and sensor_map["H2S"]["value"] >= 20:
            blocking.append(f"H₂S at {sensor_map['H2S']['value']}ppm exceeds IDLH — evacuation required")
        elif "H2S" in sensor_map and sensor_map["H2S"]["value"] >= 10:
            conditions.append(f"H₂S at {sensor_map['H2S']['value']}ppm — SCBA mandatory (OISD 116 Section 4.1)")
        if "CO" in sensor_map and sensor_map["CO"]["value"] >= 200:
            conditions.append(f"CO at {sensor_map['CO']['value']}ppm — respiratory protection mandatory")

    elif permit_type == "HOT_WORK":
        for gas in ("H2S", "CO", "CH4"):
            if gas in sensor_map and sensor_map[gas]["value"] >= sensor_map[gas]["threshold_warning"]:
                blocking.append(
                    f"Flammable/toxic gas {gas} at {sensor_map[gas]['value']}{sensor_map[gas]['unit']} "
                    f"in hot work zone — isolation must be verified (OISD 105 Section 6.1)"
                )

    return blocking, conditions


def _check_simops(permit_type: str, zone: str) -> list[str]:
    """Check for dangerous simultaneous operations."""
    conflicts = []
    active = [p for p in ACTIVE_PERMITS if p["status"] == "ACTIVE"]
    for existing in active:
        combo = (permit_type, existing["type"])
        combo_rev = (existing["type"], permit_type)
        risk = SIMOPS_RISK_MATRIX.get(combo) or SIMOPS_RISK_MATRIX.get(combo_rev)
        if risk:
            zone_note = "" if existing["zone"] == zone else f" (adjacent: {existing['zone']})"
            conflicts.append(
                f"{risk}: {permit_type} + {existing['type']} permit {existing['permit_id']}{zone_note} "
                f"— SIMOPs assessment mandatory (OISD 105 Section 7.2)"
            )
    return conflicts


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/active")
async def get_active_permits():
    """All currently active and suspended permits."""
    active = [p for p in ACTIVE_PERMITS if p["status"] in ("ACTIVE", "SUSPENDED")]
    return {
        "permits": active,
        "total": len(active),
        "active_count": sum(1 for p in active if p["status"] == "ACTIVE"),
        "suspended_count": sum(1 for p in active if p["status"] == "SUSPENDED"),
        "critical_count": sum(1 for p in active if p["risk_level"] == "CRITICAL"),
        "missing_isolation": sum(1 for p in active if not p["isolation_cert_attached"]),
    }


@router.get("/simops")
async def get_simops_assessment():
    """Current SIMOPs risk assessment for all concurrent high-risk permits."""
    HIGH_RISK = {"CONFINED_SPACE", "HOT_WORK", "ELECTRICAL_ISOLATION", "EXCAVATION"}
    active_high_risk = [
        p for p in ACTIVE_PERMITS
        if p["status"] == "ACTIVE" and p["type"] in HIGH_RISK
    ]

    conflicts = []
    seen = set()
    for i, p1 in enumerate(active_high_risk):
        for p2 in active_high_risk[i+1:]:
            key = tuple(sorted([p1["permit_id"], p2["permit_id"]]))
            if key in seen:
                continue
            seen.add(key)
            combo = (p1["type"], p2["type"])
            combo_rev = (p2["type"], p1["type"])
            risk = SIMOPS_RISK_MATRIX.get(combo) or SIMOPS_RISK_MATRIX.get(combo_rev)
            if risk:
                conflicts.append({
                    "risk_level": risk,
                    "permit_1": p1["permit_id"],
                    "type_1": p1["type"],
                    "zone_1": p1["zone"],
                    "permit_2": p2["permit_id"],
                    "type_2": p2["type"],
                    "zone_2": p2["zone"],
                    "regulatory_ref": "OISD 105 Section 7.2",
                    "action_required": "Formal SIMOPs assessment required before continuing both operations.",
                })

    return {
        "high_risk_permits_active": len(active_high_risk),
        "simops_required": len(active_high_risk) > 1,
        "conflicts": conflicts,
        "assessment_required": len(conflicts) > 0,
        "note": (
            "OISD 105 Section 7.2: SIMOPs assessment mandatory when high-risk permits "
            "are active within 25 metres of each other."
        ) if len(active_high_risk) > 1 else "No concurrent high-risk operations.",
    }


@router.get("/{permit_id}")
async def get_permit(permit_id: str):
    """Full permit detail."""
    permit = next((p for p in ACTIVE_PERMITS if p["permit_id"] == permit_id), None)
    if not permit:
        raise HTTPException(status_code=404, detail=f"Permit {permit_id} not found")
    return permit


@router.post("/validate")
async def validate_permit(request: PermitValidationRequest):
    """
    Validate a permit-to-work request against live plant conditions.
    Production: calls PermitIntelAgent for full AI analysis.
    Demo: deterministic rule-based evaluation + pre-computed AI recommendation.
    """
    blocking, conditions = _check_sensor_blocking(request.permit_type, request.zone)
    simops_conflicts = _check_simops(request.permit_type, request.zone)

    # Checklist gaps
    from backend.agents.permit_intel_agent import OISD_105_CHECKLIST, PermitType
    try:
        pt = PermitType(request.permit_type)
        required = OISD_105_CHECKLIST.get(pt, [])
        checklist_gaps = [
            f"Missing: {item.replace('_', ' ').title()} (OISD 105 mandatory)"
            for item in required
            if not request.checklist_items.get(item, False)
        ]
    except Exception:
        checklist_gaps = []

    all_blocking = blocking + [c for c in simops_conflicts if c.startswith("CRITICAL")]

    if all_blocking or checklist_gaps:
        decision = "DENIED"
        approved = False
    elif conditions or simops_conflicts:
        decision = "CONDITIONAL"
        approved = True
    else:
        decision = "APPROVED"
        approved = True

    risk_score = min(100, len(all_blocking) * 35 + len(conditions) * 15 + len(simops_conflicts) * 20 + len(checklist_gaps) * 10)
    risk_level = "CRITICAL" if risk_score >= 75 else "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 25 else "LOW"

    # Pre-computed AI recommendation based on zone and type
    ai_recs = {
        ("CONFINED_SPACE", "Confined Space B7"): (
            "DENY PERMIT: O₂ at 17.2% (safe minimum 19.5%) and falling at 0.15%/min. "
            "Entry with current conditions creates an imminent asphyxiation risk. "
            "Ventilate space and confirm O₂ above 19.5% before re-evaluating permit."
        ),
        ("HOT_WORK", "Coke Oven Battery A"): (
            "DENY PERMIT: H₂S at 18.4ppm and CO at 312ppm in zone exceed warning thresholds. "
            "Hot work with flammable gas present creates explosive and toxic risk. "
            "Confirm gas readings are below warning thresholds before issuing."
        ),
    }
    ai_recommendation = ai_recs.get(
        (request.permit_type, request.zone),
        f"{decision}: {len(all_blocking)} blocking issue(s), {len(conditions)} condition(s). "
        f"{'Resolve all blocking issues before proceeding.' if all_blocking else 'Ensure all conditions are met before work commences.'}"
    )

    return {
        "permit_id": request.permit_id,
        "decision": decision,
        "approved": approved,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "blocking_issues": all_blocking,
        "conditions": conditions + [
            "Mandatory atmospheric testing every 90 minutes (OISD 105 Section 4.3)",
            "Isolation certificate required before work commences (OISD 105 Section 6.1)",
            f"Minimum {max(2, request.planned_workers // 2)} standby personnel at entry point",
        ] if not all_blocking else [],
        "simops_conflicts": simops_conflicts,
        "checklist_gaps": checklist_gaps[:6],
        "ai_recommendation": ai_recommendation,
        "regulatory_refs": [
            "OISD 105 Section 4.3 — PTW Confined Space",
            "OISD 116 Section 4.1 — Respiratory Equipment",
            "Factory Act 1948 Section 36A — Dangerous Fumes",
        ],
        "estimated_safe_window": (
            "After ventilation restores O₂ above 19.5% (~30-60 minutes)"
            if request.permit_type == "CONFINED_SPACE" and request.zone == "Confined Space B7"
            else None
        ),
        "officer_action_required": (
            "DENY PERMIT — do not issue until all blocking issues resolved."
            if all_blocking else
            "ISSUE WITH CONDITIONS — communicate all mandatory conditions to workers before work commences."
            if conditions else
            "APPROVE — all checks passed. Standard monitoring applies."
        ),
        "validation_timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/{permit_id}/suspend")
async def suspend_permit(permit_id: str, body: PermitActionRequest):
    """Suspend an active permit."""
    permit = next((p for p in ACTIVE_PERMITS if p["permit_id"] == permit_id), None)
    if not permit:
        raise HTTPException(status_code=404, detail=f"Permit {permit_id} not found")
    if permit["status"] != "ACTIVE":
        raise HTTPException(status_code=400, detail=f"Permit {permit_id} is not active (current: {permit['status']})")

    permit["status"] = "SUSPENDED"
    permit["suspension_reason"] = body.reason
    permit["suspended_by"] = body.actioned_by
    permit["suspended_at"] = datetime.utcnow().isoformat()

    return {
        "permit_id": permit_id,
        "status": "SUSPENDED",
        "suspended_by": body.actioned_by,
        "reason": body.reason,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "All workers in zone must be notified immediately. Work must cease until permit is reissued.",
    }


@router.post("/{permit_id}/close")
async def close_permit(permit_id: str, body: PermitActionRequest):
    """Close a completed permit and move to history."""
    permit = next((p for p in ACTIVE_PERMITS if p["permit_id"] == permit_id), None)
    if not permit:
        raise HTTPException(status_code=404, detail=f"Permit {permit_id} not found")

    permit["status"] = "COMPLETED"
    permit["closed_by"] = body.actioned_by
    permit["closed_at"] = datetime.utcnow().isoformat()
    _permit_history.append(permit)
    ACTIVE_PERMITS.remove(permit)

    return {
        "permit_id": permit_id,
        "status": "COMPLETED",
        "closed_by": body.actioned_by,
        "timestamp": datetime.utcnow().isoformat(),
    }