"""
SafetyIQ — Notification Service
=================================
Multi-channel emergency notifications:
  - PA system (plant-wide announcement)
  - SMS (via Twilio / AWS SNS)
  - Email (via AWS SES / SendGrid)
  - Emergency services call log

Production: configure provider credentials in .env.
Demo: all channels are logged stubs.

Author: SafetyIQ Team
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    channel: str
    success: bool
    recipients: list[str]
    message_preview: str
    timestamp: datetime
    error: str = ""


class NotificationService:
    """
    Multi-channel notification dispatcher.

    All methods are async and return NotificationResult for audit logging.
    Production: swap stub implementations with real provider SDKs.
    """

    def __init__(self, settings: Any | None = None):
        self.settings = settings

    async def pa_announcement(self, zone: str, message: str) -> NotificationResult:
        """
        Broadcast to plant-wide PA system.
        Production: HTTP POST to PA controller API.
        """
        logger.warning(f"[PA SYSTEM] {zone}: {message[:100]}")
        await asyncio.sleep(0.1)  # Simulate network round-trip
        return NotificationResult(
            channel="PA",
            success=True,
            recipients=[f"{zone} — All personnel"],
            message_preview=message[:100],
            timestamp=datetime.utcnow(),
        )

    async def sms_blast(self, phone_numbers: list[str], message: str) -> NotificationResult:
        """
        Send SMS to list of numbers.
        Production: Twilio / AWS SNS.
        """
        logger.warning(f"[SMS] → {len(phone_numbers)} numbers: {message[:80]}")
        await asyncio.sleep(0.2)
        return NotificationResult(
            channel="SMS",
            success=True,
            recipients=phone_numbers,
            message_preview=message[:80],
            timestamp=datetime.utcnow(),
        )

    async def email_alert(
        self,
        recipients: list[str],
        subject: str,
        body: str,
    ) -> NotificationResult:
        """
        Send email alert.
        Production: AWS SES / SendGrid.
        """
        logger.warning(f"[EMAIL] To {recipients}: {subject}")
        await asyncio.sleep(0.15)
        return NotificationResult(
            channel="EMAIL",
            success=True,
            recipients=recipients,
            message_preview=f"{subject} — {body[:60]}",
            timestamp=datetime.utcnow(),
        )

    async def emergency_services_call(self, service: str, message: str) -> NotificationResult:
        """
        Log emergency services notification.
        Production: integrate with plant's emergency call system.
        """
        logger.critical(f"[EMERGENCY SERVICES] → {service}: {message[:100]}")
        await asyncio.sleep(0.3)
        return NotificationResult(
            channel=f"EMERGENCY:{service}",
            success=True,
            recipients=[service],
            message_preview=message[:100],
            timestamp=datetime.utcnow(),
        )

    async def scada_lockdown(self, zone: str, permit_ids: list[str]) -> NotificationResult:
        """
        Signal SCADA to suspend permits and initiate process shutdown in zone.
        Production: OPC-UA write / SCADA REST API.
        """
        logger.critical(f"[SCADA] Lockdown zone={zone} permits={permit_ids}")
        await asyncio.sleep(0.2)
        return NotificationResult(
            channel="SCADA",
            success=True,
            recipients=[f"SCADA:{zone}"],
            message_preview=f"Lockdown: {', '.join(permit_ids) or 'None'}",
            timestamp=datetime.utcnow(),
        )

    async def notify_all(
        self,
        zone: str,
        emergency_type: str,
        message: str,
        contacts: dict[str, list[str]],
        permit_ids: list[str],
    ) -> list[NotificationResult]:
        """
        Fire all notification channels in parallel.
        Returns list of results for audit log.
        """
        tasks = [
            self.pa_announcement(zone, f"EMERGENCY EVACUATION. {message}. Report to Assembly Point Alpha."),
            self.sms_blast(
                contacts.get("plant_safety_officer", []) + contacts.get("hospital", []),
                f"EMERGENCY: {emergency_type} in {zone}. {message[:150]}",
            ),
            self.email_alert(
                contacts.get("email", ["safety@plant.com"]),
                f"[EMERGENCY] {emergency_type} — {zone}",
                message,
            ),
            self.emergency_services_call("Fire Station", f"{emergency_type} at {zone}. {message[:100]}"),
            self.scada_lockdown(zone, permit_ids),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            r if isinstance(r, NotificationResult)
            else NotificationResult(
                channel="UNKNOWN", success=False, recipients=[],
                message_preview="", timestamp=datetime.utcnow(),
                error=str(r),
            )
            for r in results
        ]


# Module-level singleton
notification_service = NotificationService()