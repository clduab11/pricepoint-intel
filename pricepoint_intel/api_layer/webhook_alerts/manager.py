"""Webhook alert manager implementation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx


@dataclass
class AlertRule:
    """Alert rule definition."""

    rule_id: str
    name: str
    product: str
    condition_type: str  # "price_drop", "price_increase", "threshold"
    condition_value: float
    webhook_url: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "product": self.product,
            "condition_type": self.condition_type,
            "condition_value": self.condition_value,
            "webhook_url": self.webhook_url,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Alert:
    """Triggered alert."""

    alert_id: str
    rule_id: str
    product: str
    message: str
    data: dict[str, Any]
    triggered_at: datetime = field(default_factory=datetime.now)
    delivered: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "product": self.product,
            "message": self.message,
            "data": self.data,
            "triggered_at": self.triggered_at.isoformat(),
            "delivered": self.delivered,
        }


class WebhookAlertManager:
    """Webhook alert manager for real-time notifications.

    Manages alert rules and sends webhook notifications
    when conditions are met.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        """Initialize the webhook alert manager.

        Args:
            timeout: Webhook request timeout in seconds.
        """
        self._rules: dict[str, AlertRule] = {}
        self._alerts: list[Alert] = []
        self._timeout = timeout
        self._next_rule_id = 1
        self._next_alert_id = 1

    def add_rule(
        self,
        name: str,
        product: str,
        condition_type: str,
        condition_value: float,
        webhook_url: str,
    ) -> AlertRule:
        """Add a new alert rule.

        Args:
            name: Rule name.
            product: Product to monitor.
            condition_type: Type of condition.
            condition_value: Threshold value.
            webhook_url: URL to call when triggered.

        Returns:
            Created AlertRule.
        """
        rule_id = f"RULE-{self._next_rule_id:04d}"
        self._next_rule_id += 1

        rule = AlertRule(
            rule_id=rule_id,
            name=name,
            product=product,
            condition_type=condition_type,
            condition_value=condition_value,
            webhook_url=webhook_url,
        )

        self._rules[rule_id] = rule
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule.

        Args:
            rule_id: Rule identifier.

        Returns:
            True if removed, False if not found.
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """Get a rule by ID.

        Args:
            rule_id: Rule identifier.

        Returns:
            AlertRule if found, None otherwise.
        """
        return self._rules.get(rule_id)

    def list_rules(self) -> list[AlertRule]:
        """List all alert rules.

        Returns:
            List of AlertRule objects.
        """
        return list(self._rules.values())

    def check_conditions(
        self,
        product: str,
        current_price: float,
        previous_price: float | None = None,
    ) -> list[Alert]:
        """Check if any rules are triggered.

        Args:
            product: Product being checked.
            current_price: Current price.
            previous_price: Previous price (optional).

        Returns:
            List of triggered alerts.
        """
        triggered = []

        for rule in self._rules.values():
            if not rule.active:
                continue

            if rule.product.lower() not in product.lower():
                continue

            should_trigger = False
            message = ""

            if rule.condition_type == "threshold" and current_price <= rule.condition_value:
                should_trigger = True
                message = f"Price dropped to ${current_price:.2f} (threshold: ${rule.condition_value:.2f})"

            elif (
                rule.condition_type == "price_drop"
                and previous_price
                and (previous_price - current_price) / previous_price * 100 >= rule.condition_value
            ):
                should_trigger = True
                drop_pct = (previous_price - current_price) / previous_price * 100
                message = f"Price dropped {drop_pct:.1f}% (threshold: {rule.condition_value}%)"

            elif (
                rule.condition_type == "price_increase"
                and previous_price
                and (current_price - previous_price) / previous_price * 100 >= rule.condition_value
            ):
                should_trigger = True
                increase_pct = (current_price - previous_price) / previous_price * 100
                message = f"Price increased {increase_pct:.1f}% (threshold: {rule.condition_value}%)"

            if should_trigger:
                alert_id = f"ALERT-{self._next_alert_id:06d}"
                self._next_alert_id += 1

                alert = Alert(
                    alert_id=alert_id,
                    rule_id=rule.rule_id,
                    product=product,
                    message=message,
                    data={
                        "current_price": current_price,
                        "previous_price": previous_price,
                        "rule_name": rule.name,
                    },
                )

                self._alerts.append(alert)
                triggered.append(alert)

        return triggered

    async def send_webhook(self, alert: Alert, webhook_url: str) -> bool:
        """Send a webhook notification.

        Args:
            alert: Alert to send.
            webhook_url: Webhook URL.

        Returns:
            True if successful, False otherwise.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(webhook_url, json=alert.to_dict())
                alert.delivered = response.is_success
                return alert.delivered
            except Exception:
                return False

    def get_alerts(self, limit: int = 100) -> list[Alert]:
        """Get recent alerts.

        Args:
            limit: Maximum number of alerts to return.

        Returns:
            List of Alert objects.
        """
        return self._alerts[-limit:]
