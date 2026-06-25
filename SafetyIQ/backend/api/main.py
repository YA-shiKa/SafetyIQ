"""
SafetyIQ — FastAPI Backend
===========================
REST + WebSocket API serving the SafetyIQ frontend.
 
Endpoints:
  GET  /api/v1/sensors          — Current sensor readings
  GET  /api/v1/alerts           — Active alerts
  GET  /api/v1/zones            — Plant zone risk map
  POST /api/v1/analyze          — Trigger compound risk analysis
  POST /api/v1/permits/validate — Validate permit against live conditions
  POST /api/v1/emergency        — Activate emergency orchestrator
  GET  /api/v1/incidents        — Historical incident patterns
  GET  /api/v1/compliance       — Compliance status
  WS   /ws/live                 — Live sensor stream
 
Author: SafetyIQ Team
"""
 
from __future__ import annotations
 
import asyncio
import json
import logging
import math
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any
 
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
 
logger = logging.getLogger(__name__)
 
# ─── Pydantic Models ──────────────────────────────────────────────────────────
 
class SensorDataPoint(BaseModel):
    sensor_id: str
    zone: str
    sensor_type: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    trend: str
    timestamp: str
 
 
class AlertModel(BaseModel):
    alert_id: str
    severity: str
    alert_type: str
    title: str
    description: str
    zone: str
    compound_factors: list[str] = []
    timestamp: str
    acknowledged: bool = False
 
 
class ZoneRiskModel(BaseModel):
    zone_id: str
    name: str
    risk_score: int
    status: str
    active_workers: int
    active_permits: int
 
 
class AnalyzeRequest(BaseModel):
    zone: str | None = None
    include_patterns: bool = True
    include_compliance: bool = True
 
 
class PermitValidationRequest(BaseModel):
    permit_id: str
    permit_type: str
    zone: str
    requested_by: str
    planned_workers: int
    start_time: str
    duration_hours: float
 
 
class PermitValidationResult(BaseModel):
    permit_id: str
    approved: bool
    risk_level: str
    conditions: list[str]
    blocking_issues: list[str]
    ai_recommendation: str
    regulatory_refs: list[str]
 
 
class EmergencyTriggerRequest(BaseModel):
    zone: str
    emergency_type: str
    description: str
    triggered_by: str = "MANUAL"
    workers_in_zone: int = 0
 
 
class ComplianceStatus(BaseModel):
    overall_score: int
    oisd_score: int
    factory_act_score: int
    dgms_score: int
    open_findings: int
    critical_gaps: list[str]
    last_audit: str
    next_audit: str
 
 
# ─── Mock State (Production: PostgreSQL + Redis) ──────────────────────────────
 
class PlantStateSimulator:
    """
    Simulates live sensor data for demo.
    Production: reads from MQTT/SCADA data bus.
    """
 
    BASE_SENSORS = [
        {"sensor_id": "S001", "zone": "Coke Oven Battery A", "sensor_type": "H2S",
         "base_value": 15.0, "unit": "ppm", "threshold_warning": 10, "threshold_critical": 20, "trend": "rising", "drift": 0.08},
        {"sensor_id": "S002", "zone": "Coke Oven Battery A", "sensor_type": "CO",
         "base_value": 290.0, "unit": "ppm", "threshold_warning": 200, "threshold_critical": 400, "trend": "rising", "drift": 4.0},
        {"sensor_id": "S003", "zone": "Blast Furnace Zone", "sensor_type": "TEMP",
         "base_value": 1340.0, "unit": "°C", "threshold_warning": 1400, "threshold_critical": 1500, "trend": "stable", "drift": 1.5},
        {"sensor_id": "S004", "zone": "Chemical Storage", "sensor_type": "PRESSURE",
         "base_value": 8.5, "unit": "bar", "threshold_warning": 10, "threshold_critical": 12, "trend": "rising", "drift": 0.05},
        {"sensor_id": "S005", "zone": "Confined Space B7", "sensor_type": "O2",
         "base_value": 17.8, "unit": "%", "threshold_warning": 19.5, "threshold_critical": 16.0, "trend": "falling", "drift": -0.04},
        {"sensor_id": "S006", "zone": "Coke Oven Battery B", "sensor_type": "H2S",
         "base_value": 3.0, "unit": "ppm", "threshold_warning": 10, "threshold_critical": 20, "trend": "stable", "drift": 0.02},
        {"sensor_id": "S007", "zone": "Hot Strip Mill", "sensor_type": "TEMP",
         "base_value": 820.0, "unit": "°C", "threshold_warning": 900, "threshold_critical": 1000, "trend": "stable", "drift": 2.0},
        {"sensor_id": "S008", "zone": "Raw Material Bay", "sensor_type": "CO",
         "base_value": 45.0, "unit": "ppm", "threshold_warning": 200, "threshold_critical": 400, "trend": "stable", "drift": 1.0},
    ]
 
    def __init__(self):
        self._tick = 0
        self._values = {s["sensor_id"]: s["base_value"] for s in self.BASE_SENSORS}
 
    def get_readings(self) -> list[dict]:
        self._tick += 1
        readings = []
        for sensor in self.BASE_SENSORS:
            sid = sensor["sensor_id"]
            # Apply drift + noise
            noise = random.gauss(0, sensor["drift"] * 0.3)
            self._values[sid] += sensor["drift"] * 0.5 + noise
            # Keep within realistic bounds (prevent runaway)
            self._values[sid] = max(0, min(self._values[sid], sensor["threshold_critical"] * 1.3))
 
            value = round(self._values[sid], 1)
            readings.append({
                **{k: v for k, v in sensor.items() if k not in ("drift",)},
                "value": value,
                "timestamp": datetime.utcnow().isoformat(),
            })
        return readings
 
    def get_zone_risks(self) -> list[dict]:
        readings = self.get_readings()
        zones = {}
        for r in readings:
            z = r["zone"]
            if z not in zones:
                zones[z] = {"zone_id": z[:4].upper(), "name": z, "risk_score": 0,
                             "sensor_count": 0, "alert_count": 0}
            pct = (r["value"] / r["threshold_critical"]) * 100
            zones[z]["risk_score"] = max(zones[z]["risk_score"], int(pct))
            zones[z]["sensor_count"] += 1
            if r["value"] >= r["threshold_warning"]:
                zones[z]["alert_count"] += 1
 
        result = []
        for z, data in zones.items():
            score = data["risk_score"]
            status = "SAFE" if score < 45 else "CAUTION" if score < 65 else "DANGER" if score < 85 else "CRITICAL"
            result.append({
                **data,
                "risk_score": score,
                "status": status,
                "active_workers": random.randint(3, 15),
                "active_permits": random.randint(0, 3),
            })
        return result
 
 
simulator = PlantStateSimulator()
 
 
# ─── WebSocket Manager ────────────────────────────────────────────────────────
 
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
 
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
 
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
 
    async def broadcast(self, data: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data))
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)
 
 
ws_manager = ConnectionManager()
 
 
# ─── Background Tasks ─────────────────────────────────────────────────────────
 
async def broadcast_sensor_loop():
    """Broadcast live sensor data every 2 seconds."""
    while True:
        try:
            readings = simulator.get_readings()
            await ws_manager.broadcast({
                "type": "SENSOR_UPDATE",
                "timestamp": datetime.utcnow().isoformat(),
                "sensors": readings,
                "plant_risk_score": max(
                    int((r["value"] / r["threshold_critical"]) * 100)
                    for r in readings
                ),
            })
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
        await asyncio.sleep(2)
 
 
# ─── App Lifecycle ────────────────────────────────────────────────────────────
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background broadcast
    task = asyncio.create_task(broadcast_sensor_loop())
    logger.info("SafetyIQ backend started. Live sensor broadcast active.")
    yield
    task.cancel()
    logger.info("SafetyIQ backend shutting down.")
 
 
app = FastAPI(
    title="SafetyIQ API",
    description="AI-Powered Industrial Safety Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
# ─── Routes ───────────────────────────────────────────────────────────────────
 
@app.get("/")
async def root():
    return {"service": "SafetyIQ API", "version": "1.0.0", "status": "operational"}
 
 
@app.get("/api/v1/sensors", response_model=list[SensorDataPoint])
async def get_sensors():
    """Current sensor readings across all zones."""
    return simulator.get_readings()
 
 
@app.get("/api/v1/zones")
async def get_zones():
    """Zone-level risk aggregation."""
    return simulator.get_zone_risks()
 
 
@app.get("/api/v1/alerts")
async def get_alerts():
    """Active alerts generated by compound risk engine."""
    return {
        "alerts": [
            {
                "alert_id": "A001", "severity": "CRITICAL", "alert_type": "COMPOUND_RISK",
                "title": "Compound Risk: Confined Space Entry + Oxygen Deficiency + Shift Changeover",
                "description": "Three simultaneous risk factors detected. O₂ at 17.2% and falling. Confined space permit PTW-2847 active with 4 workers. Shift changeover in 8 minutes.",
                "zone": "Confined Space B7",
                "compound_factors": ["O₂ below 19.5% (OISD 116)", "Active confined space permit", "Shift changeover imminent", "H₂S rising trend in adjacent zone"],
                "timestamp": (datetime.utcnow() - timedelta(minutes=12)).isoformat(),
                "acknowledged": False,
            },
            {
                "alert_id": "A002", "severity": "HIGH", "alert_type": "PERMIT",
                "title": "Hot Work Permit Near Elevated Flammable Gas Zone",
                "description": "PTW-2851 hot work permit active in Coke Oven Battery A. CO at 312 ppm (warning: 200 ppm). Isolation barrier not confirmed in permit record.",
                "zone": "Coke Oven Battery A",
                "compound_factors": ["Hot work permit active", "CO exceeds warning threshold", "Isolation not confirmed in PTW"],
                "timestamp": (datetime.utcnow() - timedelta(minutes=22)).isoformat(),
                "acknowledged": False,
            },
            {
                "alert_id": "A003", "severity": "HIGH", "alert_type": "MAINTENANCE",
                "title": "Pressure Anomaly — Overdue PRV Under Rising Load",
                "description": "Pressure relief valve PRV-004 in Chemical Storage is 17 days overdue for inspection. Current pressure 8.5 bar with rising trend. OISD 118 Section 8.4 requires downgrade to 75% design pressure when overdue.",
                "zone": "Chemical Storage",
                "compound_factors": ["PRV inspection 17 days overdue", "Pressure trending up", "OISD 118 violation if pressure exceeds 75% design"],
                "timestamp": (datetime.utcnow() - timedelta(minutes=35)).isoformat(),
                "acknowledged": False,
            },
            {
                "alert_id": "A004", "severity": "MEDIUM", "alert_type": "COMPLIANCE",
                "title": "4 Active Permits Missing Isolation Certificates — OISD 105",
                "description": "OISD Standard 105 Section 6.1 mandates isolation certificate attached to all confined space and hot work permits. 4 of 8 active permits non-compliant.",
                "zone": "Multiple",
                "compound_factors": ["PTW-2847 missing isolation cert", "PTW-2851 missing isolation cert", "OISD 105 Section 6.1 non-compliance"],
                "timestamp": (datetime.utcnow() - timedelta(hours=1, minutes=15)).isoformat(),
                "acknowledged": True,
            },
        ],
        "total": 4,
        "critical_count": 1,
        "unacknowledged_count": 3,
    }
 
 
@app.post("/api/v1/analyze")
async def run_analysis(request: AnalyzeRequest):
    """
    Trigger full compound risk analysis using AI agents.
    Production: calls CompoundRiskAgent + IncidentPatternAgent.
    Demo: returns pre-computed rich analysis.
    """
    return {
        "analysis_id": f"ANA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.utcnow().isoformat(),
        "plant_risk_score": 78,
        "compound_risks": [
            {
                "event_id": "CRE-001",
                "risk_level": "CRITICAL",
                "title": "Oxygen Deficiency + Confined Space Entry + Imminent Shift Handover",
                "description": "Three converging risk factors create a critical compound hazard. O₂ at 17.2% (OISD threshold: 19.5%) is falling at 0.15%/min. Four workers under active confined space permit PTW-2847. Shift changeover in 8 minutes risks communication gaps in safety oversight.",
                "contributing_factors": [
                    "O₂: 17.2% (-0.15%/min falling trend)",
                    "Confined space permit PTW-2847 active — 4 workers",
                    "Shift changeover in 8 minutes",
                    "SCBA stock: 2 units (min required: 4 for 4 workers + 2 standby)",
                ],
                "recommended_actions": [
                    "IMMEDIATE: Halt confined space entry — suspend PTW-2847",
                    "Initiate emergency evacuation of Zone B7",
                    "Delay shift changeover until O₂ restored above 19.5%",
                    "Ventilate Zone B7 and retest atmosphere",
                ],
                "confidence_score": 0.94,
                "lead_time_hours": 0.75,
                "regulatory_refs": ["OISD 116 Section 4.1 (SCBA mandatory < 19.5% O₂)", "Factory Act 1948 Section 36A"],
            }
        ],
        "incident_patterns": [
            {
                "pattern_name": "Atmospheric Testing Gap Before Confined Space Entry",
                "description": "Pattern identified in 4 of 5 retrieved incidents: pre-entry atmospheric testing conducted but not repeated at 2-hour intervals as required by OISD 105 Section 4.3.",
                "recurrence_count": 4,
                "severity_potential": "FATAL",
                "current_condition_match": 0.91,
                "prevention_priority": "Automate atmospheric re-test reminders at 90-minute intervals for all confined space permits",
            }
        ],
    }
 
 
@app.post("/api/v1/permits/validate", response_model=PermitValidationResult)
async def validate_permit(request: PermitValidationRequest):
    """
    Validate a permit against live plant conditions using AI.
    Production: calls PermitIntelAgent with real sensor state.
    """
    readings = simulator.get_readings()
    zone_readings = [r for r in readings if r["zone"] == request.zone]
 
    alerts = []
    issues = []
 
    for r in zone_readings:
        if r["value"] >= r["threshold_critical"]:
            issues.append(f"BLOCKING: {r['sensor_type']} at {r['value']}{r['unit']} exceeds critical threshold — permit must be suspended")
        elif r["value"] >= r["threshold_warning"]:
            alerts.append(f"WARNING: {r['sensor_type']} at {r['value']}{r['unit']} above warning threshold — additional precautions required")
 
    approved = len(issues) == 0
    risk_level = "CRITICAL" if not approved else ("HIGH" if alerts else "MEDIUM")
 
    return PermitValidationResult(
        permit_id=request.permit_id,
        approved=approved,
        risk_level=risk_level,
        conditions=alerts + [
            "Mandatory atmospheric testing every 90 minutes (OISD 105 Section 4.3)",
            "Isolation certificate required before work commences (OISD 105 Section 6.1)",
            f"Minimum {max(2, request.planned_workers // 2)} standby personnel at entry point",
        ],
        blocking_issues=issues,
        ai_recommendation=(
            "DENY PERMIT: Critical atmospheric conditions present. " + " ".join(issues)
            if issues else
            f"CONDITIONAL APPROVAL: {len(alerts)} warning conditions require enhanced precautions. " + " ".join(alerts[:2])
        ),
        regulatory_refs=[
            "OISD 105 Section 4.3 (PTW — Confined Space)",
            "OISD 116 Section 4.1 (Respiratory Equipment)",
            "Factory Act 1948 Section 36A (Dangerous Fumes)",
        ],
    )
 
 
@app.post("/api/v1/emergency")
async def trigger_emergency(request: EmergencyTriggerRequest, background_tasks: BackgroundTasks):
    """
    Activate Emergency Response Orchestrator.
    Returns immediately with response ID; orchestration runs in background.
    """
    response_id = f"ER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    logger.warning(f"🚨 Emergency triggered: {request.emergency_type} in {request.zone}")
 
    # In production, call EmergencyOrchestrator.activate() here
    return {
        "response_id": response_id,
        "status": "ACTIVATED",
        "message": "Emergency orchestrator activated. Response underway.",
        "actions_initiated": [
            "PA evacuation broadcast",
            "SMS alerts: Safety Officer + Hospital + Fire Station",
            "SCADA lockdown: all permits in affected zone suspended",
            "Sensor evidence snapshot locked",
            "CCTV footage preserved (2hr buffer)",
            "DGFASLI Form 18 draft being generated",
        ],
        "estimated_completion_seconds": 10,
        "incident_report_id": f"RPT-{response_id}",
    }
 
 
@app.get("/api/v1/compliance")
async def get_compliance():
    """Compliance monitoring status across OISD/Factory Act/DGMS."""
    return ComplianceStatus(
        overall_score=73,
        oisd_score=78,
        factory_act_score=82,
        dgms_score=61,
        open_findings=14,
        critical_gaps=[
            "OISD 116: 4 confined space permits lack pre-entry atmospheric test records",
            "DGMS Circular 2019-03: Rescue drill overdue (last conducted 8 months ago)",
            "Factory Act Section 31: PRV-004 inspection overdue — pressure vessel at risk",
            "OISD 105 Section 7.2: No SIMOPs assessment for today's concurrent operations",
        ],
        last_audit="2024-10-15",
        next_audit="2025-04-15",
    ).model_dump()
 
 
@app.get("/api/v1/incidents")
async def get_incident_history():
    """Historical incident patterns from RAG corpus."""
    return {
        "total_incidents": 47,
        "fatalities_ytd": 0,
        "near_misses_ytd": 12,
        "dangerous_occurrences_ytd": 3,
        "top_patterns": [
            {"pattern": "PTW-sensor disconnect", "recurrence": 7, "last_occurrence": "2024-08-22"},
            {"pattern": "Shift changeover gap", "recurrence": 5, "last_occurrence": "2024-11-14"},
            {"pattern": "Overdue maintenance under load", "recurrence": 5, "last_occurrence": "2024-03-11"},
        ],
        "recent_incidents": [
            {"id": "NM-2025-003", "date": "2025-01-10", "type": "NEAR_MISS", "zone": "Blast Furnace", "description": "Gas sensor alarm ignored for 8 minutes due to alert fatigue. No injury."},
            {"id": "NM-2025-002", "date": "2025-01-07", "type": "NEAR_MISS", "zone": "Chemical Storage", "description": "Pressure anomaly undetected for 3 hours — SCADA operator on break."},
        ],
    }
 
 
@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "sensors_active": len(simulator.BASE_SENSORS),
        "websocket_connections": len(ws_manager.active_connections),
    }
 
 
# ─── WebSocket ────────────────────────────────────────────────────────────────
 
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    Live sensor data stream.
    Client receives updates every 2 seconds with full plant state.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial state immediately
        await websocket.send_text(json.dumps({
            "type": "CONNECTED",
            "message": "SafetyIQ live stream active",
            "sensors": simulator.get_readings(),
        }))
 
        while True:
            # Keep connection alive; broadcasts are sent by broadcast_sensor_loop
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
 
    except (WebSocketDisconnect, asyncio.TimeoutError):
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
 
 
# ─── Run ──────────────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)