"""Automated security tests for Authentication and Role-Based Access Control (Module 12).

Tests the 15 required backend scenarios:
1. Successful login.
2. Invalid credentials (generic 401, no enumeration).
3. Disabled-user login rejection.
4. Passwords are not stored in plaintext (Argon2id hashes).
5. Unauthenticated access to protected endpoints is rejected.
6. Logout/session invalidation acknowledgment.
7. Expired or invalid credentials are rejected.
8. Authentication secrets do not appear in error responses or logs.
9. Viewer cannot acknowledge alerts or manage rules.
10. Supervisor can perform only permitted alert actions.
11. Admin-only operations reject other roles.
12. Users cannot escalate their own privileges.
13. Resource scope querying cannot expose unauthorized data.
14. Device credentials cannot perform human-user actions.
15. Existing device-ingestion authentication remains functional.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.core.security import create_access_token, decode_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.alert import Alert, AlertRule
from app.models.device import Device
from app.models.reading import SensorReading
from app.models.user import User
from app.models.worksite import Worksite
from app.repositories.alert import create_alert_rule
from app.repositories.device import hash_device_token, register_device
from app.repositories.user import create_user


@pytest.fixture
def memory_session() -> Session:
    """In-memory SQLite database session with complete schema."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def app_client(memory_session: Session) -> TestClient:
    """TestClient wired to isolated in-memory database with actual auth dependencies active."""
    settings = Settings(
        APP_NAME="HeatShield Test",
        APP_VERSION="0.1.0-test",
        APP_ENV="testing",
        DEBUG=True,
        API_PREFIX="/api/v1",
        DATABASE_URL=None,
    )
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: memory_session
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def seeded_users_and_assets(memory_session: Session) -> dict:
    """Seed test database with users, worksite, device, and alerts."""
    worksite = Worksite(
        id=uuid.uuid4(),
        name="Nhava Sheva Port Container Yard",
        location_description="Navi Mumbai",
        is_active=True,
    )
    memory_session.add(worksite)
    memory_session.flush()

    device = Device(
        id=uuid.uuid4(),
        device_code="HS-NS01-D001",
        worksite_id=worksite.id,
        display_name="Gate 3 Sensor Node",
        status="online",
        api_key_hash=hash_device_token("device-preshared-secret-key-1234"),
        is_active=True,
    )
    memory_session.add(device)

    # Admin user
    admin = create_user(
        session=memory_session,
        email="admin@heatshield.gov.in",
        password_hash=hash_password("AdminSecurePassword123!"),
        display_name="National Director Admin",
        role="admin",
        is_active=True,
    )

    # Supervisor user
    supervisor = create_user(
        session=memory_session,
        email="supervisor@heatshield.gov.in",
        password_hash=hash_password("SupervisorSecurePassword123!"),
        display_name="Port Supervisor Rao",
        role="supervisor",
        is_active=True,
    )

    # Viewer user
    viewer = create_user(
        session=memory_session,
        email="viewer@heatshield.gov.in",
        password_hash=hash_password("ViewerSecurePassword123!"),
        display_name="Field Observer Priya",
        role="viewer",
        is_active=True,
    )

    # Deactivated user
    deactivated = create_user(
        session=memory_session,
        email="deactivated@heatshield.gov.in",
        password_hash=hash_password("DeactivatedSecurePassword123!"),
        display_name="Former Officer Dev",
        role="supervisor",
        is_active=False,
    )

    # Alert rule and active alert
    rule = create_alert_rule(
        session=memory_session,
        name="High Heat Index Warning",
        metric="heat_index",
        operator="gte",
        severity="warning",
        threshold_value=Decimal("41.0"),
        is_enabled=True,
    )

    alert = Alert(
        id=uuid.uuid4(),
        device_id=device.id,
        alert_rule_id=rule.id,
        event_type="heat_index",
        severity="warning",
        status="triggered",
        rule_version_snapshot=1,
        deduplication_key=f"{device.id}:{rule.id}:triggered",
        triggered_at=datetime.now(timezone.utc),
    )
    memory_session.add(alert)
    memory_session.commit()

    return {
        "worksite": worksite,
        "device": device,
        "admin": admin,
        "supervisor": supervisor,
        "viewer": viewer,
        "deactivated": deactivated,
        "rule": rule,
        "alert": alert,
    }


def auth_headers_for(user: User) -> dict[str, str]:
    """Helper to generate Authorization Bearer header for a given user."""
    token, _ = create_access_token(user.id, user.email, user.role)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# Scenario 1: Successful login
# ==============================================================================

def test_login_success(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 1: Valid credentials return 200, JWT access token, and user profile."""
    resp = app_client.post(
        "/api/v1/auth/login",
        json={"email": "supervisor@heatshield.gov.in", "password": "SupervisorSecurePassword123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 480 * 60
    assert data["user"]["email"] == "supervisor@heatshield.gov.in"
    assert data["user"]["role"] == "supervisor"
    assert "password_hash" not in data["user"]

    # Verify JWT claims
    claims = decode_access_token(data["access_token"])
    assert claims["sub"] == str(seeded_users_and_assets["supervisor"].id)
    assert claims["email"] == "supervisor@heatshield.gov.in"
    assert claims["role"] == "supervisor"
    assert claims["type"] == "access"


# ==============================================================================
# Scenario 2: Invalid credentials
# ==============================================================================

def test_login_invalid_credentials(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 2: Generic 401 failure prevents username enumeration."""
    # Non-existent user
    resp1 = app_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@heatshield.gov.in", "password": "AnyPassword123!"},
    )
    assert resp1.status_code == 401
    err1 = resp1.json()["error"]["message"]

    # Existing user, wrong password
    resp2 = app_client.post(
        "/api/v1/auth/login",
        json={"email": "supervisor@heatshield.gov.in", "password": "WrongPassword123!"},
    )
    assert resp2.status_code == 401
    err2 = resp2.json()["error"]["message"]

    # Both must return identical generic message
    assert err1 == err2
    assert "Invalid email or password" in err1


# ==============================================================================
# Scenario 3: Disabled-user login rejection
# ==============================================================================

def test_login_disabled_user_rejected(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 3: Deactivated account cannot login or obtain tokens."""
    resp = app_client.post(
        "/api/v1/auth/login",
        json={"email": "deactivated@heatshield.gov.in", "password": "DeactivatedSecurePassword123!"},
    )
    assert resp.status_code == 401
    assert "deactivated" in resp.json()["error"]["message"].lower()

    # Even with an existing forged or prior token, deactivated user is rejected on protected endpoints
    deact_user = seeded_users_and_assets["deactivated"]
    headers = auth_headers_for(deact_user)
    get_resp = app_client.get("/api/v1/auth/me", headers=headers)
    assert get_resp.status_code == 401
    assert "deactivated" in get_resp.json()["error"]["message"].lower()


# ==============================================================================
# Scenario 4: Passwords are not stored in plaintext
# ==============================================================================

def test_passwords_are_argon2id_hashed(memory_session: Session, seeded_users_and_assets: dict):
    """Scenario 4: Passwords in database use Argon2id format and are never stored plaintext."""
    admin = seeded_users_and_assets["admin"]
    assert not admin.password_hash.startswith("Admin")
    assert admin.password_hash.startswith("$argon2id$")
    assert "AdminSecurePassword123!" not in admin.password_hash


# ==============================================================================
# Scenario 5: Unauthenticated access to protected endpoints is rejected
# ==============================================================================

@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/devices"),
        ("get", "/api/v1/readings/latest"),
        ("get", "/api/v1/readings/history"),
        ("get", "/api/v1/alerts"),
        ("get", "/api/v1/alert-rules"),
        ("get", "/api/v1/users"),
        ("get", "/api/v1/auth/me"),
        ("post", "/api/v1/auth/logout"),
    ],
)
def test_unauthenticated_endpoints_return_401(app_client: TestClient, method: str, path: str):
    """Scenario 5: Unauthenticated access to protected endpoints is rejected with 401."""
    fn = getattr(app_client, method)
    resp = fn(path)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# ==============================================================================
# Scenario 6: Logout / session invalidation
# ==============================================================================

def test_logout_session_invalidation(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 6: POST /api/v1/auth/logout acknowledges session termination."""
    supervisor = seeded_users_and_assets["supervisor"]
    headers = auth_headers_for(supervisor)

    resp = app_client.post("/api/v1/auth/logout", headers=headers)
    assert resp.status_code == 200
    assert "Logged out successfully" in resp.json()["message"]


# ==============================================================================
# Scenario 7: Expired or invalid credentials are rejected
# ==============================================================================

def test_expired_or_invalid_tokens_rejected(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 7: Expired JWT or tampered signature is rejected with 401."""
    supervisor = seeded_users_and_assets["supervisor"]

    # 1. Expired token
    expired_token, _ = create_access_token(
        user_id=supervisor.id,
        email=supervisor.email,
        role=supervisor.role,
        expires_delta=timedelta(seconds=-10),
    )
    resp_exp = app_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp_exp.status_code == 401
    assert "expired" in resp_exp.json()["error"]["message"].lower()

    # 2. Tampered token signature
    parts = expired_token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.badsignature"
    resp_tampered = app_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp_tampered.status_code == 401

    # 3. Forged token with different signing key
    forged = jwt.encode(
        {"sub": str(supervisor.id), "email": supervisor.email, "role": "admin", "exp": 9999999999, "iat": 1, "type": "access"},
        "wrong-secret-key-1234-with-at-least-32-bytes-length",
        algorithm="HS256",
    )
    resp_forged = app_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert resp_forged.status_code == 401


# ==============================================================================
# Scenario 8: Authentication secrets do not appear in error responses or logs
# ==============================================================================

def test_secrets_do_not_appear_in_responses(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 8: Neither secret keys nor hashes appear in error bodies or me responses."""
    resp = app_client.post(
        "/api/v1/auth/login",
        json={"email": "supervisor@heatshield.gov.in", "password": "WrongPassword!"},
    )
    text = resp.text
    assert "dev-insecure-secret-key" not in text
    assert "$argon2id$" not in text
    assert "argon2" not in text

    # Profile response check
    admin = seeded_users_and_assets["admin"]
    resp_me = app_client.get("/api/v1/auth/me", headers=auth_headers_for(admin))
    me_text = resp_me.text
    assert "$argon2id$" not in me_text
    assert "password" not in resp_me.json()


# ==============================================================================
# Scenario 9: Viewer cannot acknowledge alerts or manage rules
# ==============================================================================

def test_viewer_cannot_acknowledge_alerts_or_manage_rules(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 9: Viewer role receives 403 Forbidden for state-changing safety operations."""
    viewer = seeded_users_and_assets["viewer"]
    alert = seeded_users_and_assets["alert"]
    headers = auth_headers_for(viewer)

    # 1. Viewer trying to acknowledge alert
    resp_ack = app_client.post(
        f"/api/v1/alerts/{alert.id}/acknowledge",
        json={"action_taken": "Attempted viewer ack"},
        headers=headers,
    )
    assert resp_ack.status_code == 403
    assert resp_ack.json()["error"]["code"] == "FORBIDDEN"

    # 2. Viewer trying to resolve alert
    resp_res = app_client.post(
        f"/api/v1/alerts/{alert.id}/resolve",
        json={"resolution_notes": "Attempted viewer resolve"},
        headers=headers,
    )
    assert resp_res.status_code == 403

    # 3. Viewer trying to create alert rule
    resp_rule = app_client.post(
        "/api/v1/alert-rules",
        json={
            "name": "Unauthorized Rule",
            "metric": "heat_index",
            "operator": "gte",
            "severity": "critical",
            "threshold_value": 45.0,
        },
        headers=headers,
    )
    assert resp_rule.status_code == 403


# ==============================================================================
# Scenario 10: Supervisor can perform only permitted alert actions
# ==============================================================================

def test_supervisor_permitted_alert_actions(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 10: Supervisor can acknowledge/resolve alerts, but cannot manage users."""
    supervisor = seeded_users_and_assets["supervisor"]
    alert = seeded_users_and_assets["alert"]
    headers = auth_headers_for(supervisor)

    # 1. Supervisor acknowledges alert -> Allowed (200)
    resp_ack = app_client.post(
        f"/api/v1/alerts/{alert.id}/acknowledge",
        json={"action_taken": "Provided electrolyte hydration station and ventilated rest shelter."},
        headers=headers,
    )
    assert resp_ack.status_code == 200
    assert resp_ack.json()["data"]["status"] == "acknowledged"

    # 2. Supervisor creates alert rule -> Allowed (201)
    resp_rule = app_client.post(
        "/api/v1/alert-rules",
        json={
            "name": "Supervisor Created Extreme Heat Rule",
            "metric": "temperature_c",
            "operator": "gte",
            "severity": "critical",
            "threshold_value": 44.0,
        },
        headers=headers,
    )
    assert resp_rule.status_code == 201

    # 3. Supervisor attempts to list users -> Forbidden (403)
    resp_users = app_client.get("/api/v1/users", headers=headers)
    assert resp_users.status_code == 403
    assert resp_users.json()["error"]["code"] == "FORBIDDEN"


# ==============================================================================
# Scenario 11: Admin-only operations reject other roles
# ==============================================================================

def test_admin_only_operations(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 11: Admin can manage users; supervisor and viewer are rejected with 403."""
    admin = seeded_users_and_assets["admin"]
    supervisor = seeded_users_and_assets["supervisor"]
    viewer = seeded_users_and_assets["viewer"]

    admin_headers = auth_headers_for(admin)
    super_headers = auth_headers_for(supervisor)
    viewer_headers = auth_headers_for(viewer)

    # 1. List users
    assert app_client.get("/api/v1/users", headers=admin_headers).status_code == 200
    assert app_client.get("/api/v1/users", headers=super_headers).status_code == 403
    assert app_client.get("/api/v1/users", headers=viewer_headers).status_code == 403

    # 2. Provision new user
    new_user_payload = {
        "email": "new.safety.officer@heatshield.gov.in",
        "password": "SecurePassword987!",
        "display_name": "New Safety Officer",
        "role": "supervisor",
    }
    # Viewer rejected
    assert app_client.post("/api/v1/users", json=new_user_payload, headers=viewer_headers).status_code == 403
    # Supervisor rejected
    assert app_client.post("/api/v1/users", json=new_user_payload, headers=super_headers).status_code == 403
    # Admin allowed
    create_resp = app_client.post("/api/v1/users", json=new_user_payload, headers=admin_headers)
    assert create_resp.status_code == 201
    assert create_resp.json()["email"] == "new.safety.officer@heatshield.gov.in"
    assert create_resp.json()["role"] == "supervisor"


# ==============================================================================
# Scenario 12: Users cannot escalate their own privileges
# ==============================================================================

def test_privilege_escalation_prevented(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 12: Non-admins cannot edit roles; admin cannot demote sole admin or self-deactivate."""
    admin = seeded_users_and_assets["admin"]
    supervisor = seeded_users_and_assets["supervisor"]

    # 1. Supervisor cannot call PATCH /users/{id}
    resp = app_client.patch(
        f"/api/v1/users/{supervisor.id}",
        json={"role": "admin"},
        headers=auth_headers_for(supervisor),
    )
    assert resp.status_code == 403

    # 2. Admin cannot deactivate their own account
    admin_headers = auth_headers_for(admin)
    self_deact_resp = app_client.patch(
        f"/api/v1/users/{admin.id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert self_deact_resp.status_code == 409
    assert "cannot deactivate their own account" in self_deact_resp.json()["error"]["message"]

    # 3. Admin cannot demote themselves if they are the only active admin
    self_demote_resp = app_client.patch(
        f"/api/v1/users/{admin.id}",
        json={"role": "viewer"},
        headers=admin_headers,
    )
    assert self_demote_resp.status_code == 409
    assert "sole active administrator" in self_demote_resp.json()["error"]["message"]


# ==============================================================================
# Scenario 13: Resource scope querying isolation
# ==============================================================================

def test_resource_scope_querying_isolation(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 13: Querying devices or readings with non-existent or other worksite IDs returns empty."""
    viewer = seeded_users_and_assets["viewer"]
    headers = auth_headers_for(viewer)
    random_worksite_id = uuid.uuid4()

    # Query devices for other worksite
    resp = app_client.get(f"/api/v1/devices?worksite_id={random_worksite_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["pagination"]["total"] == 0

    # Query reading history for other worksite
    resp_hist = app_client.get(f"/api/v1/readings/history?worksite_id={random_worksite_id}", headers=headers)
    assert resp_hist.status_code == 200
    assert resp_hist.json()["data"] == []
    assert resp_hist.json()["pagination"]["total"] == 0


# ==============================================================================
# Scenario 14: Device credentials cannot perform human-user actions
# ==============================================================================

def test_device_credentials_cannot_perform_human_actions(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 14: X-Device-Token presented on human user endpoints is strictly rejected with 401."""
    alert = seeded_users_and_assets["alert"]
    device_headers = {"X-Device-Token": "device-preshared-secret-key-1234"}

    # 1. Alert acknowledgement
    resp1 = app_client.post(
        f"/api/v1/alerts/{alert.id}/acknowledge",
        json={"action_taken": "Spoofed device ack"},
        headers=device_headers,
    )
    assert resp1.status_code == 401
    assert "Device credentials cannot be used" in resp1.json()["error"]["message"]

    # 2. Device listing
    resp2 = app_client.get("/api/v1/devices", headers=device_headers)
    assert resp2.status_code == 401
    assert "Device credentials cannot be used" in resp2.json()["error"]["message"]

    # 3. User listing
    resp3 = app_client.get("/api/v1/users", headers=device_headers)
    assert resp3.status_code == 401


# ==============================================================================
# Scenario 15: Device ingestion authentication maintained
# ==============================================================================

def test_device_ingestion_authentication_maintained(app_client: TestClient, seeded_users_and_assets: dict):
    """Scenario 15: Device telemetry ingestion succeeds with valid device token; rejects user JWT."""
    device = seeded_users_and_assets["device"]
    admin = seeded_users_and_assets["admin"]

    payload = {
        "device_code": device.device_code,
        "event_id": f"evt-{uuid.uuid4()}",
        "temperature_c": 38.2,
        "relative_humidity_pct": 65.0,
        "measured_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Device ingestion with valid device token -> Success (201)
    resp_ok = app_client.post(
        "/api/v1/readings",
        json=payload,
        headers={"X-Device-Token": "device-preshared-secret-key-1234"},
    )
    assert resp_ok.status_code == 201
    assert resp_ok.json()["data"]["device_id"] == str(device.id)

    # 2. Device ingestion with human JWT token -> Rejected (401)
    user_token, _ = create_access_token(admin.id, admin.email, admin.role)
    payload["event_id"] = f"evt-{uuid.uuid4()}"
    resp_reject = app_client.post(
        "/api/v1/readings",
        json=payload,
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp_reject.status_code == 401
    assert "Human user credentials cannot be used for device telemetry ingestion" in resp_reject.json()["error"]["message"]
