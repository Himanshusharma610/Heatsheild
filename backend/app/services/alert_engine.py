"""Alert rules evaluation and lifecycle management service (Module 8).

Handles:
- Pure, deterministic alert rule evaluation against environmental readings.
- Metric extraction (temperature_c, relative_humidity_pct, and Module 7 heat_index_c).
- Fail-safe missing/stale/invalid data handling (never defaults to 0 or safe).
- State-preserving deduplication per (device, rule) active episode.
- Validated lifecycle state transitions (triggered -> acknowledged -> resolved).
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
import math
from typing import Any
import uuid
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.alert import Alert, AlertAcknowledgement, AlertRule
from app.models.device import Device
from app.models.reading import SensorReading
from app.models.user import User
from app.repositories.alert import (
    acknowledge_alert,
    create_alert,
    get_active_alert_by_dedup_key,
    get_alert_by_id,
    list_active_alert_rules,
    resolve_alert,
)
from app.schemas.alert import AlertSeverity, RuleMetric, RuleOperator

logger = logging.getLogger(__name__)

SUPPORTED_METRICS = {m.value for m in RuleMetric}
SUPPORTED_OPERATORS = {o.value for o in RuleOperator}
SUPPORTED_SEVERITIES = {s.value for s in AlertSeverity}


def compare_metric_value(val: float, operator: str, threshold: float) -> bool:
    """Compare a numerical reading value against a threshold using the given operator."""
    if operator == "gt":
        return val > threshold
    if operator == "gte":
        return val >= threshold
    if operator == "lt":
        return val < threshold
    if operator == "lte":
        return val <= threshold
    if operator == "eq":
        return math.isclose(val, threshold, rel_tol=1e-5, abs_tol=1e-5)
    return False


def validate_rule_parameters(
    metric: str,
    operator: str,
    severity: str,
    threshold_value: float | Decimal | None,
) -> None:
    """Validate rule configuration parameters.

    Raises:
        ValidationException: If any parameter is invalid, unsupported, or non-finite.
    """
    if metric not in SUPPORTED_METRICS:
        raise ValidationException(
            f"Unsupported metric '{metric}'. Supported metrics: {sorted(list(SUPPORTED_METRICS))}."
        )
    if operator not in SUPPORTED_OPERATORS:
        raise ValidationException(
            f"Unsupported operator '{operator}'. Supported operators: {sorted(list(SUPPORTED_OPERATORS))}."
        )
    if severity not in SUPPORTED_SEVERITIES:
        raise ValidationException(
            f"Unsupported severity '{severity}'. Supported severities: {sorted(list(SUPPORTED_SEVERITIES))}."
        )
    if threshold_value is None:
        raise ValidationException("Threshold value is required.")

    t_val = float(threshold_value)
    if math.isnan(t_val) or math.isinf(t_val):
        raise ValidationException("Threshold value must be a finite number.")

    # Physical plausibility validation on rule thresholds
    if metric == "relative_humidity_pct" and (t_val < 0.0 or t_val > 100.0):
        raise ValidationException(f"Relative humidity threshold {t_val}% must be within [0, 100].")
    if metric in ("temperature_c", "heat_index_c", "heat_index") and (t_val < -50.0 or t_val > 100.0):
        raise ValidationException(f"Temperature threshold {t_val}°C is outside plausible bounds [-50, 100].")


def evaluate_rule(
    rule: AlertRule,
    temperature_c: float | Decimal | None,
    relative_humidity_pct: float | Decimal | None,
    quality_status: str | None = "valid",
    is_stale: bool = False,
    heat_index_val: float | None = None,
) -> bool:
    """Pure, deterministic evaluation of an alert rule against measurement values.

    Args:
        rule: Configured AlertRule model instance.
        temperature_c: Measured air temperature in Celsius.
        relative_humidity_pct: Measured relative humidity in percent.
        quality_status: Reading quality classification ('valid', 'suspect', 'invalid', 'missing').
        is_stale: Whether the reading is considered stale.
        heat_index_val: Precomputed Heat Index in Celsius, if already calculated.

    Returns:
        True if the rule condition is breached, False otherwise.
    """
    if not rule.is_enabled:
        return False

    # CRITICAL SAFETY CONSTRAINT:
    # Missing, stale, or invalid readings NEVER trigger normal alerts or evaluate as safe.
    if quality_status != "valid" or is_stale:
        return False

    if rule.threshold_value is None:
        return False

    threshold = float(rule.threshold_value)
    metric = rule.metric

    if metric == "temperature_c":
        if temperature_c is None:
            return False
        return compare_metric_value(float(temperature_c), rule.operator, threshold)

    if metric == "relative_humidity_pct":
        if relative_humidity_pct is None:
            return False
        return compare_metric_value(float(relative_humidity_pct), rule.operator, threshold)

    if metric in ("heat_index_c", "heat_index"):
        if heat_index_val is not None:
            hi_c = heat_index_val
        else:
            from app.services.heat_index import HeatIndexCalculationStatus, calculate_heat_index

            hi_result = calculate_heat_index(
                temperature_c=temperature_c,
                relative_humidity_pct=relative_humidity_pct,
                quality_status=quality_status,
                is_stale=is_stale,
            )
            # If Heat Index is unavailable (out of domain, non-finite, etc.), rule cannot match
            if hi_result.status != HeatIndexCalculationStatus.VALID or hi_result.value_c is None:
                return False
            hi_c = hi_result.value_c

        return compare_metric_value(hi_c, rule.operator, threshold)

    # Unknown metric: fail-safe reject
    return False


def build_deduplication_key(device_id: uuid.UUID, rule_id: uuid.UUID) -> str:
    """Construct deterministic deduplication key for an active alert episode."""
    return f"device:{device_id}:rule:{rule_id}"


def evaluate_reading_alerts(
    session: Session,
    reading: SensorReading,
    device: Device | None = None,
) -> list[Alert]:
    """Evaluate all applicable active alert rules for an incoming sensor reading.

    Args:
        session: Active database session.
        reading: Persisted SensorReading instance.
        device: Device producing the reading (fetched if not supplied).

    Returns:
        List of newly created Alert instances (excluding deduplicated existing episodes).
    """
    if device is None:
        device = session.get(Device, reading.device_id)
        if device is None:
            logger.warning("Cannot evaluate alerts: Device %s not found", reading.device_id)
            return []

    # ADR-010 constraint: Only 'valid' quality readings are evaluated by alert engine
    if reading.quality_status != "valid":
        logger.debug(
            "Skipping alert evaluation for reading %s: quality_status is '%s'",
            reading.id,
            reading.quality_status,
        )
        return []

    # Retrieve enabled rules matching this device's worksite (or global scope)
    rules = list_active_alert_rules(session, worksite_id=device.worksite_id)
    if not rules:
        return []

    # Pre-calculate Heat Index once if any rule evaluates heat index
    heat_index_c: float | None = None
    needs_hi = any(r.metric in ("heat_index_c", "heat_index") for r in rules)
    if needs_hi and reading.temperature_c is not None and reading.relative_humidity_pct is not None:
        from app.services.heat_index import HeatIndexCalculationStatus, calculate_heat_index

        hi_res = calculate_heat_index(
            temperature_c=reading.temperature_c,
            relative_humidity_pct=reading.relative_humidity_pct,
            quality_status=reading.quality_status,
        )
        if hi_res.status == HeatIndexCalculationStatus.VALID and hi_res.value_c is not None:
            heat_index_c = hi_res.value_c

    triggered_alerts: list[Alert] = []

    for rule in rules:
        matched = evaluate_rule(
            rule=rule,
            temperature_c=reading.temperature_c,
            relative_humidity_pct=reading.relative_humidity_pct,
            quality_status=reading.quality_status,
            is_stale=False,
            heat_index_val=heat_index_c,
        )

        if not matched:
            continue

        dedup_key = build_deduplication_key(device.id, rule.id)

        # Check if an active episode already exists for this (device, rule)
        existing_active = get_active_alert_by_dedup_key(session, dedup_key)
        if existing_active is not None:
            logger.info(
                "Deduplicated alert for device %s (%s) under rule %s: ongoing active episode %s",
                device.device_code,
                device.id,
                rule.name,
                existing_active.id,
            )
            continue

        # Create new Alert episode
        triggered_at = reading.measured_at or reading.received_at or datetime.now(timezone.utc)
        new_alert = create_alert(
            session=session,
            device_id=device.id,
            reading_id=reading.id,
            alert_rule_id=rule.id,
            event_type="threshold_exceeded",
            severity=rule.severity,
            status="triggered",
            rule_version_snapshot=rule.rule_version,
            deduplication_key=dedup_key,
            triggered_at=triggered_at,
        )
        triggered_alerts.append(new_alert)
        logger.warning(
            "Triggered new alert %s for device %s rule '%s' (severity: %s)",
            new_alert.id,
            device.device_code,
            rule.name,
            rule.severity,
        )

    return triggered_alerts


def acknowledge_alert_service(
    session: Session,
    alert_id: uuid.UUID,
    actor: User,
    action_taken: str | None = None,
) -> tuple[Alert, AlertAcknowledgement]:
    """Acknowledge an active alert and record the documented safety action.

    Args:
        session: Active database session.
        alert_id: UUID of target alert.
        actor: Authenticated supervisor/admin User instance.
        action_taken: Optional notes describing safety action taken.

    Returns:
        Tuple of (updated Alert, created AlertAcknowledgement).

    Raises:
        NotFoundException: If alert does not exist.
        ConflictException: If alert is already resolved or expired.
    """
    alert = get_alert_by_id(session, alert_id)
    if alert is None:
        raise NotFoundException(f"Alert '{alert_id}' not found.")

    if alert.status in ("resolved", "expired"):
        raise ConflictException(
            f"Cannot acknowledge alert '{alert_id}': alert is already in '{alert.status}' state."
        )

    ack = acknowledge_alert(
        session=session,
        alert_id=alert_id,
        actor_id=actor.id,
        action_taken=action_taken,
    )
    session.flush()
    return alert, ack


def resolve_alert_service(
    session: Session,
    alert_id: uuid.UUID,
    actor: User | None = None,
    resolution_notes: str | None = None,
) -> Alert:
    """Resolve an alert incident.

    Args:
        session: Active database session.
        alert_id: UUID of target alert.
        actor: Optional supervisor User resolving the incident.
        resolution_notes: Optional notes confirming normalized conditions.

    Returns:
        The updated Alert instance.

    Raises:
        NotFoundException: If alert does not exist.
        ConflictException: If alert is already resolved or expired.
    """
    alert = get_alert_by_id(session, alert_id)
    if alert is None:
        raise NotFoundException(f"Alert '{alert_id}' not found.")

    if alert.status == "resolved":
        raise ConflictException(f"Alert '{alert_id}' is already resolved.")

    if alert.status == "expired":
        raise ConflictException(f"Cannot resolve expired alert '{alert_id}'.")

    resolved = resolve_alert(session, alert_id)
    session.flush()
    logger.info("Alert %s marked as resolved by actor %s", alert_id, actor.id if actor else "system")
    return resolved or alert
