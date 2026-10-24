"""Alert and AlertRule repository operations."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertAcknowledgement, AlertRule


def create_alert_rule(
    session: Session,
    name: str,
    metric: str,
    operator: str,
    severity: str,
    worksite_id: uuid.UUID | None = None,
    threshold_value: Decimal | float | None = None,
    threshold_params: dict[str, Any] | None = None,
    is_enabled: bool = True,
) -> AlertRule:
    """Create a new alert rule."""
    thresh_decimal = Decimal(str(threshold_value)) if threshold_value is not None else None
    rule = AlertRule(
        name=name,
        metric=metric,
        operator=operator,
        severity=severity,
        worksite_id=worksite_id,
        threshold_value=thresh_decimal,
        threshold_params=threshold_params,
        is_enabled=is_enabled,
        rule_version=1,
    )
    session.add(rule)
    session.flush()
    return rule


def get_alert_rule_by_id(session: Session, rule_id: uuid.UUID) -> AlertRule | None:
    """Retrieve alert rule by primary key."""
    return session.get(AlertRule, rule_id)


def list_active_alert_rules(
    session: Session,
    worksite_id: uuid.UUID | None = None,
) -> list[AlertRule]:
    """Retrieve enabled alert rules matching the specified worksite or global scope."""
    stmt = select(AlertRule).where(AlertRule.is_enabled.is_(True))
    if worksite_id is not None:
        # Match site-specific rules OR global rules (worksite_id is None)
        stmt = stmt.where((AlertRule.worksite_id == worksite_id) | (AlertRule.worksite_id.is_(None)))
    stmt = stmt.order_by(AlertRule.name.asc())
    return list(session.scalars(stmt).all())


def create_alert(
    session: Session,
    device_id: uuid.UUID,
    event_type: str,
    severity: str,
    status: str = "triggered",
    reading_id: uuid.UUID | None = None,
    alert_rule_id: uuid.UUID | None = None,
    rule_version_snapshot: int | None = None,
    deduplication_key: str | None = None,
) -> Alert:
    """Create a new alert event."""
    alert = Alert(
        device_id=device_id,
        event_type=event_type,
        severity=severity,
        status=status,
        reading_id=reading_id,
        alert_rule_id=alert_rule_id,
        rule_version_snapshot=rule_version_snapshot,
        deduplication_key=deduplication_key,
    )
    session.add(alert)
    session.flush()
    return alert


def get_alert_by_id(session: Session, alert_id: uuid.UUID) -> Alert | None:
    """Retrieve alert by primary key."""
    return session.get(Alert, alert_id)


def get_active_alert_by_dedup_key(session: Session, deduplication_key: str) -> Alert | None:
    """Lookup active non-resolved alert by deduplication key."""
    stmt = (
        select(Alert)
        .where(
            Alert.deduplication_key == deduplication_key,
            Alert.status.in_(["triggered", "acknowledged"]),
        )
        .order_by(Alert.triggered_at.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def list_alerts(
    session: Session,
    device_id: uuid.UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Alert]:
    """List alerts with optional filtering and pagination."""
    stmt = select(Alert)
    if device_id is not None:
        stmt = stmt.where(Alert.device_id == device_id)
    if status is not None:
        stmt = stmt.where(Alert.status == status)
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    stmt = stmt.order_by(Alert.triggered_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt).all())


def acknowledge_alert(
    session: Session,
    alert_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
    action_taken: str | None = None,
) -> AlertAcknowledgement:
    """Record an acknowledgement action for an alert and update alert status."""
    alert = session.get(Alert, alert_id)
    if not alert:
        raise ValueError(f"Alert with id {alert_id} not found")

    now = datetime.now(timezone.utc)
    if alert.status == "triggered":
        alert.status = "acknowledged"
    if alert.acknowledged_at is None:
        alert.acknowledged_at = now

    ack = AlertAcknowledgement(
        alert_id=alert_id,
        actor_id=actor_id,
        action_taken=action_taken,
        acknowledged_at=now,
    )
    session.add(ack)
    session.flush()
    return ack


def resolve_alert(session: Session, alert_id: uuid.UUID) -> Alert | None:
    """Mark an alert as resolved."""
    alert = session.get(Alert, alert_id)
    if alert:
        alert.status = "resolved"
        alert.resolved_at = datetime.now(timezone.utc)
        session.flush()
    return alert
