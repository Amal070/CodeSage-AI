import uuid
from datetime import timedelta
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

client = TestClient(app)


def get_random_email() -> str:
    """Generate a unique email address for test isolation."""
    unique_id = uuid.uuid4().hex[:8]
    return f"testuser_{unique_id}@codesage.ai"


# ============================================================
# 1. PASSWORD HASHING UNIT TESTS
# ============================================================

def test_password_hashing_and_verification():
    """Verify that bcrypt password hashing is one-way, salted, and verifiable."""
    raw_pwd = "SecurePassword123!"
    hashed = hash_password(raw_pwd)

    # Must not store plaintext
    assert hashed != raw_pwd
    # Must start with bcrypt prefix
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    # Must verify correctly
    assert verify_password(raw_pwd, hashed) is True
    # Wrong password must fail
    assert verify_password("WrongPassword!", hashed) is False


# ============================================================
# 2. JWT TOKEN UNIT TESTS
# ============================================================

def test_jwt_creation_and_expiration():
    """Verify that JWT tokens can be created, decoded, and expire correctly."""
    payload = {"sub": "999", "email": "test_jwt@codesage.ai"}
    token = create_access_token(data=payload, expires_delta=timedelta(minutes=15))

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded.get("sub") == "999"
    assert decoded.get("email") == "test_jwt@codesage.ai"
    assert "exp" in decoded

    # Expired token test
    expired_token = create_access_token(
        data=payload,
        expires_delta=timedelta(seconds=-10)
    )
    assert decode_access_token(expired_token) is None


# ============================================================
# 3. REGISTRATION API TESTS (POST /api/auth/register)
# ============================================================

def test_register_valid_user():
    """Registering a new user should return 201 and safe user profile without password hash."""
    test_email = get_random_email()
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Alex Sage",
            "email": test_email,
            "password": "Password123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alex Sage"
    assert data["email"] == test_email.lower()
    assert "id" in data
    assert "created_at" in data
    # Ensure sensitive data is never exposed
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email():
    """Registering an already existing email address should return 400 Bad Request."""
    test_email = get_random_email()
    payload = {
        "name": "Original User",
        "email": test_email,
        "password": "Password123!",
    }

    # First registration: succeeds
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with same email: fails
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


def test_register_invalid_email_format():
    """Registering with an invalid email should return 422 Unprocessable Entity."""
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Invalid Email",
            "email": "not-an-email",
            "password": "Password123!",
        },
    )
    assert response.status_code == 422


def test_register_weak_or_short_password():
    """Registering with a password shorter than 6 chars should return 422."""
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Short Pwd",
            "email": get_random_email(),
            "password": "123",
        },
    )
    assert response.status_code == 422


# ============================================================
# 4. LOGIN API TESTS (POST /api/auth/login)
# ============================================================

def test_login_success():
    """Login with valid credentials returns 200 and a valid Bearer JWT."""
    test_email = get_random_email()
    password = "CorrectPassword123!"

    # Register first
    reg_res = client.post(
        "/api/auth/register",
        json={
            "name": "Login User",
            "email": test_email,
            "password": password,
        },
    )
    assert reg_res.status_code == 201

    # Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": password},
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_email.lower()
    assert "password_hash" not in data["user"]


def test_login_wrong_password():
    """Login with incorrect password returns 401 Unauthorized."""
    test_email = get_random_email()
    reg_res = client.post(
        "/api/auth/register",
        json={
            "name": "Wrong Pwd User",
            "email": test_email,
            "password": "CorrectPassword123!",
        },
    )
    assert reg_res.status_code == 201

    login_res = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": "WrongPassword!"},
    )
    assert login_res.status_code == 401
    assert "invalid email or password" in login_res.json()["detail"].lower()


def test_login_non_existent_user():
    """Login with non-existent email returns 401 without revealing user existence."""
    login_res = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent_9999@codesage.ai",
            "password": "SomePassword123!",
        },
    )
    assert login_res.status_code == 401
    assert "invalid email or password" in login_res.json()["detail"].lower()


# ============================================================
# 5. PROTECTED ROUTE TESTS (GET /api/auth/me)
# ============================================================

def test_get_me_without_token():
    """Accessing /api/auth/me without token returns 401 Unauthorized."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_with_invalid_token():
    """Accessing /api/auth/me with invalid token returns 401 Unauthorized."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401


def test_get_me_with_expired_token():
    """Accessing /api/auth/me with expired token returns 401 Unauthorized."""
    expired_token = create_access_token(
        data={"sub": "1", "email": "test@codesage.ai"},
        expires_delta=timedelta(seconds=-60),
    )
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


def test_get_me_with_valid_token():
    """Accessing /api/auth/me with valid token returns the authenticated user profile."""
    test_email = get_random_email()
    password = "ProfilePassword123!"

    # Register
    reg_res = client.post(
        "/api/auth/register",
        json={
            "name": "Profile Owner",
            "email": test_email,
            "password": password,
        },
    )
    assert reg_res.status_code == 201

    # Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": test_email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Protected me
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["name"] == "Profile Owner"
    assert data["email"] == test_email.lower()
    assert "password_hash" not in data


# ============================================================
# 6. REGRESSION TESTS (Day 1 & Day 2 Endpoints)
# ============================================================

def test_regression_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json().get("status") == "online"


def test_regression_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json().get("status") == "OK"


def test_regression_system_info():
    res = client.get("/api/system-info")
    assert res.status_code == 200
    assert res.json().get("framework") == "FastAPI"


def test_regression_db_test():
    res = client.get("/db-test")
    assert res.status_code == 200
    assert res.json().get("status") == "success"
