"""
SafetyIQ — Geospatial Safety Module
=====================================
Provides zone-level risk mapping, worker location tracking,
and geospatial hazard zone classification for the plant layout.

Visakhapatnam Steel Complex plant layout is modelled as a grid
of named zones with known adjacency relationships and hazard classifications.

Production:
  - Worker locations via IoT RFID/UWB tags
  - Plant layout from CAD DXF/GeoJSON import
  - Hazard zone classification per OISD 118 Appendix A

Author: SafetyIQ Team
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ─── Zone Definitions ─────────────────────────────────────────────────────────

class HazardClass(str, Enum):
    """OISD 118 Appendix A hazard zone classification."""
    ZONE_0 = "ZONE_0"   # Continuous explosive atmosphere
    ZONE_1 = "ZONE_1"   # Occasional explosive atmosphere
    ZONE_2 = "ZONE_2"   # Rarely explosive atmosphere
    NON_HAZARDOUS = "NON_HAZARDOUS"


@dataclass
class PlantZone:
    zone_id: str
    name: str
    # Grid coordinates (x, y, width, height) in metres from plant origin
    x: float
    y: float
    width: float
    height: float
    hazard_class: HazardClass
    # IDs of adjacent zones (sharing a boundary)
    adjacent_zones: list[str] = field(default_factory=list)
    # Typical worker count during day shift
    typical_workers: int = 0
    # Key equipment in zone
    key_equipment: list[str] = field(default_factory=list)
    # Whether confined space entry is possible in this zone
    has_confined_spaces: bool = False
    # Max allowable simultaneous high-risk permits
    max_concurrent_hrp: int = 2


@dataclass
class WorkerLocation:
    worker_id: str
    name: str
    zone_id: str
    timestamp: datetime
    permit_id: str | None = None


@dataclass
class ZoneRiskSnapshot:
    zone_id: str
    zone_name: str
    risk_score: int                # 0–100
    status: str                    # SAFE | CAUTION | ELEVATED | DANGER | CRITICAL
    active_workers: int
    active_permits: int
    sensor_alerts: list[dict]
    compound_risk_events: int
    hazard_class: HazardClass
    adjacent_zone_alerts: list[str]  # Zones adjacent that are also in alarm
    top_hazard: str
    geospatial: dict[str, float]     # {x, y, width, height} in metres


# ─── Vizag Steel Complex Plant Layout ─────────────────────────────────────────

PLANT_ZONES: dict[str, PlantZone] = {
    "COKA": PlantZone(
        zone_id="COKA", name="Coke Oven Battery A",
        x=0, y=0, width=200, height=100,
        hazard_class=HazardClass.ZONE_1,
        adjacent_zones=["COKB", "BFUR"],
        typical_workers=12,
        key_equipment=["Coke Oven 1–7", "Gas Collector Main", "Gas Detector GD-COKA-001"],
        has_confined_spaces=True,
        max_concurrent_hrp=1,
    ),
    "COKB": PlantZone(
        zone_id="COKB", name="Coke Oven Battery B",
        x=200, y=0, width=200, height=100,
        hazard_class=HazardClass.ZONE_1,
        adjacent_zones=["COKA", "BFUR", "HSTR"],
        typical_workers=10,
        key_equipment=["Coke Oven 8–14", "Gas Detector GD-COKB-001"],
        has_confined_spaces=True,
        max_concurrent_hrp=1,
    ),
    "BFUR": PlantZone(
        zone_id="BFUR", name="Blast Furnace Zone",
        x=0, y=100, width=200, height=120,
        hazard_class=HazardClass.ZONE_1,
        adjacent_zones=["COKA", "COKB", "CONF", "CHEM"],
        typical_workers=18,
        key_equipment=["Blast Furnace #1", "Blast Furnace #2", "Hot Metal Ladles"],
        has_confined_spaces=True,
        max_concurrent_hrp=2,
    ),
    "HSTR": PlantZone(
        zone_id="HSTR", name="Hot Strip Mill",
        x=200, y=100, width=200, height=120,
        hazard_class=HazardClass.ZONE_2,
        adjacent_zones=["COKB", "RAWM"],
        typical_workers=15,
        key_equipment=["Rolling Mill #1", "Cooling Beds", "Coilers 1–3"],
        has_confined_spaces=False,
        max_concurrent_hrp=3,
    ),
    "CONF": PlantZone(
        zone_id="CONF", name="Confined Space B7",
        x=0, y=220, width=100, height=80,
        hazard_class=HazardClass.ZONE_0,
        adjacent_zones=["BFUR", "CHEM"],
        typical_workers=6,
        key_equipment=["Gas Duct B7", "O2 Detector GD-CONF-001"],
        has_confined_spaces=True,
        max_concurrent_hrp=1,
    ),
    "CHEM": PlantZone(
        zone_id="CHEM", name="Chemical Storage",
        x=100, y=220, width=100, height=80,
        hazard_class=HazardClass.ZONE_1,
        adjacent_zones=["CONF", "BFUR", "RAWM"],
        typical_workers=4,
        key_equipment=["Acid Storage Tank", "PRV-004", "PRV-005"],
        has_confined_spaces=False,
        max_concurrent_hrp=1,
    ),
    "RAWM": PlantZone(
        zone_id="RAWM", name="Raw Material Bay",
        x=200, y=220, width=200, height=80,
        hazard_class=HazardClass.NON_HAZARDOUS,
        adjacent_zones=["HSTR", "CHEM"],
        typical_workers=8,
        key_equipment=["Ore Stockpile", "Conveyor Belt C1–C4", "Stacker/Reclaimer"],
        has_confined_spaces=True,
        max_concurrent_hrp=2,
    ),
}


# ─── Geospatial Risk Engine ────────────────────────────────────────────────────

class GeospatialRiskMapper:
    """
    Maps sensor and agent data onto the plant zone grid to produce
    a geospatial risk picture for the dashboard heatmap.
    """

    def get_zone_snapshots(
        self,
        sensor_readings: list[dict[str, Any]],
        compound_events: list[dict[str, Any]],
        permit_data: list[dict[str, Any]],
        worker_locations: list[WorkerLocation] | None = None,
    ) -> list[ZoneRiskSnapshot]:
        """
        Fuse sensor + event + permit data onto zone grid.
        Returns a list of ZoneRiskSnapshot sorted by risk score.
        """
        snapshots: dict[str, dict] = {
            zid: {
                "zone": zone,
                "sensor_alerts": [],
                "sensor_scores": [],
                "compound_events": 0,
                "compound_score": 0,
                "permits": 0,
                "workers": worker_locations and sum(
                    1 for w in worker_locations if w.zone_id == zid
                ) or zone.typical_workers,
                "top_hazard": "Nominal",
            }
            for zid, zone in PLANT_ZONES.items()
        }

        # Map sensor readings to zones
        for reading in sensor_readings:
            zone_name = reading.get("zone", "")
            zid = self._name_to_id(zone_name)
            if zid and zid in snapshots:
                pct = int((reading["value"] / reading["threshold_critical"]) * 100)
                snapshots[zid]["sensor_scores"].append(pct)
                if reading["value"] >= reading["threshold_warning"]:
                    snapshots[zid]["sensor_alerts"].append({
                        "type": reading["sensor_type"],
                        "value": reading["value"],
                        "unit": reading["unit"],
                        "alarm_state": (
                            "CRITICAL" if reading["value"] >= reading["threshold_critical"]
                            else "WARNING"
                        ),
                    })

        # Map compound events
        for event in compound_events:
            event_zone = event.get("zone", "")
            zid = self._name_to_id(event_zone)
            if zid and zid in snapshots:
                level = event.get("risk_level", "LOW")
                score = {"CRITICAL": 40, "HIGH": 25, "MEDIUM": 15, "LOW": 5}.get(level, 5)
                snapshots[zid]["compound_events"] += 1
                snapshots[zid]["compound_score"] = max(snapshots[zid]["compound_score"], score)
                snapshots[zid]["top_hazard"] = event.get("title", snapshots[zid]["top_hazard"])

        # Map permits
        for permit in permit_data:
            pzone = permit.get("zone", "")
            zid = self._name_to_id(pzone)
            if zid and zid in snapshots:
                snapshots[zid]["permits"] += 1

        # Build snapshots
        result = []
        for zid, data in snapshots.items():
            zone = data["zone"]
            sensor_score = max(data["sensor_scores"]) if data["sensor_scores"] else 0
            compound_score = data["compound_score"]
            risk_score = min(100, max(sensor_score, compound_score))

            status = self._score_to_status(risk_score)

            # Adjacent zone alert propagation
            adj_alerts = [
                PLANT_ZONES[adj].name
                for adj in zone.adjacent_zones
                if adj in snapshots
                and (max(snapshots[adj]["sensor_scores"] or [0]) >= 50 or snapshots[adj]["compound_events"] > 0)
            ]

            result.append(ZoneRiskSnapshot(
                zone_id=zid,
                zone_name=zone.name,
                risk_score=risk_score,
                status=status,
                active_workers=data["workers"],
                active_permits=data["permits"],
                sensor_alerts=data["sensor_alerts"],
                compound_risk_events=data["compound_events"],
                hazard_class=zone.hazard_class,
                adjacent_zone_alerts=adj_alerts,
                top_hazard=data["top_hazard"],
                geospatial={"x": zone.x, "y": zone.y, "width": zone.width, "height": zone.height},
            ))

        result.sort(key=lambda z: z.risk_score, reverse=True)
        return result

    def get_evacuation_zones(self, trigger_zone_id: str) -> list[str]:
        """
        Given a zone where an emergency is triggered, return all zones
        that should be evacuated (trigger zone + adjacent).
        """
        if trigger_zone_id not in PLANT_ZONES:
            # Try name lookup
            trigger_zone_id = self._name_to_id(trigger_zone_id) or trigger_zone_id

        zone = PLANT_ZONES.get(trigger_zone_id)
        if not zone:
            return [trigger_zone_id]

        evac = [zone.name]
        for adj_id in zone.adjacent_zones:
            adj = PLANT_ZONES.get(adj_id)
            if adj:
                evac.append(adj.name)
        return evac

    def distance_between_zones(self, zone_id_a: str, zone_id_b: str) -> float:
        """Euclidean distance between zone centres in metres."""
        a = PLANT_ZONES.get(zone_id_a)
        b = PLANT_ZONES.get(zone_id_b)
        if not a or not b:
            return float("inf")
        cx_a, cy_a = a.x + a.width / 2, a.y + a.height / 2
        cx_b, cy_b = b.x + b.width / 2, b.y + b.height / 2
        return math.sqrt((cx_a - cx_b) ** 2 + (cy_a - cy_b) ** 2)

    def is_simops_proximity_risk(self, zone_id_a: str, zone_id_b: str, threshold_m: float = 25.0) -> bool:
        """
        Returns True if two zones are within the SIMOPs proximity threshold
        (OISD 105 Section 7.2: 25 metres).
        """
        return self.distance_between_zones(zone_id_a, zone_id_b) <= threshold_m

    def to_api_response(self, snapshots: list[ZoneRiskSnapshot]) -> list[dict[str, Any]]:
        """Serialise for REST / WebSocket."""
        return [
            {
                "zone_id": s.zone_id,
                "zone_name": s.zone_name,
                "risk_score": s.risk_score,
                "status": s.status,
                "active_workers": s.active_workers,
                "active_permits": s.active_permits,
                "sensor_alerts": s.sensor_alerts,
                "compound_risk_events": s.compound_risk_events,
                "hazard_class": s.hazard_class.value,
                "adjacent_zone_alerts": s.adjacent_zone_alerts,
                "top_hazard": s.top_hazard,
                "geospatial": s.geospatial,
            }
            for s in snapshots
        ]

    # ── Private helpers ───────────────────────────────────────────────────────

    _NAME_MAP: dict[str, str] = {
        zone.name: zid
        for zid, zone in PLANT_ZONES.items()
    }

    def _name_to_id(self, name: str) -> str | None:
        return self._NAME_MAP.get(name)

    @staticmethod
    def _score_to_status(score: int) -> str:
        if score >= 91: return "CRITICAL"
        if score >= 76: return "DANGER"
        if score >= 56: return "ELEVATED"
        if score >= 31: return "CAUTION"
        return "SAFE"


# Module-level singleton
geo_mapper = GeospatialRiskMapper()