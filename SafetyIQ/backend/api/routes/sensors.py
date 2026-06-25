"""
SafetyIQ — Sensor Routes
=========================
REST endpoints for sensor telemetry, zone risk aggregation,
sensor history, and manual threshold overrides.

Endpoints:
  GET  /api/v1/sensors                 — All current sensor readings
  GET  /api/v1/sensors/{sensor_id}     — Single sensor with 60-point history
  GET  /api/v1/sensors/zone/{zone}     — Sensors filtered to one zone
  GET  /api/v1/sensors/alerts/active   — Only sensors in warning/critical state
  POST /api/v1/sensors/{sensor_id}/ack — Acknowledge a sensor alarm
  GET  /api/v1/zones                   — Zone-level risk aggregation
  GET  /api/v1/zones/{zone_id}         — Single zone detail with all sensors

Production: readings come from MQTT → Redis pipeline.
Demo: PlantStateSimulator generates realistic drifting values.

Author: SafetyIQ Team
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["Sensors & Zones"])


# ─── Models ───────────────────────────────────────────────────────────────────

class SensorReading(BaseModel):
    sensor_id: str
    zone: str
    sensor_type: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    trend: str
    timestamp: str
    alarm_state: str        # "NORMAL" | "WARNING" | "CRITICAL"
    acknowledged: bool = False
    last_calibration: str | None = None


class SensorHistory(BaseModel):
    sensor_id: str
    sensor_type: str
    zone: str
    unit: str
    readings: list[dict]   # [{timestamp, value}]
    threshold_warning: float
    threshold_critical: float
    statistics: dict       # {min, max, mean, trend_slope}


class ZoneDetail(BaseModel):
    zone_id: str
    zone_name: str
    risk_score: int
    status: str
    active_workers: int
    active_permits: int
    sensors: list[SensorReading]
    compound_risk_events: int
    last_inspection: str | None = None


class AckRequest(BaseModel):
    acknowledged_by: str
    reason: str


# ─── In-memory alarm state (production: Redis) ────────────────────────────────

_acknowledged_alarms: dict[str, dict] = {}


# ─── Sensor Definitions ───────────────────────────────────────────────────────

SENSOR_SPECS = [
    {
        "sensor_id": "S001", "zone": "Coke Oven Battery A",
        "sensor_type": "H2S", "unit": "ppm",
        "threshold_warning": 10, "threshold_critical": 20,
        "base_value": 15.0, "drift": 0.08, "trend": "rising",
        "last_calibration": "2025-01-01",
    },
    {
        "sensor_id": "S002", "zone": "Coke Oven Battery A",
        "sensor_type": "CO", "unit": "ppm",
        "threshold_warning": 200, "threshold_critical": 400,
        "base_value": 290.0, "drift": 4.0, "trend": "rising",
        "last_calibration": "2025-01-01",
    },
    {
        "sensor_id": "S003", "zone": "Blast Furnace Zone",
        "sensor_type": "TEMP", "unit": "°C",
        "threshold_warning": 1400, "threshold_critical": 1500,
        "base_value": 1340.0, "drift": 1.5, "trend": "stable",
        "last_calibration": "2024-12-15",
    },
    {
        "sensor_id": "S004", "zone": "Chemical Storage",
        "sensor_type": "PRESSURE", "unit": "bar",
        "threshold_warning": 10, "threshold_critical": 12,
        "base_value": 8.5, "drift": 0.05, "trend": "rising",
        "last_calibration": "2025-01-05",
    },
    {
        "sensor_id": "S005", "zone": "Confined Space B7",
        "sensor_type": "O2", "unit": "%",
        "threshold_warning": 19.5, "threshold_critical": 16.0,
        "base_value": 17.8, "drift": -0.04, "trend": "falling",
        "last_calibration": "2025-01-10",
    },
    {
        "sensor_id": "S006", "zone": "Coke Oven Battery B",
        "sensor_type": "H2S", "unit": "ppm",
        "threshold_warning": 10, "threshold_critical": 20,
        "base_value": 3.0, "drift": 0.02, "trend": "stable",
        "last_calibration": "2025-01-01",
    },
    {
        "sensor_id": "S007", "zone": "Hot Strip Mill",
        "sensor_type": "TEMP", "unit": "°C",
        "threshold_warning": 900, "threshold_critical": 1000,
        "base_value": 820.0, "drift": 2.0, "trend": "stable",
        "last_calibration": "2024-12-20",
    },
    {
        "sensor_id": "S008", "zone": "Raw Material Bay",
        "sensor_type": "CO", "unit": "ppm",
        "threshold_warning": 200, "threshold_critical": 400,
        "base_value": 45.0, "drift": 1.0, "trend": "stable",
        "last_calibration": "2025-01-08",
    },
]

# Mutable live values (production: Redis HSET per sensor_id)
_live_values: dict[str, float] = {s["sensor_id"]: s["base_value"] for s in SENSOR_SPECS}


def _simulate_reading(spec: dict) -> SensorReading:
    """Apply drift + noise to produce a simulated live reading."""
    sid = spec["sensor_id"]
    noise = random.gauss(0, spec["drift"] * 0.3)
    _live_values[sid] += spec["drift"] * 0.5 + noise
    _live_values[sid] = max(0.0, min(_live_values[sid], spec["threshold_critical"] * 1.3))
    value = round(_live_values[sid], 1)

    if value >= spec["threshold_critical"]:
        alarm_state = "CRITICAL"
    elif value >= spec["threshold_warning"]:
        alarm_state = "WARNING"
    else:
        alarm_state = "NORMAL"

    return SensorReading(
        sensor_id=sid,
        zone=spec["zone"],
        sensor_type=spec["sensor_type"],
        value=value,
        unit=spec["unit"],
        threshold_warning=spec["threshold_warning"],
        threshold_critical=spec["threshold_critical"],
        trend=spec["trend"],
        timestamp=datetime.utcnow().isoformat(),
        alarm_state=alarm_state,
        acknowledged=sid in _acknowledged_alarms,
        last_calibration=spec.get("last_calibration"),
    )


def _generate_history(spec: dict, points: int = 60) -> list[dict]:
    """
    Generate synthetic history going back `points` minutes.
    Production: SELECT from TimescaleDB hypertable.
    """
    base = spec["base_value"]
    drift = spec["drift"]
    history = []
    for i in range(points, 0, -1):
        ts = datetime.utcnow() - timedelta(minutes=i)
        # Walk backwards from base with accumulated drift
        historical_value = max(0, base - drift * i * 0.5 + random.gauss(0, drift * 0.5))
        history.append({
            "timestamp": ts.isoformat(),
            "value": round(historical_value, 1),
        })
    return history


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/sensors", response_model=list[SensorReading])
async def get_all_sensors():
    """Current live readings for all sensors across the plant."""
    return [_simulate_reading(spec) for spec in SENSOR_SPECS]


@router.get("/sensors/alerts/active")
async def get_active_sensor_alerts(
    min_level: str = Query("WARNING", description="Minimum alarm level: WARNING or CRITICAL"),
):
    """
    Return only sensors currently in alarm state.
    Useful for alert panel without the full sensor payload.
    """
    readings = [_simulate_reading(spec) for spec in SENSOR_SPECS]
    levels = {"WARNING", "CRITICAL"} if min_level == "WARNING" else {"CRITICAL"}

    alerts = [r for r in readings if r.alarm_state in levels]
    unacknowledged = [r for r in alerts if not r.acknowledged]

    return {
        "total_in_alarm": len(alerts),
        "unacknowledged": len(unacknowledged),
        "critical_count": sum(1 for r in alerts if r.alarm_state == "CRITICAL"),
        "warning_count":  sum(1 for r in alerts if r.alarm_state == "WARNING"),
        "sensors": [r.model_dump() for r in alerts],
    }


@router.get("/sensors/{sensor_id}", response_model=SensorHistory)
async def get_sensor_detail(sensor_id: str, history_minutes: int = Query(60, ge=5, le=480)):
    """
    Full detail for a single sensor including recent history.
    history_minutes: how far back to fetch (5–480 minutes).
    """
    spec = next((s for s in SENSOR_SPECS if s["sensor_id"] == sensor_id), None)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")

    history = _generate_history(spec, points=history_minutes)
    values = [h["value"] for h in history]

    # Simple linear trend slope (production: use numpy or statsmodels)
    n = len(values)
    if n > 1:
        slope = (values[-1] - values[0]) / n
    else:
        slope = 0.0

    return SensorHistory(
        sensor_id=sensor_id,
        sensor_type=spec["sensor_type"],
        zone=spec["zone"],
        unit=spec["unit"],
        readings=history,
        threshold_warning=spec["threshold_warning"],
        threshold_critical=spec["threshold_critical"],
        statistics={
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "mean": round(sum(values) / n, 2),
            "trend_slope_per_minute": round(slope, 4),
            "time_to_critical_minutes": _estimate_time_to_critical(
                values[-1], spec["threshold_critical"], slope
            ),
        },
    )


@router.get("/sensors/zone/{zone_name}")
async def get_sensors_by_zone(zone_name: str):
    """All sensors for a specific zone."""
    matching_specs = [s for s in SENSOR_SPECS if s["zone"].lower() == zone_name.lower()]
    if not matching_specs:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_name}' not found or has no sensors")
    readings = [_simulate_reading(spec) for spec in matching_specs]
    return {
        "zone": zone_name,
        "sensor_count": len(readings),
        "alert_count": sum(1 for r in readings if r.alarm_state != "NORMAL"),
        "sensors": [r.model_dump() for r in readings],
    }


@router.post("/sensors/{sensor_id}/ack")
async def acknowledge_sensor_alarm(sensor_id: str, body: AckRequest):
    """
    Acknowledge a sensor alarm.
    Production: writes to audit log + clears alarm in Redis.
    Acknowledged alarms still appear in history but are de-prioritised in UI.
    """
    spec = next((s for s in SENSOR_SPECS if s["sensor_id"] == sensor_id), None)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")

    _acknowledged_alarms[sensor_id] = {
        "acknowledged_by": body.acknowledged_by,
        "reason": body.reason,
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {
        "sensor_id": sensor_id,
        "acknowledged": True,
        "acknowledged_by": body.acknowledged_by,
        "timestamp": datetime.utcnow().isoformat(),
        "warning": (
            "Alarm acknowledged but sensor is still in active alarm state. "
            "Physical investigation is mandatory per OISD 105 Section 4.1."
        ),
    }


@router.get("/zones")
async def get_zones():
    """Zone-level risk aggregation across all plant areas."""
    readings = [_simulate_reading(spec) for spec in SENSOR_SPECS]

    zone_data: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "sensors": [], "scores": [], "alert_count": 0
    })

    for reading in readings:
        z = reading.zone
        zone_data[z]["sensors"].append(reading.model_dump())
        pct = int((reading.value / reading.threshold_critical) * 100)
        zone_data[z]["scores"].append(pct)
        if reading.alarm_state != "NORMAL":
            zone_data[z]["alert_count"] += 1

    result = []
    for zone_name, data in zone_data.items():
        score = max(data["scores"]) if data["scores"] else 0
        if score >= 91:
            status = "CRITICAL"
        elif score >= 76:
            status = "DANGER"
        elif score >= 56:
            status = "ELEVATED"
        elif score >= 31:
            status = "CAUTION"
        else:
            status = "SAFE"

        result.append({
            "zone_id": zone_name[:4].upper(),
            "zone_name": zone_name,
            "risk_score": score,
            "status": status,
            "active_workers": random.randint(3, 15),
            "active_permits": random.randint(0, 3),
            "alert_count": data["alert_count"],
            "sensor_count": len(data["sensors"]),
        })

    result.sort(key=lambda z: z["risk_score"], reverse=True)
    return result


@router.get("/zones/{zone_id}", response_model=ZoneDetail)
async def get_zone_detail(zone_id: str):
    """
    Full zone detail: all sensors, risk score, active permit count.
    zone_id can be the full zone name or the 4-char shortcode.
    """
    # Match by name or 4-char ID
    zone_specs = [
        s for s in SENSOR_SPECS
        if s["zone"].lower() == zone_id.lower()
        or s["zone"][:4].upper() == zone_id.upper()
    ]
    if not zone_specs:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")

    zone_name = zone_specs[0]["zone"]
    readings = [_simulate_reading(spec) for spec in zone_specs]
    scores = [int((r.value / r.threshold_critical) * 100) for r in readings]
    risk_score = max(scores) if scores else 0

    if risk_score >= 91:   status = "CRITICAL"
    elif risk_score >= 76: status = "DANGER"
    elif risk_score >= 56: status = "ELEVATED"
    elif risk_score >= 31: status = "CAUTION"
    else:                  status = "SAFE"

    return ZoneDetail(
        zone_id=zone_name[:4].upper(),
        zone_name=zone_name,
        risk_score=risk_score,
        status=status,
        active_workers=random.randint(3, 15),
        active_permits=random.randint(0, 3),
        sensors=readings,
        compound_risk_events=random.randint(0, 3),
        last_inspection=(datetime.utcnow() - timedelta(days=random.randint(5, 90))).strftime("%Y-%m-%d"),
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _estimate_time_to_critical(current: float, critical: float, slope: float) -> float | None:
    """
    Given current value, critical threshold, and slope (per minute),
    estimate minutes until critical threshold is breached.
    Returns None if slope is non-positive (not approaching critical).
    """
    if slope <= 0 or current >= critical:
        return None
    remaining = critical - current
    return round(remaining / slope, 1)