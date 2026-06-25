"""
SafetyIQ — Compound Risk Detection Agent
=========================================
Multi-signal correlation engine that identifies dangerous combinations
of conditions that no single sensor would flag alone.
 
Detection logic covers:
  • Gas accumulation + active confined space permits
  • Hot work proximity to elevated flammable gas zones
  • Oxygen deficiency + maintenance activity
  • Pressure anomalies + aging relief valve status
  • Shift changeover + incomplete hazard isolation
  • Multiple simultaneous high-risk operations (SIMOPs)
 
Author: SafetyIQ Team
"""
 
import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
 
import anthropic
 
logger = logging.getLogger(__name__)
 
 
# ─── Data Models ──────────────────────────────────────────────────────────────
 
class RiskLevel(str, Enum):
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
 
 
class RiskCategory(str, Enum):
    GAS_ACCUMULATION = "GAS_ACCUMULATION"
    CONFINED_SPACE = "CONFINED_SPACE"
    HOT_WORK = "HOT_WORK"
    PRESSURE_ANOMALY = "PRESSURE_ANOMALY"
    OXYGEN_DEFICIENCY = "OXYGEN_DEFICIENCY"
    SIMOPS = "SIMOPS"  # Simultaneous Operations
    SHIFT_CHANGEOVER = "SHIFT_CHANGEOVER"
    EQUIPMENT_FAILURE = "EQUIPMENT_FAILURE"
 
 
@dataclass
class SensorReading:
    sensor_id: str
    zone: str
    sensor_type: str          # H2S, CO, O2, TEMP, PRESSURE, etc.
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime
    trend: str = "stable"     # "rising", "falling", "stable"
    rate_of_change: float = 0.0  # per minute
 
 
@dataclass
class PermitToWork:
    permit_id: str
    permit_type: str          # HOT_WORK, CONFINED_SPACE, ELECTRICAL, HEIGHT, etc.
    zone: str
    start_time: datetime
    end_time: datetime
    workers: list[str]
    issuing_officer: str
    isolation_confirmed: bool = False
    active: bool = True
 
 
@dataclass
class MaintenanceRecord:
    equipment_id: str
    equipment_name: str
    zone: str
    last_inspection: datetime
    next_due: datetime
    status: str               # OPERATIONAL, DEGRADED, UNDER_MAINTENANCE, FAILED
    days_overdue: int = 0
 
 
@dataclass
class CompoundRiskEvent:
    event_id: str
    risk_level: RiskLevel
    categories: list[RiskCategory]
    zone: str
    title: str
    description: str
    contributing_factors: list[str]
    recommended_actions: list[str]
    predicted_escalation_time: datetime | None
    confidence_score: float   # 0.0 - 1.0
    lead_time_hours: float    # How far in advance we detected this
    regulatory_refs: list[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ai_analysis: str = ""
 
 
@dataclass
class PlantState:
    """Snapshot of full plant safety state for compound analysis."""
    timestamp: datetime
    sensors: list[SensorReading]
    active_permits: list[PermitToWork]
    maintenance_records: list[MaintenanceRecord]
    shift_changeover_in_minutes: int | None  # None if not imminent
    workers_on_site: int
    last_incident_days: int
 
 
# ─── Risk Rules Engine ────────────────────────────────────────────────────────
 
class CompoundRiskRules:
    """
    Deterministic rule engine that identifies compound risk preconditions.
    Rules are evaluated first; AI is used for nuanced analysis and communication.
    """
 
    @staticmethod
    def check_confined_space_gas_compound(
        state: PlantState,
    ) -> list[tuple[str, list[str]]]:
        """
        Rule: Confined space entry permit + abnormal gas readings in same zone.
        This combination killed 8 workers at Visakhapatnam January 2025.
        """
        findings = []
        confined_permits = [p for p in state.active_permits if p.permit_type == "CONFINED_SPACE"]
 
        for permit in confined_permits:
            zone_sensors = [s for s in state.sensors if s.zone == permit.zone]
            hazardous_sensors = [
                s for s in zone_sensors
                if s.value >= s.threshold_warning
            ]
            if hazardous_sensors:
                factors = [
                    f"Active confined space permit #{permit.permit_id} in {permit.zone}",
                    f"{len(permit.workers)} workers authorized for entry",
                ] + [
                    f"{s.sensor_type} at {s.value}{s.unit} ({s.trend}) — warning: {s.threshold_warning}"
                    for s in hazardous_sensors
                ]
                findings.append((permit.zone, factors))
 
        return findings
 
    @staticmethod
    def check_hot_work_near_gas(state: PlantState, proximity_threshold_meters: float = 15.0) -> list[tuple[str, list[str]]]:
        """
        Rule: Hot work permit issued in/near zone with elevated flammable gas.
        Combination has preceded multiple Indian steel plant fatalities.
        """
        findings = []
        hot_work_permits = [p for p in state.active_permits if p.permit_type == "HOT_WORK"]
 
        for permit in hot_work_permits:
            # Check same zone AND adjacent zones (simplified: same zone for MVP)
            zone_sensors = [s for s in state.sensors
                           if s.zone == permit.zone and s.sensor_type in ("H2S", "CO", "CH4")]
            elevated = [s for s in zone_sensors if s.value >= s.threshold_warning]
 
            if elevated:
                factors = [
                    f"Hot work permit #{permit.permit_id} active in {permit.zone}",
                    f"Isolation barrier confirmed: {'YES' if permit.isolation_confirmed else 'NOT CONFIRMED ⚠️'}",
                ] + [
                    f"Flammable gas {s.sensor_type}: {s.value}{s.unit} (LEL concern)"
                    for s in elevated
                ]
                findings.append((permit.zone, factors))
 
        return findings
 
    @staticmethod
    def check_oxygen_deficiency_entry(state: PlantState) -> list[tuple[str, list[str]]]:
        """
        Rule: O2 below safe threshold (<19.5%) + any active entry permit.
        """
        findings = []
        o2_sensors = [s for s in state.sensors if s.sensor_type == "O2" and s.value < 19.5]
 
        for sensor in o2_sensors:
            zone_permits = [p for p in state.active_permits if p.zone == sensor.zone]
            if zone_permits:
                factors = [
                    f"Oxygen level: {sensor.value}% (safe minimum: 19.5%) — TREND: {sensor.trend}",
                    f"Rate of decline: {abs(sensor.rate_of_change):.2f}% per minute" if sensor.trend == "falling" else "",
                ] + [
                    f"Active permit {p.permit_id} ({p.permit_type}) — {len(p.workers)} workers"
                    for p in zone_permits
                ]
                findings.append((sensor.zone, [f for f in factors if f]))
 
        return findings
 
    @staticmethod
    def check_simops(state: PlantState, max_concurrent: int = 2) -> list[tuple[str, list[str]]]:
        """
        Rule: More than N high-risk permits active simultaneously in adjacent zones.
        """
        findings = []
        high_risk_types = {"CONFINED_SPACE", "HOT_WORK", "ELECTRICAL_ISOLATION", "EXCAVATION"}
        high_risk_permits = [p for p in state.active_permits if p.permit_type in high_risk_types]
 
        if len(high_risk_permits) > max_concurrent:
            factors = [f"Simultaneous Operations detected: {len(high_risk_permits)} high-risk permits active"] + [
                f"{p.permit_id}: {p.permit_type} in {p.zone}"
                for p in high_risk_permits
            ]
            findings.append(("Multiple Zones", factors))
 
        return findings
 
    @staticmethod
    def check_shift_changeover_risk(state: PlantState) -> list[tuple[str, list[str]]]:
        """
        Rule: Shift changeover within 15 min + any critical sensor + active permits.
        Shift handover is a historically high-risk transition window.
        """
        findings = []
        if state.shift_changeover_in_minutes is not None and state.shift_changeover_in_minutes <= 15:
            critical_sensors = [s for s in state.sensors if s.value >= s.threshold_warning]
            if critical_sensors and state.active_permits:
                factors = [
                    f"Shift changeover in {state.shift_changeover_in_minutes} minutes",
                    f"{len(state.active_permits)} active permits requiring handover briefing",
                    f"{len(critical_sensors)} sensors currently in alert state",
                ]
                findings.append(("Plant-Wide", factors))
 
        return findings
 
    @staticmethod
    def check_overdue_equipment_under_load(state: PlantState) -> list[tuple[str, list[str]]]:
        """
        Rule: Equipment overdue for inspection operating under elevated pressure/temp.
        """
        findings = []
        overdue = [m for m in state.maintenance_records if m.days_overdue > 0 and m.status == "OPERATIONAL"]
 
        for equip in overdue:
            zone_pressure = [s for s in state.sensors
                            if s.zone == equip.zone and s.sensor_type == "PRESSURE" and s.value >= s.threshold_warning]
            if zone_pressure:
                factors = [
                    f"Equipment '{equip.equipment_name}' overdue inspection by {equip.days_overdue} days",
                    f"Last inspected: {equip.last_inspection.strftime('%Y-%m-%d')}",
                ] + [
                    f"Pressure {s.value}{s.unit} exceeds warning threshold {s.threshold_warning}{s.unit}"
                    for s in zone_pressure
                ]
                findings.append((equip.zone, factors))
 
        return findings
 
 
# ─── Main Agent ───────────────────────────────────────────────────────────────
 
class CompoundRiskAgent:
    """
    Multi-signal compound risk detection agent.
 
    Architecture:
    1. Rule engine detects structural risk combinations (fast, deterministic)
    2. AI layer (Claude) provides contextual analysis, severity assessment,
       predicted escalation timeline, and regulatory guidance
    3. Results are scored, ranked, and emitted as CompoundRiskEvent objects
    """
 
    def __init__(self, anthropic_api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.rules = CompoundRiskRules()
        self.event_history: list[CompoundRiskEvent] = []
 
    async def analyze(self, state: PlantState) -> list[CompoundRiskEvent]:
        """
        Full compound risk analysis pass over current plant state.
        Returns list of CompoundRiskEvent objects sorted by severity.
        """
        logger.info(f"Running compound risk analysis at {state.timestamp}")
 
        # Step 1: Rule-based pre-screening
        raw_findings: list[tuple[str, list[str], RiskCategory]] = []
 
        for zone, factors in self.rules.check_confined_space_gas_compound(state):
            raw_findings.append((zone, factors, RiskCategory.CONFINED_SPACE))
 
        for zone, factors in self.rules.check_hot_work_near_gas(state):
            raw_findings.append((zone, factors, RiskCategory.HOT_WORK))
 
        for zone, factors in self.rules.check_oxygen_deficiency_entry(state):
            raw_findings.append((zone, factors, RiskCategory.OXYGEN_DEFICIENCY))
 
        for zone, factors in self.rules.check_simops(state):
            raw_findings.append((zone, factors, RiskCategory.SIMOPS))
 
        for zone, factors in self.rules.check_shift_changeover_risk(state):
            raw_findings.append((zone, factors, RiskCategory.SHIFT_CHANGEOVER))
 
        for zone, factors in self.rules.check_overdue_equipment_under_load(state):
            raw_findings.append((zone, factors, RiskCategory.EQUIPMENT_FAILURE))
 
        if not raw_findings:
            logger.info("No compound risk conditions detected.")
            return []
 
        logger.info(f"Rule engine found {len(raw_findings)} potential compound risk(s). Escalating to AI analysis.")
 
        # Step 2: AI analysis of each finding
        events: list[CompoundRiskEvent] = []
        for zone, factors, category in raw_findings:
            event = await self._ai_analyze_finding(zone, factors, category, state)
            if event:
                events.append(event)
 
        # Step 3: Sort by risk level
        severity_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3, RiskLevel.SAFE: 4}
        events.sort(key=lambda e: severity_order[e.risk_level])
 
        self.event_history.extend(events)
        return events
 
    async def _ai_analyze_finding(
        self,
        zone: str,
        factors: list[str],
        category: RiskCategory,
        state: PlantState,
    ) -> CompoundRiskEvent | None:
        """
        Use Claude to analyze a rule-detected compound risk finding.
        Returns structured CompoundRiskEvent with AI-enriched analysis.
        """
 
        system_prompt = """You are an expert industrial safety AI specializing in Indian heavy industry regulations.
You analyze compound risk conditions at steel plants and refineries.
Your analysis must be precise, actionable, and reference specific OISD, Factory Act 1948, or DGMS regulations.
Always respond in valid JSON matching the specified schema."""
 
        sensor_summary = [
            {"zone": s.zone, "type": s.sensor_type, "value": s.value, "unit": s.unit,
             "threshold_warning": s.threshold_warning, "threshold_critical": s.threshold_critical,
             "trend": s.trend}
            for s in state.sensors if s.zone == zone or s.value >= s.threshold_warning
        ]
 
        user_prompt = f"""
Analyze this compound risk condition detected at an Indian steel plant:
 
ZONE: {zone}
RISK CATEGORY: {category.value}
DETECTED FACTORS:
{json.dumps(factors, indent=2)}
 
RELEVANT SENSOR READINGS:
{json.dumps(sensor_summary, indent=2)}
 
OPERATIONAL CONTEXT:
- Workers on site: {state.workers_on_site}
- Active permits: {len(state.active_permits)}
- Shift changeover in: {state.shift_changeover_in_minutes} minutes (None = not imminent)
- Days since last incident: {state.last_incident_days}
 
Respond with ONLY valid JSON (no markdown) matching this exact schema:
{{
  "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "title": "brief title of the compound risk",
  "description": "2-3 sentence description of the compound risk and why it's dangerous",
  "additional_contributing_factors": ["factor1", "factor2"],
  "recommended_actions": [
    "Immediate action 1 (with timeframe)",
    "Immediate action 2",
    "Follow-up action"
  ],
  "predicted_escalation_hours": 2.5,
  "confidence_score": 0.87,
  "lead_time_hours": 1.5,
  "regulatory_references": [
    "OISD Standard 105 Section X.Y: description",
    "Factory Act 1948 Section XX: description"
  ],
  "ai_analysis": "Detailed technical analysis of why this specific combination is dangerous, what historical incidents match this pattern, and the mechanistic pathway to an incident."
}}
"""
 
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
            )
 
            raw = response.content[0].text.strip()
            # Strip code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
 
            escalation_time = None
            if data.get("predicted_escalation_hours"):
                escalation_time = state.timestamp + timedelta(hours=data["predicted_escalation_hours"])
 
            event = CompoundRiskEvent(
                event_id=f"CRE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{zone[:4].upper()}",
                risk_level=RiskLevel(data["risk_level"]),
                categories=[category],
                zone=zone,
                title=data["title"],
                description=data["description"],
                contributing_factors=factors + data.get("additional_contributing_factors", []),
                recommended_actions=data.get("recommended_actions", []),
                predicted_escalation_time=escalation_time,
                confidence_score=data.get("confidence_score", 0.8),
                lead_time_hours=data.get("lead_time_hours", 1.0),
                regulatory_refs=data.get("regulatory_references", []),
                ai_analysis=data.get("ai_analysis", ""),
            )
            return event
 
        except json.JSONDecodeError as e:
            logger.error(f"AI response JSON parse error: {e}")
            # Fallback: create event from rule data without AI enrichment
            return CompoundRiskEvent(
                event_id=f"CRE-FALLBACK-{zone[:4].upper()}",
                risk_level=RiskLevel.HIGH,
                categories=[category],
                zone=zone,
                title=f"Compound Risk Detected: {category.value.replace('_', ' ').title()} in {zone}",
                description="Rule engine detected compound risk condition. AI analysis unavailable.",
                contributing_factors=factors,
                recommended_actions=["Evacuate affected zone immediately", "Notify safety officer", "Suspend all active permits in zone"],
                predicted_escalation_time=None,
                confidence_score=0.7,
                lead_time_hours=0.5,
                regulatory_refs=["OISD 105", "Factory Act 1948 Section 38"],
            )
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error during compound risk analysis: {e}")
            return None
 
    def get_plant_risk_score(self, events: list[CompoundRiskEvent]) -> int:
        """
        Compute overall plant risk score (0-100) from active events.
        Weights: CRITICAL=40pts, HIGH=25pts, MEDIUM=15pts, LOW=5pts (capped at 100)
        """
        weights = {RiskLevel.CRITICAL: 40, RiskLevel.HIGH: 25, RiskLevel.MEDIUM: 15, RiskLevel.LOW: 5}
        score = sum(weights.get(e.risk_level, 0) for e in events)
        return min(score, 100)
 
    def to_api_response(self, events: list[CompoundRiskEvent]) -> dict[str, Any]:
        """Serialize events for REST API response."""
        return {
            "plant_risk_score": self.get_plant_risk_score(events),
            "total_events": len(events),
            "critical_count": sum(1 for e in events if e.risk_level == RiskLevel.CRITICAL),
            "high_count": sum(1 for e in events if e.risk_level == RiskLevel.HIGH),
            "events": [
                {
                    **asdict(e),
                    "timestamp": e.timestamp.isoformat(),
                    "predicted_escalation_time": e.predicted_escalation_time.isoformat() if e.predicted_escalation_time else None,
                }
                for e in events
            ],
        }
 
 
# ─── Example Usage ────────────────────────────────────────────────────────────
 
async def demo():
    """Demonstration with simulated plant state mirroring Vizag-type conditions."""
    state = PlantState(
        timestamp=datetime.utcnow(),
        sensors=[
            SensorReading("S001", "Coke Oven Battery A", "H2S", 18.4, "ppm", 10, 20, datetime.utcnow(), "rising", 0.3),
            SensorReading("S002", "Coke Oven Battery A", "CO", 312, "ppm", 200, 400, datetime.utcnow(), "rising", 8.0),
            SensorReading("S005", "Confined Space B7", "O2", 17.2, "%", 19.5, 16.0, datetime.utcnow(), "falling", -0.15),
        ],
        active_permits=[
            PermitToWork("PTW-2847", "CONFINED_SPACE", "Confined Space B7",
                        datetime.utcnow() - timedelta(hours=1), datetime.utcnow() + timedelta(hours=3),
                        ["Worker A", "Worker B", "Worker C", "Worker D"], "SO-Sharma", isolation_confirmed=True),
            PermitToWork("PTW-2851", "HOT_WORK", "Coke Oven Battery A",
                        datetime.utcnow() - timedelta(minutes=30), datetime.utcnow() + timedelta(hours=2),
                        ["Welder X", "Helper Y"], "SO-Patel", isolation_confirmed=False),
        ],
        maintenance_records=[
            MaintenanceRecord("PRV-004", "Pressure Relief Valve PRV-004", "Coke Oven Battery A",
                             datetime.utcnow() - timedelta(days=47), datetime.utcnow() - timedelta(days=17),
                             "OPERATIONAL", days_overdue=17),
        ],
        shift_changeover_in_minutes=12,
        workers_on_site=53,
        last_incident_days=287,
    )
 
    agent = CompoundRiskAgent()
    events = await agent.analyze(state)
 
    print(f"\n{'='*60}")
    print(f"SafetyIQ Compound Risk Analysis — {len(events)} events detected")
    print(f"Plant Risk Score: {agent.get_plant_risk_score(events)}/100")
    print(f"{'='*60}\n")
 
    for event in events:
        print(f"[{event.risk_level.value}] {event.title}")
        print(f"  Zone: {event.zone}")
        print(f"  Confidence: {event.confidence_score:.0%}")
        print(f"  Lead time: {event.lead_time_hours:.1f}h")
        print(f"  Factors: {len(event.contributing_factors)}")
        print(f"  Regulatory: {', '.join(event.regulatory_refs[:2])}")
        print()
 
 
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(demo())
 