"""Alert management and rules API endpoints (Module 8).

Implements:
- GET /api/v1/alerts: List active and historical alerts with filtering & pagination.
- POST /api/v1/alerts/{id}/acknowledge: Supervisor acknowledgement with documented safety actions.
- POST /api/v1/alerts/{id}/resolve: Supervisor resolution of alert episodes.
- GET /api/v1/alert-rules: List configured alert rules.
- POST /api/v1/alert-rules: Create and configure new alert rules.
"""

from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.user_auth import require_authenticated_user, require_supervisor_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.alert import (
    count_alert_rules,
    count_alerts,
    create_alert_rule,
    list_alert_rules,
    list_alerts,
)
from app.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertAcknowledgeResponse,
    AlertAcknowledgeResponseData,
    AlertAcknowledgementData,
    AlertData,
    AlertListResponse,
    AlertPagination,
    AlertResolveRequest,
    AlertResolveResponse,
    AlertResolveResponseData,
    AlertRuleCreateRequest,
    AlertRuleData,
    AlertRuleListResponse,
    AlertRuleResponse,
    AlertSeverity,
    AlertStatus,
)
from app.schemas.common import ErrorResponse
from app.services.alert_engine import (
    acknowledge_alert_service,
    resolve_alert_service,
    validate_rule_parameters,
)

router = APIRouter()


# ==============================================================================
# Alert Query Endpoints
# ==============================================================================

@router.get(
    "/alerts",
    response_model=AlertListResponse,
    status_code=status.HTTP_200_OK,
    summary="List alerts",
    description="Lists alerts filtered by device, worksite, status, or severity with pagination.",
    responses={
        status.HTTP_200_OK: {"model": AlertListResponse, "description": "Paginated list of alerts."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Authentication required."},
    },
)
def get_alerts_endpoint(
    device_id: uuid.UUID | None = Query(default=None, description="Filter by device ID."),
    worksite_id: uuid.UUID | None = Query(default=None, description="Filter by worksite ID (via device)."),
    status: AlertStatus | None = Query(default=None, description="Filter by alert status."),
    severity: AlertSeverity | None = Query(default=None, description="Filter by severity classification."),
    start_time: datetime | None = Query(default=None, description="Filter alerts triggered on or after start_time."),
    end_time: datetime | None = Query(default=None, description="Filter alerts triggered on or before end_time."),
    limit: int = Query(default=50, ge=1, le=100, description="Page limit."),
    offset: int = Query(default=0, ge=0, description="Page offset."),
    _user: User = Depends(require_authenticated_user),
    session: Session = Depends(get_db),
) -> AlertListResponse:
    """Retrieve paginated alerts adhering to API contracts."""
    status_val = status.value if status else None
    severity_val = severity.value if severity else None

    total = count_alerts(
        session=session,
        device_id=device_id,
        worksite_id=worksite_id,
        status=status_val,
        severity=severity_val,
        start_time=start_time,
        end_time=end_time,
    )
    alerts = list_alerts(
        session=session,
        device_id=device_id,
        worksite_id=worksite_id,
        status=status_val,
        severity=severity_val,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    alert_items: list[AlertData] = [
        AlertData(
            id=a.id,
            device_id=a.device_id,
            device_code=a.device.device_code if a.device else None,
            reading_id=a.reading_id,
            alert_rule_id=a.alert_rule_id,
            alert_rule_name=a.alert_rule.name if a.alert_rule else None,
            event_type=a.event_type,
            severity=a.severity,
            status=a.status,
            rule_version_snapshot=a.rule_version_snapshot,
            deduplication_key=a.deduplication_key,
            triggered_at=a.triggered_at,
            acknowledged_at=a.acknowledged_at,
            resolved_at=a.resolved_at,
            created_at=a.created_at,
        )
        for a in alerts
    ]

    return AlertListResponse(
        data=alert_items,
        pagination=AlertPagination(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(alerts)) < total,
        ),
    )


# ==============================================================================
# Alert Lifecycle Actions
# ==============================================================================

@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertAcknowledgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge alert",
    description="Acknowledges an active alert and records the documented safety or corrective action.",
    responses={
        status.HTTP_200_OK: {"model": AlertAcknowledgeResponse, "description": "Alert acknowledged successfully."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Supervisor authentication required."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Supervisor privilege required."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Alert ID does not exist."},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Alert is already resolved or expired."},
    },
)
def acknowledge_alert_endpoint(
    alert_id: uuid.UUID,
    payload: AlertAcknowledgeRequest,
    supervisor: User = Depends(require_supervisor_user),
    session: Session = Depends(get_db),
) -> AlertAcknowledgeResponse:
    """Acknowledge an alert and persist documented safety actions."""
    alert, ack = acknowledge_alert_service(
        session=session,
        alert_id=alert_id,
        actor=supervisor,
        action_taken=payload.action_taken,
    )
    session.commit()

    return AlertAcknowledgeResponse(
        data=AlertAcknowledgeResponseData(
            id=alert.id,
            status=alert.status,
            acknowledged_at=alert.acknowledged_at or ack.acknowledged_at,
            acknowledgement=AlertAcknowledgementData(
                id=ack.id,
                actor_id=ack.actor_id,
                action_taken=ack.action_taken,
                acknowledged_at=ack.acknowledged_at,
            ),
        )
    )


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=AlertResolveResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve alert",
    description="Marks an active or acknowledged alert episode as resolved.",
    responses={
        status.HTTP_200_OK: {"model": AlertResolveResponse, "description": "Alert resolved successfully."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Supervisor authentication required."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Supervisor privilege required."},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Alert ID does not exist."},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Alert is already resolved or expired."},
    },
)
def resolve_alert_endpoint(
    alert_id: uuid.UUID,
    payload: AlertResolveRequest | None = None,
    supervisor: User = Depends(require_supervisor_user),
    session: Session = Depends(get_db),
) -> AlertResolveResponse:
    """Mark an alert episode as resolved."""
    notes = payload.resolution_notes if payload else None
    alert = resolve_alert_service(
        session=session,
        alert_id=alert_id,
        actor=supervisor,
        resolution_notes=notes,
    )
    session.commit()

    return AlertResolveResponse(
        data=AlertResolveResponseData(
            id=alert.id,
            status=alert.status,
            resolved_at=alert.resolved_at or alert.created_at,
        )
    )


# ==============================================================================
# Alert Rules Endpoints
# ==============================================================================

@router.get(
    "/alert-rules",
    response_model=AlertRuleListResponse,
    status_code=status.HTTP_200_OK,
    summary="List alert rules",
    description="List configured alert rules with optional filtering and pagination.",
    responses={
        status.HTTP_200_OK: {"model": AlertRuleListResponse, "description": "List of alert rules."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Authentication required."},
    },
)
def get_alert_rules_endpoint(
    worksite_id: uuid.UUID | None = Query(default=None, description="Filter by worksite scope."),
    is_enabled: bool | None = Query(default=None, description="Filter by enabled status."),
    severity: AlertSeverity | None = Query(default=None, description="Filter by severity."),
    limit: int = Query(default=50, ge=1, le=100, description="Page limit."),
    offset: int = Query(default=0, ge=0, description="Page offset."),
    _user: User = Depends(require_authenticated_user),
    session: Session = Depends(get_db),
) -> AlertRuleListResponse:
    """Retrieve configured alert rules."""
    sev_val = severity.value if severity else None
    total = count_alert_rules(session, worksite_id=worksite_id, is_enabled=is_enabled, severity=sev_val)
    rules = list_alert_rules(
        session=session,
        worksite_id=worksite_id,
        is_enabled=is_enabled,
        severity=sev_val,
        limit=limit,
        offset=offset,
    )

    rule_items: list[AlertRuleData] = [
        AlertRuleData(
            id=r.id,
            name=r.name,
            worksite_id=r.worksite_id,
            metric=r.metric,
            operator=r.operator,
            threshold_value=float(r.threshold_value) if r.threshold_value is not None else None,
            threshold_params=r.threshold_params,
            severity=r.severity,
            is_enabled=r.is_enabled,
            rule_version=r.rule_version,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rules
    ]

    return AlertRuleListResponse(
        data=rule_items,
        pagination=AlertPagination(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(rules)) < total,
        ),
    )


@router.post(
    "/alert-rules",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create alert rule",
    description="Creates a new alert rule. Requires supervisor authorization.",
    responses={
        status.HTTP_201_CREATED: {"model": AlertRuleResponse, "description": "Alert rule created successfully."},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Supervisor authentication required."},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Supervisor privilege required."},
        getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422): {"model": ErrorResponse, "description": "Rule validation failure."},
    },
)
def create_alert_rule_endpoint(
    payload: AlertRuleCreateRequest,
    _supervisor: User = Depends(require_supervisor_user),
    session: Session = Depends(get_db),
) -> AlertRuleResponse:
    """Create and configure a new alert rule."""
    validate_rule_parameters(
        metric=payload.metric.value,
        operator=payload.operator.value,
        severity=payload.severity.value,
        threshold_value=payload.threshold_value,
    )

    rule = create_alert_rule(
        session=session,
        name=payload.name,
        metric=payload.metric.value,
        operator=payload.operator.value,
        severity=payload.severity.value,
        worksite_id=payload.worksite_id,
        threshold_value=payload.threshold_value,
        threshold_params=payload.threshold_params,
        is_enabled=payload.is_enabled,
    )
    session.commit()

    return AlertRuleResponse(
        data=AlertRuleData(
            id=rule.id,
            name=rule.name,
            worksite_id=rule.worksite_id,
            metric=rule.metric,
            operator=rule.operator,
            threshold_value=float(rule.threshold_value) if rule.threshold_value is not None else None,
            threshold_params=rule.threshold_params,
            severity=rule.severity,
            is_enabled=rule.is_enabled,
            rule_version=rule.rule_version,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )
    )
