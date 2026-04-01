from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Any

import httpx
import structlog

from backend.app.config import settings

logger = structlog.get_logger(__name__)


class Notifier:
    async def notify(self, alert_payload: dict[str, Any]) -> tuple[bool, bool]:
        slack_sent = await self._send_slack(alert_payload)
        email_sent = await asyncio.to_thread(self._send_email, alert_payload)
        return slack_sent, email_sent

    async def _send_slack(self, alert_payload: dict[str, Any]) -> bool:
        if not settings.slack_webhook_url:
            return False
        message = (
            f"Price alert for {alert_payload['asin']} in {alert_payload['location_code']}: "
            f"{alert_payload['competitor_seller_name']} is at INR {alert_payload['competitor_price']:.2f}, "
            f"{alert_payload['delta_percent']:.2%} below {alert_payload['own_seller_name']}."
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(settings.slack_webhook_url, json={"text": message})
                response.raise_for_status()
            return True
        except Exception:
            logger.exception("slack_notification_failed", asin=alert_payload["asin"])
            return False

    def _send_email(self, alert_payload: dict[str, Any]) -> bool:
        if not all([settings.smtp_host, settings.alert_email_from, settings.alert_email_to]):
            return False
        try:
            message = EmailMessage()
            message["Subject"] = f"Amazon price alert: {alert_payload['asin']}"
            message["From"] = settings.alert_email_from
            message["To"] = settings.alert_email_to
            message.set_content(alert_payload["message"])
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.starttls()
                if settings.smtp_username and settings.smtp_password:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
            return True
        except Exception:
            logger.exception("email_notification_failed", asin=alert_payload["asin"])
            return False


notifier = Notifier()
