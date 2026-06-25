"""
SafetyIQ — Emergency Response Orchestrator
==========================================
Autonomous agent that, on confirmed trigger, immediately:
  1. Initiates zone evacuation protocol
  2. Alerts response teams across all channels (PA, SMS, email, Slack)
  3. Locks down affected permits
  4. Preserves sensor evidence (48-hr snapshot)
  5. Generates preliminary regulatory-compliant incident report (DGFASLI Form 18)
  6. Coordinates with emergency services
 
Goal: Transform the critical first 10 minutes from chaos to coordinated response.
 
Author: SafetyIQ Team
"""
 
from __future__ import annotations
 
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
 
import anthropic
 
logger = logging.getLogger(__name__)
 
 
class EmergencyType(str, Enum):
    GAS_LEAK = "GAS_LEAK"
    EXPLOSION = "EXPLOSION"
    FIRE = "FIRE"
    CONFINED_SPACE_RESCUE = "CONFINED_SPACE_RESCUE"
    STRUCTURAL_FAILURE = "STRUCTURAL_FAILURE"
    CHEMICAL_SPILL = "CHEMICAL_SPILL"
    WORKER_INJURY = "WORKER_INJURY"
    EVACUATION = "EVACUATION"
 
 
class ResponseStatus(str, Enum):
    INITIATED = "INITIATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
 
 
@dataclass
class EmergencyTrigger:
    trigger_id: str
    emergency_type: EmergencyType
    zone: str
    severity: str                    # CRITICAL, HIGH
    triggering_event: str            # Description of what triggered
    sensor_readings: list[dict]      # Current sensor state at trigger time
    active_permits: list[dict]       # Permits in affected zone
    workers_in_zone: int
    triggered_by: str               # "AUTO_AI" or officer name
    timestamp: datetime = field(default_factory=datetime.utcnow)
 
 
@dataclass
class ResponseAction:
    action_id: str
    action_type: str
    description: str
    status: ResponseStatus
    target: str                     # Who/what the action targets
    initiated_at: datetime
    completed_at: datetime | None = None
    result: str = ""
    error: str = ""
 
 
@dataclass
class IncidentReport:
    """Preliminary DGFASLI Form 18 compliant incident report."""
    report_id: str
    form_type: str = "DGFASLI_FORM_18"
    plant_name: str = ""
    plant_address: str = ""
    date_of_incident: str = ""
    time_of_incident: str = ""
    nature_of_incident: str = ""
    location_in_plant: str = ""
    equipment_involved: str = ""
    persons_affected: int = 0
    fatalities: int = 0
    injuries: int = 0
    immediate_cause: str = ""
    root_cause_preliminary: str = ""
    immediate_actions_taken: list[str] = field(default_factory=list)
    witness_names: list[str] = field(default_factory=list)
    hazardous_substances: list[str] = field(default_factory=list)
    regulatory_notification_required: list[str] = field(default_factory=list)
    generated_by_ai: bool = True
    requires_human_review: bool = True
    generated_at: datetime = field(default_factory=datetime.utcnow)
 
 
@dataclass
class EmergencyResponse:
    response_id: str
    trigger: EmergencyTrigger
    actions: list[ResponseAction] = field(default_factory=list)
    incident_report: IncidentReport | None = None
    evacuation_zones: list[str] = field(default_factory=list)
    response_start: datetime = field(default_factory=datetime.utcnow)
    response_complete: datetime | None = None
    total_elapsed_seconds: float = 0
    ai_situation_report: str = ""
 
 
# ─── Notification Channels (stub — production wires to actual systems) ─────────
 
class NotificationChannel:
    """Production: integrate with actual PA, SMS, email, Slack APIs."""
 
    @staticmethod
    async def pa_announcement(zone: str, message: str) -> bool:
        logger.info(f"[PA SYSTEM] Zone {zone}: {message}")
        await asyncio.sleep(0.2)  # Simulate API call
        return True
 
    @staticmethod
    async def sms_blast(phone_numbers: list[str], message: str) -> bool:
        logger.info(f"[SMS] Sent to {len(phone_numbers)} numbers: {message[:100]}")
        await asyncio.sleep(0.3)
        return True
 
    @staticmethod
    async def email_alert(recipients: list[str], subject: str, body: str) -> bool:
        logger.info(f"[EMAIL] To {recipients}: {subject}")
        await asyncio.sleep(0.2)
        return True
 
    @staticmethod
    async def emergency_services_call(service: str, message: str) -> bool:
        logger.info(f"[EMERGENCY SERVICES] Notified {service}: {message[:100]}")
        await asyncio.sleep(0.5)
        return True
 
    @staticmethod
    async def scada_lockdown(zone: str, permit_ids: list[str]) -> bool:
        logger.info(f"[SCADA] Locking down zone {zone}, permits: {permit_ids}")
        await asyncio.sleep(0.4)
        return True
 
 
# ─── Evidence Preservation ────────────────────────────────────────────────────
 
class EvidencePreserver:
    """Locks and archives sensor readings, CCTV frames, and logs at trigger time."""
 
    @staticmethod
    async def snapshot_sensors(trigger: EmergencyTrigger) -> str:
        """
        Production: write 48-hr rolling sensor buffer to immutable storage.
        Returns snapshot ID for regulatory purposes.
        """
        snapshot_id = f"SNAP-{trigger.trigger_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"[EVIDENCE] Sensor snapshot locked: {snapshot_id}")
        await asyncio.sleep(0.3)
        return snapshot_id
 
    @staticmethod
    async def lock_cctv_footage(zone: str, hours_back: int = 2) -> str:
        footage_id = f"CCTV-{zone.replace(' ', '_')}-{datetime.utcnow().strftime('%H%M%S')}"
        logger.info(f"[EVIDENCE] CCTV footage preserved: {footage_id} ({hours_back}h)")
        await asyncio.sleep(0.4)
        return footage_id
 
    @staticmethod
    async def archive_permits(permit_ids: list[str]) -> bool:
        logger.info(f"[EVIDENCE] Permits archived: {permit_ids}")
        await asyncio.sleep(0.2)
        return True
 
 
# ─── Main Orchestrator ────────────────────────────────────────────────────────
 
class EmergencyOrchestrator:
    """
    Autonomous emergency response orchestrator.
 
    On trigger activation, executes a parallel multi-channel response plan
    within seconds, while generating regulatory documentation in background.
    """
 
    PLANT_CONFIG = {
        "name": "Visakhapatnam Steel Complex",
        "address": "Steel Plant Road, Ukkunagaram, Visakhapatnam, Andhra Pradesh 530031",
        "emergency_contacts": {
            "plant_safety_officer": ["+91-891-2518XXX"],
            "fire_station": ["+91-891-2752XXX"],
            "hospital": ["+91-891-2744XXX"],
            "district_factory_inspector": ["+91-891-2750XXX"],
            "dgfasli_regional": ["+91-40-2312XXX"],
        },
        "zones": {
            "Coke Oven Battery A": {"adjacent": ["Coke Oven Battery B", "Blast Furnace Zone"], "workers_typical": 12},
            "Confined Space B7": {"adjacent": ["Coke Oven Battery A"], "workers_typical": 6},
        }
    }
 
    def __init__(self, anthropic_api_key: str | None = None):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.notifier = NotificationChannel()
        self.preserver = EvidencePreserver()
        self.response_log: list[EmergencyResponse] = []
 
    async def activate(self, trigger: EmergencyTrigger) -> EmergencyResponse:
        """
        Main activation sequence. Runs parallel response tracks.
        Returns complete EmergencyResponse within ~10 seconds.
        """
        logger.warning(f"🚨 EMERGENCY ACTIVATED: {trigger.emergency_type} in {trigger.zone}")
        start_time = datetime.utcnow()
 
        response = EmergencyResponse(
            response_id=f"ER-{trigger.trigger_id}",
            trigger=trigger,
        )
 
        # Determine evacuation zones (affected + adjacent)
        zone_config = self.PLANT_CONFIG["zones"].get(trigger.zone, {})
        response.evacuation_zones = [trigger.zone] + zone_config.get("adjacent", [])
 
        # Run all response tracks in parallel
        await asyncio.gather(
            self._track_evacuation(trigger, response),
            self._track_notifications(trigger, response),
            self._track_evidence(trigger, response),
            self._track_scada_lockdown(trigger, response),
            return_exceptions=True,
        )
 
        # Generate incident report (can run slightly after immediate actions)
        response.incident_report = await self._generate_incident_report(trigger, response)
 
        # AI situation report
        response.ai_situation_report = await self._generate_situation_report(trigger, response)
 
        response.response_complete = datetime.utcnow()
        response.total_elapsed_seconds = (response.response_complete - start_time).total_seconds()
 
        logger.warning(f"Emergency response complete in {response.total_elapsed_seconds:.1f}s")
        self.response_log.append(response)
        return response
 
    async def _track_evacuation(self, trigger: EmergencyTrigger, response: EmergencyResponse):
        """Track 1: Initiate evacuation across affected zones."""
        action = ResponseAction(
            action_id="ACT-EVAC-001",
            action_type="EVACUATION",
            description=f"Evacuate {', '.join(response.evacuation_zones)}",
            status=ResponseStatus.IN_PROGRESS,
            target=", ".join(response.evacuation_zones),
            initiated_at=datetime.utcnow(),
        )
        try:
            await self.notifier.pa_announcement(
                zone=trigger.zone,
                message=f"EMERGENCY EVACUATION. All personnel in {' and '.join(response.evacuation_zones)} must evacuate immediately to assembly point Alpha. This is not a drill. Repeat: EVACUATE IMMEDIATELY."
            )
            action.status = ResponseStatus.COMPLETED
            action.result = f"PA evacuation broadcast to {len(response.evacuation_zones)} zones"
        except Exception as e:
            action.status = ResponseStatus.FAILED
            action.error = str(e)
        finally:
            action.completed_at = datetime.utcnow()
            response.actions.append(action)
 
    async def _track_notifications(self, trigger: EmergencyTrigger, response: EmergencyResponse):
        """Track 2: Multi-channel alert notifications."""
        contacts = self.PLANT_CONFIG["emergency_contacts"]
 
        message_body = (
            f"EMERGENCY ALERT — SafetyIQ\n"
            f"Plant: {self.PLANT_CONFIG['name']}\n"
            f"Zone: {trigger.zone}\n"
            f"Type: {trigger.emergency_type.value}\n"
            f"Time: {trigger.timestamp.strftime('%H:%M:%S')}\n"
            f"Workers in zone: {trigger.workers_in_zone}\n"
            f"Triggered by: {trigger.triggering_event[:200]}\n"
            f"Response ID: {response.response_id}"
        )
 
        tasks = [
            self.notifier.sms_blast(
                contacts["plant_safety_officer"] + contacts["hospital"],
                message_body
            ),
            self.notifier.email_alert(
                ["safety@plant.com", "gm@plant.com", "dgfasli@gov.in"],
                f"[EMERGENCY] {trigger.emergency_type.value} — {trigger.zone}",
                message_body
            ),
            self.notifier.emergency_services_call(
                "Fire Station",
                f"Emergency at {self.PLANT_CONFIG['name']}, {trigger.zone}. {trigger.emergency_type.value}. {trigger.workers_in_zone} workers may be affected."
            ),
        ]
 
        results = await asyncio.gather(*tasks, return_exceptions=True)
 
        action = ResponseAction(
            action_id="ACT-NOTIFY-001",
            action_type="NOTIFICATION",
            description="Multi-channel emergency notifications",
            status=ResponseStatus.COMPLETED if all(r is True for r in results) else ResponseStatus.IN_PROGRESS,
            target="Safety Officer, Hospital, Fire Station, DGFASLI",
            initiated_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            result=f"Notifications sent: {sum(1 for r in results if r is True)}/{len(results)} channels successful",
        )
        response.actions.append(action)
 
    async def _track_evidence(self, trigger: EmergencyTrigger, response: EmergencyResponse):
        """Track 3: Preserve sensor evidence and CCTV footage."""
        snapshot_id, footage_id, _ = await asyncio.gather(
            self.preserver.snapshot_sensors(trigger),
            self.preserver.lock_cctv_footage(trigger.zone, hours_back=2),
            self.preserver.archive_permits([p.get("permit_id", "?") for p in trigger.active_permits]),
        )
 
        action = ResponseAction(
            action_id="ACT-EVIDENCE-001",
            action_type="EVIDENCE_PRESERVATION",
            description="Lock sensor snapshots, CCTV footage, and permit records",
            status=ResponseStatus.COMPLETED,
            target="Sensor DB, CCTV System, PTW Archive",
            initiated_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            result=f"Snapshot: {snapshot_id} | CCTV: {footage_id}",
        )
        response.actions.append(action)
 
    async def _track_scada_lockdown(self, trigger: EmergencyTrigger, response: EmergencyResponse):
        """Track 4: Lock out active permits and initiate process shutdown."""
        permit_ids = [p.get("permit_id", "?") for p in trigger.active_permits]
 
        await self.notifier.scada_lockdown(trigger.zone, permit_ids)
 
        action = ResponseAction(
            action_id="ACT-SCADA-001",
            action_type="SCADA_LOCKDOWN",
            description=f"Suspend {len(permit_ids)} active permits and initiate emergency shutdown",
            status=ResponseStatus.COMPLETED,
            target="SCADA System",
            initiated_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            result=f"Permits suspended: {', '.join(permit_ids) or 'None'}. Zone locked.",
        )
        response.actions.append(action)
 
    async def _generate_incident_report(
        self, trigger: EmergencyTrigger, response: EmergencyResponse
    ) -> IncidentReport:
        """Generate preliminary DGFASLI Form 18 compliant incident report."""
 
        prompt = f"""Generate a preliminary DGFASLI Form 18 incident notification report based on:
 
EMERGENCY TYPE: {trigger.emergency_type.value}
ZONE: {trigger.zone}
PLANT: {self.PLANT_CONFIG['name']}
TIME: {trigger.timestamp.isoformat()}
WORKERS IN ZONE: {trigger.workers_in_zone}
TRIGGERING EVENT: {trigger.triggering_event}
 
SENSOR READINGS AT TRIGGER:
{json.dumps(trigger.sensor_readings, indent=2)}
 
ACTIVE PERMITS:
{json.dumps(trigger.active_permits, indent=2)}
 
RESPONSE ACTIONS TAKEN:
{json.dumps([{"type": a.action_type, "desc": a.description, "result": a.result} for a in response.actions], indent=2)}
 
Respond with valid JSON only matching:
{{
  "nature_of_incident": "...",
  "immediate_cause": "...",
  "root_cause_preliminary": "...",
  "hazardous_substances": ["H2S", "CO"],
  "regulatory_notification_required": ["DGFASLI within 12 hours", "Factory Inspector within 24 hours"],
  "immediate_actions_taken": ["action1", "action2"]
}}"""
 
        try:
            resp = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                system="You generate regulatory-compliant incident reports for Indian industrial facilities. Respond in valid JSON only.",
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
 
            return IncidentReport(
                report_id=f"RPT-{response.response_id}",
                plant_name=self.PLANT_CONFIG["name"],
                plant_address=self.PLANT_CONFIG["address"],
                date_of_incident=trigger.timestamp.strftime("%Y-%m-%d"),
                time_of_incident=trigger.timestamp.strftime("%H:%M:%S"),
                nature_of_incident=data.get("nature_of_incident", trigger.triggering_event[:200]),
                location_in_plant=trigger.zone,
                persons_affected=trigger.workers_in_zone,
                immediate_cause=data.get("immediate_cause", "Under investigation"),
                root_cause_preliminary=data.get("root_cause_preliminary", "Pending investigation"),
                immediate_actions_taken=data.get("immediate_actions_taken", []),
                hazardous_substances=data.get("hazardous_substances", []),
                regulatory_notification_required=data.get("regulatory_notification_required", []),
            )
        except Exception as e:
            logger.error(f"Incident report generation error: {e}")
            return IncidentReport(
                report_id=f"RPT-{response.response_id}",
                plant_name=self.PLANT_CONFIG["name"],
                date_of_incident=trigger.timestamp.strftime("%Y-%m-%d"),
                time_of_incident=trigger.timestamp.strftime("%H:%M:%S"),
                location_in_plant=trigger.zone,
                nature_of_incident=trigger.triggering_event,
                requires_human_review=True,
            )
 
    async def _generate_situation_report(
        self, trigger: EmergencyTrigger, response: EmergencyResponse
    ) -> str:
        """Generate a concise situation report for the incident commander."""
        prompt = f"""Generate a 5-line incident commander situation report (SITREP) for:
 
Emergency: {trigger.emergency_type.value} at {trigger.zone}
Trigger: {trigger.triggering_event}
Workers in zone: {trigger.workers_in_zone}
Actions completed: {len([a for a in response.actions if a.status == ResponseStatus.COMPLETED])}/{len(response.actions)}
Evacuation zones: {', '.join(response.evacuation_zones)}
 
Format: SITREP lines, one per line. Start each with the category: SITUATION / FORCES / ACTIONS / NEEDS / NEXT"""
 
        try:
            resp = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip()
        except Exception:
            return f"SITREP: Emergency {trigger.emergency_type.value} active in {trigger.zone}. Evacuation in progress. {trigger.workers_in_zone} workers potentially affected."
 
    def to_api_response(self, response: EmergencyResponse) -> dict[str, Any]:
        """Serialize for REST API."""
        return {
            "response_id": response.response_id,
            "trigger_zone": response.trigger.zone,
            "emergency_type": response.trigger.emergency_type.value,
            "elapsed_seconds": response.total_elapsed_seconds,
            "evacuation_zones": response.evacuation_zones,
            "actions_completed": sum(1 for a in response.actions if a.status == ResponseStatus.COMPLETED),
            "total_actions": len(response.actions),
            "actions": [
                {
                    "id": a.action_id, "type": a.action_type, "description": a.description,
                    "status": a.status.value, "result": a.result,
                }
                for a in response.actions
            ],
            "incident_report_id": response.incident_report.report_id if response.incident_report else None,
            "situation_report": response.ai_situation_report,
        }
 
 
# ─── Demo ─────────────────────────────────────────────────────────────────────
 
async def demo():
    trigger = EmergencyTrigger(
        trigger_id="TRIG-20250115-001",
        emergency_type=EmergencyType.GAS_LEAK,
        zone="Coke Oven Battery A",
        severity="CRITICAL",
        triggering_event="H2S exceeded critical threshold (21.3 ppm, critical: 20 ppm) with rising trend. CO at 358 ppm. 12 workers in zone. Confined space entry permit PTW-2847 active.",
        sensor_readings=[
            {"id": "S001", "type": "H2S", "value": 21.3, "unit": "ppm", "trend": "rising"},
            {"id": "S002", "type": "CO", "value": 358, "unit": "ppm", "trend": "rising"},
        ],
        active_permits=[
            {"permit_id": "PTW-2847", "type": "CONFINED_SPACE", "workers": 4},
            {"permit_id": "PTW-2851", "type": "HOT_WORK", "workers": 2},
        ],
        workers_in_zone=12,
        triggered_by="AUTO_AI",
    )
 
    orchestrator = EmergencyOrchestrator()
    response = await orchestrator.activate(trigger)
 
    print(f"\n{'='*60}")
    print(f"Emergency Response Complete in {response.total_elapsed_seconds:.1f} seconds")
    print(f"{'='*60}")
    for action in response.actions:
        print(f"  [{action.status.value:10}] {action.action_type}: {action.result}")
    print(f"\nSITREP:\n{response.ai_situation_report}")
    if response.incident_report:
        print(f"\nForm 18 Draft: {response.incident_report.report_id}")
        print(f"  Nature: {response.incident_report.nature_of_incident[:100]}")
 
 
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(demo())