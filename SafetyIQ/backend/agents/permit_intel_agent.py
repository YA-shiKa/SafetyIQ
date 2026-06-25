"""
SafetyIQ — Digital Permit Intelligence Agent
=============================================
AI that analyses active permits against real-time plant conditions
and flags dangerous simultaneous operations.
 
Key checks:
  • Hot work permits vs adjacent gas sensor readings
  • Confined space permits vs atmospheric conditions
  • SIMOPs (simultaneous operations) analysis
  • PTW completeness vs OISD 105 checklist
  • Permit-to-maintenance cross-reference
 
Author: SafetyIQ Team
"""
 
from __future__ import annotations
 
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
 
import anthropic
 
logger = logging.getLogger(__name__)
 
 
class PermitDecision(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONAL = "CONDITIONAL"
    SUSPENDED = "SUSPENDED"
    DENIED = "DENIED"
 
 
class PermitType(str, Enum):
    HOT_WORK = "HOT_WORK"
    CONFINED_SPACE = "CONFINED_SPACE"
    ELECTRICAL_ISOLATION = "ELECTRICAL_ISOLATION"
    HEIGHT_WORK = "HEIGHT_WORK"
    EXCAVATION = "EXCAVATION"
    RADIOGRAPHY = "RADIOGRAPHY"
    CHEMICAL_HANDLING = "CHEMICAL_HANDLING"
 
 
@dataclass
class LiveCondition:
    zone: str
    sensor_readings: list[dict]
    adjacent_zone_readings: list[dict]
    active_permits_same_zone: list[dict]
    active_permits_adjacent: list[dict]
    maintenance_alerts: list[str]
    shift_info: dict
 
 
@dataclass
class PermitRequest:
    permit_id: str
    permit_type: PermitType
    zone: str
    work_description: str
    planned_workers: int
    start_time: datetime
    duration_hours: float
    isolation_plan: str
    rescue_plan: str
    requested_by: str
    checklist_items: dict[str, bool] = field(default_factory=dict)
 
 
@dataclass
class PermitValidation:
    permit_id: str
    decision: PermitDecision
    risk_score: int                  # 0-100
    blocking_issues: list[str]
    conditions: list[str]            # Mandatory conditions if CONDITIONAL
    simops_conflicts: list[str]      # Detected simultaneous operation conflicts
    checklist_gaps: list[str]        # Missing mandatory checklist items per OISD 105
    ai_recommendation: str
    regulatory_basis: list[str]
    estimated_safe_window: str | None  # When conditions might improve
    officer_action_required: str
    validation_timestamp: datetime = field(default_factory=datetime.utcnow)
 
 
# ─── OISD 105 Mandatory Checklist ────────────────────────────────────────────
 
OISD_105_CHECKLIST: dict[PermitType, list[str]] = {
    PermitType.CONFINED_SPACE: [
        "atmospheric_testing_o2",
        "atmospheric_testing_h2s",
        "atmospheric_testing_co",
        "atmospheric_testing_combustibles",
        "isolation_confirmed",
        "isolation_certificate_attached",
        "rescue_plan_documented",
        "rescue_equipment_at_entry",
        "communication_protocol_established",
        "standby_personnel_assigned",
        "scba_availability_confirmed",
        "entry_supervisor_designated",
    ],
    PermitType.HOT_WORK: [
        "area_cleared_of_combustibles",
        "fire_extinguisher_at_site",
        "firewatch_assigned",
        "isolation_from_flammable_sources",
        "isolation_certificate_attached",
        "gas_testing_completed",
        "hot_work_area_marked",
        "adjacent_zone_notified",
    ],
    PermitType.ELECTRICAL_ISOLATION: [
        "loto_applied",
        "voltage_test_confirmed_dead",
        "isolation_certificate_attached",
        "authorized_electrician_assigned",
        "earthing_applied",
    ],
    PermitType.HEIGHT_WORK: [
        "fall_arrest_system_inspected",
        "scaffold_inspected",
        "exclusion_zone_established",
        "weather_assessment_done",
        "rescue_plan_documented",
    ],
}
 
 
class PermitIntelAgent:
    """
    Digital Permit Intelligence Agent.
    Validates permits against live sensor conditions and regulatory checklists.
    """
 
    SIMOPS_RISK_MATRIX: dict[tuple[str, str], str] = {
        (PermitType.HOT_WORK, PermitType.CONFINED_SPACE): "CRITICAL",
        (PermitType.HOT_WORK, PermitType.CHEMICAL_HANDLING): "HIGH",
        (PermitType.ELECTRICAL_ISOLATION, PermitType.CONFINED_SPACE): "HIGH",
        (PermitType.RADIOGRAPHY, PermitType.HEIGHT_WORK): "MEDIUM",
        (PermitType.EXCAVATION, PermitType.HEIGHT_WORK): "MEDIUM",
    }
 
    def __init__(self, anthropic_api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
 
    async def validate(
        self,
        permit_request: PermitRequest,
        live_condition: LiveCondition,
    ) -> PermitValidation:
        """Full permit validation against live conditions."""
 
        # Step 1: Checklist gap analysis
        checklist_gaps = self._check_oisd_checklist(permit_request)
 
        # Step 2: Sensor-based blocking conditions
        blocking_issues, conditions = self._evaluate_sensors(permit_request, live_condition)
 
        # Step 3: SIMOPs analysis
        simops_conflicts = self._evaluate_simops(permit_request, live_condition)
 
        # All blocking issues
        all_blocking = blocking_issues + (
            [f"CRITICAL SIMOPs conflict: {c}" for c in simops_conflicts
             if c.startswith("CRITICAL")]
        )
 
        # Step 4: AI analysis for nuanced recommendation
        ai_recommendation, regulatory_basis, estimated_window = await self._ai_evaluate(
            permit_request, live_condition, all_blocking, conditions, simops_conflicts, checklist_gaps
        )
 
        # Step 5: Determine final decision
        if all_blocking or checklist_gaps:
            decision = PermitDecision.DENIED if all_blocking else PermitDecision.SUSPENDED
        elif conditions or simops_conflicts:
            decision = PermitDecision.CONDITIONAL
        else:
            decision = PermitDecision.APPROVED
 
        risk_score = min(100, len(all_blocking) * 35 + len(conditions) * 15 + len(simops_conflicts) * 20 + len(checklist_gaps) * 10)
 
        officer_action = (
            "DENY PERMIT — do not issue until blocking issues resolved." if all_blocking else
            "ISSUE WITH CONDITIONS — communicate all mandatory conditions to workers before work commences." if conditions else
            "APPROVE — all checks passed. Standard monitoring applies."
        )
 
        return PermitValidation(
            permit_id=permit_request.permit_id,
            decision=decision,
            risk_score=risk_score,
            blocking_issues=all_blocking,
            conditions=conditions,
            simops_conflicts=simops_conflicts,
            checklist_gaps=checklist_gaps,
            ai_recommendation=ai_recommendation,
            regulatory_basis=regulatory_basis,
            estimated_safe_window=estimated_window,
            officer_action_required=officer_action,
        )
 
    def _check_oisd_checklist(self, request: PermitRequest) -> list[str]:
        """Identify missing mandatory checklist items per OISD 105."""
        required = OISD_105_CHECKLIST.get(request.permit_type, [])
        gaps = []
        for item in required:
            if not request.checklist_items.get(item, False):
                readable = item.replace("_", " ").title()
                gaps.append(f"Missing: {readable} (OISD 105 Section 4.3 mandatory)")
        return gaps
 
    def _evaluate_sensors(
        self, request: PermitRequest, condition: LiveCondition
    ) -> tuple[list[str], list[str]]:
        """Map sensor readings to permit-specific risk rules."""
        blocking = []
        conditions = []
 
        sensor_map = {r["sensor_type"]: r for r in condition.sensor_readings}
 
        if request.permit_type == PermitType.CONFINED_SPACE:
            if "O2" in sensor_map and sensor_map["O2"]["value"] < 19.5:
                o2 = sensor_map["O2"]["value"]
                if o2 < 16.0:
                    blocking.append(f"O₂ critically low: {o2}% (OISD 116: entry PROHIBITED below 16%)")
                else:
                    blocking.append(f"O₂ below safe minimum: {o2}% (OISD 116: SCBA mandatory, standby required)")
            if "H2S" in sensor_map and sensor_map["H2S"]["value"] >= 10:
                h2s = sensor_map["H2S"]["value"]
                if h2s >= 20:
                    blocking.append(f"H₂S at {h2s}ppm exceeds IDLH — immediate evacuation required")
                else:
                    conditions.append(f"H₂S at {h2s}ppm — SCBA mandatory, 2 standby persons required (OISD 116 Section 4.1)")
            if "CO" in sensor_map and sensor_map["CO"]["value"] >= 200:
                co = sensor_map["CO"]["value"]
                conditions.append(f"CO at {co}ppm above warning threshold — respiratory protection mandatory")
 
        elif request.permit_type == PermitType.HOT_WORK:
            for gas_type in ("H2S", "CO", "CH4"):
                if gas_type in sensor_map and sensor_map[gas_type]["value"] >= sensor_map[gas_type].get("threshold_warning", 999):
                    val = sensor_map[gas_type]["value"]
                    blocking.append(f"Flammable/toxic gas {gas_type} at {val} in hot work zone — OISD 105 Section 6.1: isolation must be verified")
            # Adjacent zone check
            for adj in condition.adjacent_zone_readings:
                if adj.get("sensor_type") in ("H2S", "CO") and adj.get("value", 0) >= adj.get("threshold_warning", 999):
                    conditions.append(f"Adjacent zone {adj.get('zone')}: {adj['sensor_type']} elevated. Hot work separation assessment required (OISD 105 Section 7.2)")
 
        return blocking, conditions
 
    def _evaluate_simops(
        self, request: PermitRequest, condition: LiveCondition
    ) -> list[str]:
        """Check for dangerous simultaneous operations."""
        conflicts = []
        all_active = condition.active_permits_same_zone + condition.active_permits_adjacent
 
        for active in all_active:
            active_type = active.get("permit_type", "")
            combo = (request.permit_type.value, active_type)
            combo_rev = (active_type, request.permit_type.value)
 
            risk = self.SIMOPS_RISK_MATRIX.get(combo) or self.SIMOPS_RISK_MATRIX.get(combo_rev)
            if risk:
                zone_note = "" if active.get("zone") == request.zone else f" (adjacent zone: {active.get('zone')})"
                conflicts.append(
                    f"{risk}: {request.permit_type.value} + {active_type} permit #{active.get('permit_id')}{zone_note} — OISD 105 Section 7.2 SIMOPs assessment mandatory"
                )
 
        return conflicts
 
    async def _ai_evaluate(
        self,
        request: PermitRequest,
        condition: LiveCondition,
        blocking: list[str],
        conditions: list[str],
        simops: list[str],
        checklist_gaps: list[str],
    ) -> tuple[str, list[str], str | None]:
        """
        AI-powered nuanced evaluation for complex scenarios.
        Returns: (recommendation, regulatory_basis, estimated_safe_window)
        """
 
        prompt = f"""You are an AI safety officer evaluating a permit-to-work request at an Indian steel plant.
 
PERMIT REQUEST:
- ID: {request.permit_id}
- Type: {request.permit_type.value}
- Zone: {request.zone}
- Work: {request.work_description}
- Workers: {request.planned_workers}
- Duration: {request.duration_hours}h
- Isolation Plan: {request.isolation_plan}
 
CURRENT CONDITIONS IN ZONE:
{json.dumps(condition.sensor_readings, indent=2)}
 
ADJACENT ZONE CONDITIONS:
{json.dumps(condition.adjacent_zone_readings[:3], indent=2)}
 
PRE-ANALYSIS RESULTS:
Blocking issues: {json.dumps(blocking)}
Conditions: {json.dumps(conditions)}
SIMOPs conflicts: {json.dumps(simops)}
Checklist gaps: {json.dumps(checklist_gaps)}
 
Respond ONLY in valid JSON:
{{
  "ai_recommendation": "Concise recommendation to the issuing safety officer (2-3 sentences). Specific, actionable, in plain language.",
  "regulatory_basis": ["OISD Standard X Section Y: why it applies", "Factory Act Section Z: why it applies"],
  "estimated_safe_window": "When conditions may improve (e.g., 'After ventilation in ~45 minutes' or 'After PRV inspection is completed') — null if conditions are non-time-dependent"
}}"""
 
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
                system="You are an expert industrial safety AI. Respond only in valid JSON.",
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return (
                data.get("ai_recommendation", "Refer to safety officer for manual review."),
                data.get("regulatory_basis", []),
                data.get("estimated_safe_window"),
            )
        except Exception as e:
            logger.error(f"Permit AI evaluation error: {e}")
            decision_text = "DENY" if blocking else "CONDITIONAL APPROVAL"
            return (
                f"{decision_text}: {len(blocking)} blocking and {len(conditions)} conditional issues found. Safety officer review required.",
                ["OISD 105", "Factory Act 1948 Section 36A"],
                None,
            )
 
    def to_api_response(self, validation: PermitValidation) -> dict[str, Any]:
        return {
            "permit_id": validation.permit_id,
            "decision": validation.decision.value,
            "risk_score": validation.risk_score,
            "blocking_issues": validation.blocking_issues,
            "conditions": validation.conditions,
            "simops_conflicts": validation.simops_conflicts,
            "checklist_gaps": validation.checklist_gaps,
            "ai_recommendation": validation.ai_recommendation,
            "regulatory_basis": validation.regulatory_basis,
            "estimated_safe_window": validation.estimated_safe_window,
            "officer_action_required": validation.officer_action_required,
            "validation_timestamp": validation.validation_timestamp.isoformat(),
        }
 