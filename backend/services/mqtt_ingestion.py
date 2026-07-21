"""
SafetyIQ — MQTT IoT Sensor Ingestion Service
==============================================
Subscribes to MQTT topics from IoT sensors and feeds readings
into the SensorFusion pipeline.

Topic schema:
  safetyiq/plant/sensors/{zone_id}/{sensor_id}

Payload (JSON):
  {
    "sensor_id": "S001",
    "zone": "Coke Oven Battery A",
    "sensor_type": "H2S",
    "value": 18.4,
    "unit": "ppm",
    "timestamp": "2025-01-15T08:23:11.123Z"
  }

Production:
  Enable via FEATURE_MQTT_INGESTION=true in .env
  Set MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD

Author: SafetyIQ Team
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


class MQTTIngestionService:
    """
    Async MQTT subscriber for IoT sensor telemetry.

    Production: uses aiomqtt (asyncio-native MQTT client).
    Demo: no-op when FEATURE_MQTT_INGESTION=false.
    """

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        username: str = "",
        password: str = "",
        topic_prefix: str = "safetyiq/plant/sensors",
        on_reading: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix
        self.on_reading = on_reading
        self._running = False

    async def start(self):
        """
        Start subscribing to sensor topics.
        Production: replace stub with actual aiomqtt client.
        """
        self._running = True
        logger.info(
            f"MQTT ingestion service starting: "
            f"broker={self.broker_host}:{self.broker_port}, "
            f"topic={self.topic_prefix}/#"
        )

        # Production implementation:
        # async with aiomqtt.Client(
        #     hostname=self.broker_host,
        #     port=self.broker_port,
        #     username=self.username or None,
        #     password=self.password or None,
        # ) as client:
        #     await client.subscribe(f"{self.topic_prefix}/#")
        #     async for message in client.messages:
        #         await self._handle_message(str(message.topic), message.payload)

        logger.warning(
            "MQTT ingestion is in STUB mode. "
            "Set FEATURE_MQTT_INGESTION=true and configure broker to enable live ingestion."
        )

    async def stop(self):
        self._running = False
        logger.info("MQTT ingestion service stopped.")

    async def _handle_message(self, topic: str, payload: bytes):
        """Parse and route a raw MQTT message."""
        try:
            data = json.loads(payload.decode("utf-8"))
            if self.on_reading:
                self.on_reading(data)
            logger.debug(f"MQTT reading: {data.get('sensor_id')} = {data.get('value')}")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"MQTT message parse error on topic {topic}: {e}")
        except Exception as e:
            logger.error(f"MQTT message handling error: {e}")

    @property
    def is_running(self) -> bool:
        return self._running


# Convenience factory
def create_mqtt_service(settings: Any, on_reading: Callable | None = None) -> MQTTIngestionService:
    return MQTTIngestionService(
        broker_host=settings.mqtt_broker_host,
        broker_port=settings.mqtt_broker_port,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
        topic_prefix=settings.mqtt_sensor_topic_prefix,
        on_reading=on_reading,
    )