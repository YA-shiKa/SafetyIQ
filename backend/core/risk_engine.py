"""
SafetyIQ — Unified Risk Engine
================================
Aggregates outputs from all AI agents into a single plant-level risk score,
zone-level heatmap data, and a prioritised action queue.

Architecture:
  CompoundRiskAgent  ─┐
  PermitIntelAgent   ─┤─► RiskEngine.fuse() ─► PlantRiskSummary
  ComplianceAgent    ─┤         │
  IncidentRagAgent   ─┘         └─► WebSocket broadcast

Scoring weights (calibrated against DGFASLI incident data):
  CRITICAL compound risk  : +40 pts
  HIGH compound risk      : +25 pts
  MEDIUM compound risk    : +15 pts
  Active PTW violation    : +10 pts per permit
  Compliance gap (critical): +8 pts per gap
  False-negative dampening: score never drops below 5 when sensors are live

Author: SafetyIQ Team
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ─── Enums ────────────────────────────────────────────────────────────────────

class PlantStatus(str, Enum):
    SAFE       = "SAFE"        # 0–30
    CAUTION    = "CAUTION"     # 31–55
    ELEVATED   = "ELEVATED"    # 56–75
    DANGER     = "DANGER"      # 76–90
    CRITICAL   = "CRITICAL"    # 91–100


class ActionPriority(str, Enum):
    IMMEDIATE  = "IMMEDIATE"   # Must act now (CRITICAL events)
    URGENT     = "URGENT"      # Act within 30 min (HIGH events)
    SCHEDULED  = "SCHEDULED"   # Plan for next shift (MEDIUM)
    MONITOR    = "MONITOR"     # Track only (LOW)


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class ActionItem:
    action_id: str
    priority: ActionPriority
    source: str              # "COMPOUND_RISK" | "PERMIT" | "COMPLIANCE" | "PATTERN"
    zone: str
    title: str
    description: str
    regulatory_refs: list[str] = field(default_factory=list)
    estimated_resolution_minutes: int = 60
    assigned_to: str = "Safety Officer"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ZoneRiskEntry:
    zone_id: str
    zone_name: str
    risk_score: int          # 0–100
    status: PlantStatus
    active_workers: int
    active_permits: int
    top_hazard: str          # Human-readable top contributing factor
    sensor_alerts: list[dict] = field(default_factory=list)
    compound_events: int = 0


@dataclass
class PlantRiskSummary:
    """
    Top-level output of RiskEngine.fuse().
    Consumed by the WebSocket broadcast and REST /api/v1/analyze.
    """
    timestamp: datetime
    plant_risk_score: int        # 0–100
    plant_status: PlantStatus
    zones: list[ZoneRiskEntry]
    action_queue: list[ActionItem]
    critical_count: int
    high_count: int
    medium_count: int
    total_workers_at_risk: int
    prediction_lead_time_hours: float  # Best lead time across all events
    false_negative_risk: str     # "LOW" | "MEDIUM" | "HIGH"
    summary_text: str            # 1-sentence situation summary for commanders


# ─── Scoring Constants ────────────────────────────────────────────────────────

_COMPOUND_WEIGHTS = {
    "CRITICAL": 40,
    "HIGH":     25,
    "MEDIUM":   15,
    "LOW":       5,
}

_PTW_VIOLATION_WEIGHT     = 10
_COMPLIANCE_CRITICAL_WEIGHT = 8
_COMPLIANCE_HIGH_WEIGHT     = 4

_STATUS_THRESHOLDS = [
    (91, PlantStatus.CRITICAL),
    (76, PlantStatus.DANGER),
    (56, PlantStatus.ELEVATED),
    (31, PlantStatus.CAUTION),
    (0,  PlantStatus.SAFE),
]


# ─── Risk Engine ──────────────────────────────────────────────────────────────

class RiskEngine:
    """
    Stateless fusion layer.  Call fuse() with dicts from each agent API endpoint
    and receive a fully-scored PlantRiskSummary.

    Usage:
        engine = RiskEngine()
        summary = engine.fuse(
            compound_events=compound_agent.to_api_response(events),
            permit_validations=[permit_agent.to_api_response(v) for v in validations],
            compliance_status=compliance_agent.get_status(),
            sensor_readings=simulator.get_readings(),
            zone_configs=plant_config["zones"],
        )
    """

    def fuse(
        self,
        compound_events: dict[str, Any],
        permit_validations: list[dict[str, Any]],
        compliance_status: dict[str, Any],
        sensor_readings: list[dict[str, Any]],
        zone_configs: dict[str, Any] | None = None,
    ) -> PlantRiskSummary:
        """Main fusion method. All inputs are plain dicts (API response format)."""

        now = datetime.utcnow()

        # ── 1. Base score from compound risk events ──────────────────────────
        events = compound_events.get("events", [])
        base_score = sum(
            _COMPOUND_WEIGHTS.get(e.get("risk_level", "LOW"), 0)
            for e in events
        )

        # ── 2. Penalty from permit violations ────────────────────────────────
        ptw_penalty = sum(
            _PTW_VIOLATION_WEIGHT
            for v in permit_validations
            if not v.get("approved", True) or v.get("risk_level") == "CRITICAL"
        )

        # ── 3. Compliance penalty ─────────────────────────────────────────────
        critical_gaps = compliance_status.get("critical_gaps", [])
        open_findings = compliance_status.get("open_findings", 0)
        compliance_penalty = (
            len(critical_gaps) * _COMPLIANCE_CRITICAL_WEIGHT
            + max(0, open_findings - len(critical_gaps)) * _COMPLIANCE_HIGH_WEIGHT
        )

        # ── 4. Floor: never 0 while sensors are active ───────────────────────
        total_score = min(100, max(5, base_score + ptw_penalty + compliance_penalty))

        # ── 5. Determine plant status ─────────────────────────────────────────
        plant_status = _score_to_status(total_score)

        # ── 6. Build zone risk map ────────────────────────────────────────────
        zones = self._build_zone_map(events, permit_validations, sensor_readings)

        # ── 7. Build prioritised action queue ─────────────────────────────────
        action_queue = self._build_action_queue(
            events, permit_validations, critical_gaps
        )

        # ── 8. Aggregate metrics ──────────────────────────────────────────────
        critical_count = compound_events.get("critical_count", 0)
        high_count     = compound_events.get("high_count", 0)
        medium_count   = sum(1 for e in events if e.get("risk_level") == "MEDIUM")

        workers_at_risk = sum(
            e.get("workers_in_zone", 0) for e in events
            if e.get("risk_level") in ("CRITICAL", "HIGH")
        )

        lead_times = [
            e.get("lead_time_hours", 0.0) for e in events
            if e.get("risk_level") in ("CRITICAL", "HIGH")
        ]
        best_lead_time = min(lead_times) if lead_times else 0.0

        fn_risk = _false_negative_risk(total_score, critical_gaps, events)

        summary_text = _generate_summary(
            total_score, plant_status, critical_count, high_count, zones
        )

        return PlantRiskSummary(
            timestamp=now,
            plant_risk_score=total_score,
            plant_status=plant_status,
            zones=zones,
            action_queue=action_queue,
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            total_workers_at_risk=workers_at_risk,
            prediction_lead_time_hours=best_lead_time,
            false_negative_risk=fn_risk,
            summary_text=summary_text,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_zone_map(
        self,
        events: list[dict],
        permit_validations: list[dict],
        sensor_readings: list[dict],
    ) -> list[ZoneRiskEntry]:
        """Aggregate sensor + event data per zone."""
        zone_map: dict[str, dict] = {}

        # Seed from sensors
        for reading in sensor_readings:
            zone = reading.get("zone", "Unknown")
            if zone not in zone_map:
                zone_map[zone] = {
                    "alerts": [],
                    "scores": [],
                    "workers": 0,
                    "permits": 0,
                    "compound_events": 0,
                    "top_hazard": "Nominal",
                }
            pct = int((reading["value"] / reading["threshold_critical"]) * 100)
            zone_map[zone]["scores"].append(pct)
            if reading["value"] >= reading["threshold_warning"]:
                zone_map[zone]["alerts"].append({
                    "type": reading["sensor_type"],
                    "value": reading["value"],
                    "unit": reading["unit"],
                })

        # Overlay compound events
        for event in events:
            zone = event.get("zone", "Unknown")
            if zone not in zone_map:
                zone_map[zone] = {
                    "alerts": [], "scores": [],
                    "workers": 0, "permits": 0,
                    "compound_events": 0, "top_hazard": "Nominal",
                }
            level = event.get("risk_level", "LOW")
            zone_map[zone]["scores"].append(_COMPOUND_WEIGHTS.get(level, 5))
            zone_map[zone]["compound_events"] += 1
            zone_map[zone]["top_hazard"] = event.get("title", zone_map[zone]["top_hazard"])

        # Overlay permit data
        for validation in permit_validations:
            zone = validation.get("zone", "Unknown")
            if zone in zone_map:
                zone_map[zone]["permits"] += 1

        entries = []
        for zone_name, data in zone_map.items():
            score = max(data["scores"]) if data["scores"] else 5
            status = _score_to_status(score)
            entries.append(ZoneRiskEntry(
                zone_id=zone_name[:4].upper(),
                zone_name=zone_name,
                risk_score=score,
                status=status,
                active_workers=data["workers"],
                active_permits=data["permits"],
                top_hazard=data["top_hazard"],
                sensor_alerts=data["alerts"],
                compound_events=data["compound_events"],
            ))

        entries.sort(key=lambda z: z.risk_score, reverse=True)
        return entries

    def _build_action_queue(
        self,
        events: list[dict],
        permit_validations: list[dict],
        critical_gaps: list[str],
    ) -> list[ActionItem]:
        """Build prioritised list of required actions."""
        actions: list[ActionItem] = []
        counter = 0

        # From compound risk events
        priority_map = {
            "CRITICAL": ActionPriority.IMMEDIATE,
            "HIGH":     ActionPriority.URGENT,
            "MEDIUM":   ActionPriority.SCHEDULED,
            "LOW":      ActionPriority.MONITOR,
        }
        for event in events:
            counter += 1
            level = event.get("risk_level", "LOW")
            recommended = event.get("recommended_actions", [])
            actions.append(ActionItem(
                action_id=f"ACT-CRE-{counter:03d}",
                priority=priority_map.get(level, ActionPriority.MONITOR),
                source="COMPOUND_RISK",
                zone=event.get("zone", "Unknown"),
                title=event.get("title", "Compound Risk"),
                description=recommended[0] if recommended else event.get("description", ""),
                regulatory_refs=event.get("regulatory_refs", []),
                estimated_resolution_minutes=30 if level == "CRITICAL" else 60,
            ))

        # From blocked permits
        for validation in permit_validations:
            if not validation.get("approved", True):
                counter += 1
                actions.append(ActionItem(
                    action_id=f"ACT-PTW-{counter:03d}",
                    priority=ActionPriority.IMMEDIATE,
                    source="PERMIT",
                    zone=validation.get("zone", "Unknown"),
                    title=f"Permit {validation.get('permit_id','?')} BLOCKED",
                    description=validation.get("ai_recommendation", "Permit denied — resolve blocking issues."),
                    regulatory_refs=validation.get("regulatory_basis", []),
                    estimated_resolution_minutes=45,
                ))

        # From compliance gaps
        for gap in critical_gaps:
            counter += 1
            actions.append(ActionItem(
                action_id=f"ACT-COMP-{counter:03d}",
                priority=ActionPriority.URGENT,
                source="COMPLIANCE",
                zone="Plant-Wide",
                title="Critical Compliance Gap",
                description=gap,
                estimated_resolution_minutes=120,
            ))

        # Sort: IMMEDIATE first
        priority_order = {
            ActionPriority.IMMEDIATE: 0,
            ActionPriority.URGENT:    1,
            ActionPriority.SCHEDULED: 2,
            ActionPriority.MONITOR:   3,
        }
        actions.sort(key=lambda a: priority_order[a.priority])
        return actions

    def to_api_response(self, summary: PlantRiskSummary) -> dict[str, Any]:
        """Serialise PlantRiskSummary for REST/WebSocket."""
        return {
            "timestamp": summary.timestamp.isoformat(),
            "plant_risk_score": summary.plant_risk_score,
            "plant_status": summary.plant_status.value,
            "summary_text": summary.summary_text,
            "false_negative_risk": summary.false_negative_risk,
            "prediction_lead_time_hours": summary.prediction_lead_time_hours,
            "counts": {
                "critical": summary.critical_count,
                "high": summary.high_count,
                "medium": summary.medium_count,
                "workers_at_risk": summary.total_workers_at_risk,
            },
            "zones": [
                {
                    "zone_id": z.zone_id,
                    "zone_name": z.zone_name,
                    "risk_score": z.risk_score,
                    "status": z.status.value,
                    "active_workers": z.active_workers,
                    "active_permits": z.active_permits,
                    "top_hazard": z.top_hazard,
                    "sensor_alerts": z.sensor_alerts,
                    "compound_events": z.compound_events,
                }
                for z in summary.zones
            ],
            "action_queue": [
                {
                    "action_id": a.action_id,
                    "priority": a.priority.value,
                    "source": a.source,
                    "zone": a.zone,
                    "title": a.title,
                    "description": a.description,
                    "regulatory_refs": a.regulatory_refs,
                    "estimated_resolution_minutes": a.estimated_resolution_minutes,
                    "assigned_to": a.assigned_to,
                    "timestamp": a.timestamp.isoformat(),
                }
                for a in summary.action_queue
            ],
        }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _score_to_status(score: int) -> PlantStatus:
    for threshold, status in _STATUS_THRESHOLDS:
        if score >= threshold:
            return status
    return PlantStatus.SAFE


def _false_negative_risk(
    score: int,
    critical_gaps: list[str],
    events: list[dict],
) -> str:
    """
    Estimate the probability that we are missing an undetected risk.
    HIGH = dangerous conditions exist but score is not reflecting them.
    """
    unconfirmed_isolations = sum(
        1 for e in events
        if "isolation" in str(e.get("contributing_factors", "")).lower()
        and "NOT CONFIRMED" in str(e.get("contributing_factors", ""))
    )
    compliance_gap_count = len(critical_gaps)

    if compliance_gap_count >= 3 or unconfirmed_isolations >= 2:
        return "HIGH"
    if compliance_gap_count >= 1 or unconfirmed_isolations >= 1:
        return "MEDIUM"
    return "LOW"


def _generate_summary(
    score: int,
    status: PlantStatus,
    critical_count: int,
    high_count: int,
    zones: list[ZoneRiskEntry],
) -> str:
    hottest_zone = zones[0].zone_name if zones else "plant-wide"
    if status == PlantStatus.CRITICAL:
        return (
            f"CRITICAL: Plant risk at {score}/100 — {critical_count} critical compound events "
            f"in {hottest_zone} require IMMEDIATE intervention."
        )
    if status == PlantStatus.DANGER:
        return (
            f"DANGER: Risk score {score}/100 — {high_count} high-severity events active. "
            f"Safety officer action required in {hottest_zone}."
        )
    if status in (PlantStatus.ELEVATED, PlantStatus.CAUTION):
        return (
            f"ELEVATED ({score}/100): {high_count + critical_count} events flagged. "
            f"Monitor {hottest_zone} closely and verify permit conditions."
        )
    return f"Plant status SAFE ({score}/100). No compound risk conditions detected."