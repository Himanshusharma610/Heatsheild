"""Repositories package for HeatShield Bharat."""

from app.repositories.alert import (
    acknowledge_alert,
    create_alert,
    create_alert_rule,
    get_active_alert_by_dedup_key,
    get_alert_by_id,
    get_alert_rule_by_id,
    list_active_alert_rules,
    list_alerts,
    resolve_alert,
)
from app.repositories.device import (
    deactivate_device,
    get_device_by_code,
    get_device_by_id,
    list_devices_by_worksite,
    register_device,
    update_device_heartbeat,
)
from app.repositories.reading import (
    create_reading,
    get_latest_valid_reading,
    get_reading_by_device_and_event,
    get_reading_by_id,
    get_reading_history,
)
from app.repositories.worksite import (
    create_worksite,
    deactivate_worksite,
    get_worksite_by_id,
    get_worksite_by_name,
    list_active_worksites,
)

__all__ = [
    "acknowledge_alert",
    "create_alert",
    "create_alert_rule",
    "create_reading",
    "create_worksite",
    "deactivate_device",
    "deactivate_worksite",
    "get_active_alert_by_dedup_key",
    "get_alert_by_id",
    "get_alert_rule_by_id",
    "get_device_by_code",
    "get_device_by_id",
    "get_latest_valid_reading",
    "get_reading_by_device_and_event",
    "get_reading_by_id",
    "get_reading_history",
    "get_worksite_by_id",
    "get_worksite_by_name",
    "list_active_alert_rules",
    "list_active_worksites",
    "list_alerts",
    "list_devices_by_worksite",
    "register_device",
    "resolve_alert",
    "update_device_heartbeat",
]
