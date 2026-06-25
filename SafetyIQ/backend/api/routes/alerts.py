"""
SafetyIQ — Alerts Routes
=========================
REST endpoints for compound risk alerts.

Endpoints:
  GET  /api/v1/alerts              — All active alerts
  GET  /api/v1/alerts/{alert_id}   — Single alert detail
  POST /api/v1/alerts/{alert_id}/ack — Acknowledge alert
  GET  /api/v1/alerts/summary      — Counts by severity

Author: SafetyIQ Team
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


# ─── Models ───────────────────────────────────────────────────────────────────

class AckRequest(BaseModel):
    acknowledged_by: str
    reason: str = ""


# ─── Mock alert store (Production: PostgreSQL + Redis pub/sub) ─────────────────

_ALERTS: list[dict[str, Any]] = [
    {
        "alert_id": "A001",
        "severity": "CRITICAL",
        "alert_type": "COMPOUND_RISK",
        "title": "Compound Risk: Confined Space Entry + Oxygen Deficiency + Shift Changeover",
        "description": (
            "Three simultaneous risk factors detected. O₂ at 17.2% and falling. "
            "Confined space permit PTW-2847 active with 4 workers. Shift changeover in 8 minutes."
        ),
        "zone": "Confined Space B7",
        "compound_factors": [
            "O₂ below 19.5% (OISD 116 — SCBA mandatory)",
            "Active confined space permit PTW-2847 (4 workers)",
            "Shift changeover in 8 minutes",
            "H₂S rising trend in adjacent Coke Oven Battery A",
        ],
        "timestamp": (datetime.utcnow() - timedelta(minutes=12)).isoformat(),
        "acknowledged": False,
        "regulatory_refs": ["OISD 116 Section 4.1", "Factory Act 1948 Section 36A"],
        "recommended_action": "IMMEDIATE: Halt confined space entry. Suspend PTW-2847. Ventilate Zone B7.",
    },
    {
        "alert_id": "A002",
        "severity": "HIGH",
        "alert_type": "PERMIT",
        "title": "Hot Work Permit Near Elevated Flammable Gas Zone",
        "description": (
            "PTW-2851 hot work permit active in Coke Oven Battery A. "
            "CO at 312 ppm (warning: 200 ppm). Isolation barrier not confirmed in permit record."
        ),
        "zone": "Coke Oven Battery A",
        "compound_factors": [
            "Hot work permit PTW-2851 active",
            "CO at 312 ppm (warning: 200 ppm) — rising trend",
            "H₂S at 18.4 ppm (warning: 10 ppm)",
            "Isolation not confirmed in PTW",
        ],
        "timestamp": (datetime.utcnow() - timedelta(minutes=22)).isoformat(),
        "acknowledged": False,
        "regulatory_refs": ["OISD 105 Section 6.1", "Factory Act 1948 Section 36"],
        "recommended_action": "Suspend PTW-2851 until isolation is confirmed and gas readings normalise.",
    },
    {
        "alert_id": "A003",
        "severity": "HIGH",
        "alert_type": "MAINTENANCE",
        "title": "Pressure Anomaly — Overdue PRV Under Rising Load",
        "description": (
            "Pressure relief valve PRV-004 in Chemical Storage is 17 days overdue for inspection. "
            "Current pressure 8.5 bar with rising trend. OISD 118 Section 8.4 requires downgrade "
            "to 75% design pressure when overdue."
        ),
        "zone": "Chemical Storage",
        "compound_factors": [
            "PRV-004 inspection 17 days overdue (OISD 118 Section 8.4)",
            "Current pressure: 8.5 bar (warning: 10 bar) — rising",
            "Overdue inspection + rising pressure = compound failure risk",
        ],
        "timestamp": (datetime.utcnow() - timedelta(minutes=35)).isoformat(),
        "acknowledged": False,
        "regulatory_refs": ["OISD 118 Section 8.4", "Factory Act 1948 Section 31"],
        "recommended_action": "Reduce operating pressure to 75% design. Schedule PRV inspection within 48 hours.",
    },
    {
        "alert_id": "A004",
        "severity": "MEDIUM",
        "alert_type": "COMPLIANCE",
        "title": "4 Active Permits Missing Isolation Certificates — OISD 105",
        "description": (
            "OISD Standard 105 Section 6.1 mandates isolation certificate attached to all "
            "confined space and hot work permits. 4 of 8 active permits are non-compliant."
        ),
        "zone": "Multiple",
        "compound_factors": [
            "PTW-2847 missing isolation cert",
            "PTW-2851 missing isolation cert",
            "PTW-2853 missing isolation cert + no atmospheric test",
            "OISD 105 Section 6.1 non-compliance",
        ],
        "timestamp": (datetime.utcnow() - timedelta(hours=1, minutes=15)).isoformat(),
        "acknowledged": True,
        "regulatory_refs": ["OISD 105 Section 6.1"],
        "recommended_action": "Halt all affected operations until isolation certificates are attached and verified.",
    },
    {
        "alert_id": "A005",
        "severity": "MEDIUM",
        "alert_type": "COMPLIANCE",
        "title": "Emergency Rescue Drill Overdue — 8 Months Since Last Drill",
        "description": (
            "DGMS Circular 2019-03 requires emergency rescue drills every 6 months. "
            "Last drill was conducted 8 months ago."
        ),
        "zone": "Plant-Wide",
        "compound_factors": [
            "Last rescue drill: April 2024 (8 months ago)",
            "DGMS Circular 2019-03 requires 6-month intervals",
            "2 months overdue",
        ],
        "timestamp": (datetime.utcnow() - timedelta(hours=6)).isoformat(),
        "acknowledged": False,
        "regulatory_refs": ["DGMS Circular 2019-03"],
        "recommended_action": "Schedule rescue drill within 14 days. Include confined space + gas leak scenarios.",
    },
]

_acknowledged: dict[str, dict] = {}


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def get_alerts(severity: str | None = None, acknowledged: bool | None = None):
    """
    All active alerts with optional filtering.

    Query params:
      severity: CRITICAL | HIGH | MEDIUM | LOW
      acknowledged: true | false
    """
    alerts = list(_ALERTS)

    if severity:
        alerts = [a for a in alerts if a["severity"] == severity.upper()]
    if acknowledged is not None:
        alerts = [a for a in alerts if a["acknowledged"] == acknowledged]

    return {
        "alerts": alerts,
        "total": len(alerts),
        "critical_count": sum(1 for a in alerts if a["severity"] == "CRITICAL"),
        "high_count": sum(1 for a in alerts if a["severity"] == "HIGH"),
        "unacknowledged_count": sum(1 for a in alerts if not a["acknowledged"]),
    }


@router.get("/summary")
async def get_alert_summary():
    """Lightweight summary for sidebar badge counts."""
    return {
        "total": len(_ALERTS),
        "critical": sum(1 for a in _ALERTS if a["severity"] == "CRITICAL"),
        "high": sum(1 for a in _ALERTS if a["severity"] == "HIGH"),
        "medium": sum(1 for a in _ALERTS if a["severity"] == "MEDIUM"),
        "unacknowledged": sum(1 for a in _ALERTS if not a["acknowledged"]),
    }


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    """Full alert detail including regulatory references."""
    alert = next((a for a in _ALERTS if a["alert_id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert


@router.post("/{alert_id}/ack")
async def acknowledge_alert(alert_id: str, body: AckRequest):
    """
    Acknowledge an alert.
    Production: writes to audit log, removes from active queue in Redis.
    Acknowledged alerts remain visible in history.
    """
    alert = next((a for a in _ALERTS if a["alert_id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    alert["acknowledged"] = True
    _acknowledged[alert_id] = {
        "acknowledged_by": body.acknowledged_by,
        "reason": body.reason,
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {
        "alert_id": alert_id,
        "acknowledged": True,
        "acknowledged_by": body.acknowledged_by,
        "timestamp": datetime.utcnow().isoformat(),
        "note": (
            "Alert acknowledged. Physical investigation and corrective action "
            "are still required per OISD 105 Section 4.1."
        ),
    }