"""Alert and AlertRule repository operations."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.alert import Alert, AlertAcknowledgement, AlertRule
from app.models.device import Device


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


def list_alert_rules(
    session: Session,
    worksite_id: uuid.UUID | None = None,
    is_enabled: bool | None = None,
    severity: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AlertRule]:
    """Retrieve alert rules with optional filtering and pagination."""
    stmt = select(AlertRule)
    if worksite_id is not None:
        stmt = stmt.where((AlertRule.worksite_id == worksite_id) | (AlertRule.worksite_id.is_(None)))
    if is_enabled is not None:
        stmt = stmt.where(AlertRule.is_enabled == is_enabled)
    if severity is not None:
        stmt = stmt.where(AlertRule.severity == severity)
    stmt = stmt.order_by(AlertRule.name.asc()).limit(limit).offset(offset)
    return list(session.scalars(stmt).all())


def count_alert_rules(
    session: Session,
    worksite_id: uuid.UUID | None = None,
    is_enabled: bool | None = None,
    severity: str | None = None,
) -> int:
    """Count alert rules matching filters."""
    stmt = select(func.count(AlertRule.id))
    if worksite_id is not None:
        stmt = stmt.where((AlertRule.worksite_id == worksite_id) | (AlertRule.worksite_id.is_(None)))
    if is_enabled is not None:
        stmt = stmt.where(AlertRule.is_enabled == is_enabled)
    if severity is not None:
        stmt = stmt.where(AlertRule.severity == severity)
    return session.scalar(stmt) or 0


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
    triggered_at: datetime | None = None,
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
    if triggered_at is not None:
        alert.triggered_at = triggered_at
    session.add(alert)
    session.flush()
    return alert


def get_alert_by_id(session: Session, alert_id: uuid.UUID) -> Alert | None:
    """Retrieve alert by primary key with preloaded relationships."""
    stmt = (
        select(Alert)
        .options(joinedload(Alert.device), joinedload(Alert.alert_rule), joinedload(Alert.acknowledgements))
        .where(Alert.id == alert_id)
    )
    return session.scalars(stmt).first()


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
    worksite_id: uuid.UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Alert]:
    """List alerts with optional filtering and pagination."""
    stmt = (
        select(Alert)
        .options(joinedload(Alert.device), joinedload(Alert.alert_rule))
    )
    if worksite_id is not None:
        stmt = stmt.join(Device, Alert.device_id == Device.id).where(Device.worksite_id == worksite_id)
    if device_id is not None:
        stmt = stmt.where(Alert.device_id == device_id)
    if status is not None:
        stmt = stmt.where(Alert.status == status)
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    if start_time is not None:
        stmt = stmt.where(Alert.triggered_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(Alert.triggered_at <= end_time)
    stmt = stmt.order_by(Alert.triggered_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt).all())


def count_alerts(
    session: Session,
    device_id: uuid.UUID | None = None,
    worksite_id: uuid.UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> int:
    """Count total alerts matching filters for pagination."""
    stmt = select(func.count(Alert.id))
    if worksite_id is not None:
        stmt = stmt.join(Device, Alert.device_id == Device.id).where(Device.worksite_id == worksite_id)
    if device_id is not None:
        stmt = stmt.where(Alert.device_id == device_id)
    if status is not None:
        stmt = stmt.where(Alert.status == status)
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    if start_time is not None:
        stmt = stmt.where(Alert.triggered_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(Alert.triggered_at <= end_time)
    return session.scalar(stmt) or 0


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
