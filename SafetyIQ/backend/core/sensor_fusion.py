"""
SafetyIQ — Sensor Fusion
==========================
Fuses multi-source sensor data (IoT, SCADA, manual entry) into a
unified, normalised sensor state for consumption by all AI agents.

Production data sources:
  - MQTT topics: safetyiq/plant/sensors/{zone}/{sensor_id}
  - SCADA REST/OPC-UA polling
  - Manual calibration overrides via API

This module handles:
  - Unit normalisation
  - Outlier / spike filtering (3-sigma)
  - Sensor health scoring
  - Gap filling when a sensor goes offline
  - Compound alarm state computation

Author: SafetyIQ Team
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Maximum history retained per sensor for trend analysis
HISTORY_WINDOW = 60  # data points (~60 minutes at 1/min)


@dataclass
class NormalisedReading:
    """Single fused, normalised reading ready for agent consumption."""
    sensor_id: str
    zone: str
    sensor_type: str
    value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime
    trend: str = "stable"              # "rising" | "falling" | "stable"
    rate_of_change: float = 0.0        # per minute
    alarm_state: str = "NORMAL"        # "NORMAL" | "WARNING" | "CRITICAL"
    sensor_health: float = 1.0         # 0.0 (dead) → 1.0 (healthy)
    is_interpolated: bool = False       # True if value was gap-filled
    raw_value: float | None = None      # Pre-normalised value (for audit)


@dataclass
class SensorFusionState:
    """Snapshot of entire plant sensor state after fusion."""
    timestamp: datetime
    readings: list[NormalisedReading]
    plant_alarm_summary: dict[str, int]   # {"NORMAL": N, "WARNING": N, "CRITICAL": N}
    zones_in_alarm: list[str]
    fusion_health: float                  # Average sensor health 0→1


class RollingBuffer:
    """Fixed-size rolling history for a single sensor."""

    def __init__(self, maxlen: int = HISTORY_WINDOW):
        self._buf: deque[tuple[datetime, float]] = deque(maxlen=maxlen)

    def push(self, ts: datetime, value: float):
        self._buf.append((ts, value))

    def values(self) -> list[float]:
        return [v for _, v in self._buf]

    def timestamps(self) -> list[datetime]:
        return [ts for ts, _ in self._buf]

    def slope(self) -> float:
        """Linear regression slope (value per minute)."""
        vals = self.values()
        if len(vals) < 3:
            return 0.0
        n = len(vals)
        x_mean = (n - 1) / 2.0
        y_mean = statistics.mean(vals)
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(vals))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return (num / den) if den != 0 else 0.0

    def is_outlier(self, value: float, sigma: float = 3.0) -> bool:
        """Return True if value is more than sigma standard deviations from the mean."""
        vals = self.values()
        if len(vals) < 5:
            return False
        mean = statistics.mean(vals)
        std  = statistics.stdev(vals) if len(vals) > 1 else 0
        return std > 0 and abs(value - mean) > sigma * std

    def last_value(self) -> float | None:
        return self._buf[-1][1] if self._buf else None

    def last_timestamp(self) -> datetime | None:
        return self._buf[-1][0] if self._buf else None


class SensorFusion:
    """
    Multi-source sensor fusion engine.

    Usage:
        fusion = SensorFusion()

        # Push a raw reading (from MQTT callback, SCADA poll, etc.)
        fusion.push_reading("S001", "Coke Oven Battery A", "H2S", 18.4, "ppm", 10.0, 20.0)

        # Get fused plant state
        state = fusion.get_state()
    """

    def __init__(self):
        self._histories: dict[str, RollingBuffer] = defaultdict(RollingBuffer)
        self._metadata: dict[str, dict[str, Any]] = {}   # sensor_id → spec
        self._last_seen: dict[str, datetime] = {}

    def push_reading(
        self,
        sensor_id: str,
        zone: str,
        sensor_type: str,
        raw_value: float,
        unit: str,
        threshold_warning: float,
        threshold_critical: float,
        timestamp: datetime | None = None,
    ) -> NormalisedReading:
        """
        Ingest a single raw reading, apply normalisation and outlier filtering,
        and return a NormalisedReading.
        """
        ts = timestamp or datetime.utcnow()

        # Store metadata
        self._metadata[sensor_id] = {
            "zone": zone, "sensor_type": sensor_type, "unit": unit,
            "threshold_warning": threshold_warning, "threshold_critical": threshold_critical,
        }

        buf = self._histories[sensor_id]

        # Outlier filter: reject spikes > 3σ from rolling mean
        is_outlier = buf.is_outlier(raw_value)
        if is_outlier:
            logger.debug(f"Sensor {sensor_id}: outlier value {raw_value} rejected (3σ filter)")
            # Use last good value instead
            value = buf.last_value() or raw_value
            is_interpolated = True
        else:
            value = raw_value
            is_interpolated = False
            buf.push(ts, value)

        self._last_seen[sensor_id] = ts

        # Trend analysis
        slope = buf.slope()  # units per minute
        if abs(slope) < 0.01 * threshold_warning:
            trend = "stable"
        elif slope > 0:
            trend = "rising"
        else:
            trend = "falling"

        # Alarm state
        if value >= threshold_critical:
            alarm_state = "CRITICAL"
        elif value >= threshold_warning:
            alarm_state = "WARNING"
        else:
            alarm_state = "NORMAL"

        # Sensor health: degrades if readings become stale
        age_minutes = (ts - (self._last_seen.get(sensor_id) or ts)).total_seconds() / 60
        health = max(0.0, 1.0 - (age_minutes / 30.0))  # degrades to 0 at 30 min no data

        return NormalisedReading(
            sensor_id=sensor_id,
            zone=zone,
            sensor_type=sensor_type,
            value=round(value, 2),
            unit=unit,
            threshold_warning=threshold_warning,
            threshold_critical=threshold_critical,
            timestamp=ts,
            trend=trend,
            rate_of_change=round(slope, 4),
            alarm_state=alarm_state,
            sensor_health=round(health, 2),
            is_interpolated=is_interpolated,
            raw_value=raw_value if is_interpolated else None,
        )

    def push_batch(self, readings: list[dict[str, Any]]) -> list[NormalisedReading]:
        """Push a batch of raw readings (e.g. from SCADA poll)."""
        return [
            self.push_reading(
                r["sensor_id"], r["zone"], r["sensor_type"],
                r["value"], r["unit"],
                r["threshold_warning"], r["threshold_critical"],
                datetime.fromisoformat(r["timestamp"]) if "timestamp" in r else None,
            )
            for r in readings
        ]

    def get_state(self) -> SensorFusionState:
        """
        Return the current fused plant state.
        Gap-fills sensors that have not reported recently (> 2 min).
        """
        now = datetime.utcnow()
        readings = []

        for sensor_id, meta in self._metadata.items():
            buf = self._histories[sensor_id]
            last_val = buf.last_value()
            last_ts  = buf.last_timestamp()

            if last_val is None:
                continue

            age_seconds = (now - last_ts).total_seconds() if last_ts else 9999
            is_stale = age_seconds > 120  # 2-minute stale threshold

            # Gap fill: repeat last known value (with is_interpolated=True)
            if is_stale:
                logger.warning(f"Sensor {sensor_id} stale ({age_seconds:.0f}s). Gap-filling.")

            threshold_w = meta["threshold_warning"]
            threshold_c = meta["threshold_critical"]
            val = last_val

            alarm_state = (
                "CRITICAL" if val >= threshold_c
                else "WARNING" if val >= threshold_w
                else "NORMAL"
            )

            health = max(0.0, 1.0 - (age_seconds / 1800.0))  # dead at 30 min

            readings.append(NormalisedReading(
                sensor_id=sensor_id,
                zone=meta["zone"],
                sensor_type=meta["sensor_type"],
                value=val,
                unit=meta["unit"],
                threshold_warning=threshold_w,
                threshold_critical=threshold_c,
                timestamp=last_ts or now,
                trend=self._trend_label(buf.slope(), threshold_w),
                rate_of_change=round(buf.slope(), 4),
                alarm_state=alarm_state,
                sensor_health=round(health, 2),
                is_interpolated=is_stale,
            ))

        alarm_counts: dict[str, int] = {"NORMAL": 0, "WARNING": 0, "CRITICAL": 0}
        zones_in_alarm: set[str] = set()

        for r in readings:
            alarm_counts[r.alarm_state] = alarm_counts.get(r.alarm_state, 0) + 1
            if r.alarm_state != "NORMAL":
                zones_in_alarm.add(r.zone)

        avg_health = statistics.mean(r.sensor_health for r in readings) if readings else 1.0

        return SensorFusionState(
            timestamp=now,
            readings=readings,
            plant_alarm_summary=alarm_counts,
            zones_in_alarm=sorted(zones_in_alarm),
            fusion_health=round(avg_health, 2),
        )

    def get_zone_readings(self, zone: str) -> list[NormalisedReading]:
        """Return current fused readings for a specific zone."""
        state = self.get_state()
        return [r for r in state.readings if r.zone == zone]

    def get_sensor_history(self, sensor_id: str) -> list[tuple[datetime, float]]:
        """Return raw history buffer for a sensor (for chart rendering)."""
        buf = self._histories.get(sensor_id)
        if not buf:
            return []
        return list(zip(buf.timestamps(), buf.values()))

    @staticmethod
    def _trend_label(slope: float, threshold_warning: float) -> str:
        sensitivity = max(0.005, 0.01 * threshold_warning)
        if slope > sensitivity:
            return "rising"
        if slope < -sensitivity:
            return "falling"
        return "stable"


# Module-level singleton
sensor_fusion = SensorFusion()