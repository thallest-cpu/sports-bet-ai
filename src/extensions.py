"""Future integration contracts. No payments, subscriptions or delivery enabled."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Plan:
    code: str
    alerts_enabled: bool = False


@dataclass(frozen=True)
class AlertEvent:
    prediction_id: str
    event_type: str
    idempotency_key: str


class AlertSink(Protocol):
    def enqueue(self, event: AlertEvent) -> None: ...


class DisabledAlerts:
    def enqueue(self, event: AlertEvent) -> None:
        return None
