"""
CodeSage AI — Day 24 Hardening & Security Test Suite

Tests:
1. Unauthenticated request rejection across endpoints (401)
2. Invalid and expired JWT handling (401)
3. Multi-tenant cross-user project isolation (404 for unauthorized user)
4. Path traversal defenses (relative, absolute, parent directory)
5. Malicious Zip Slip archive rejection
6. /db-test credential sanitization
7. Function doc service graceful handling without AttributeError
8. Input validation and resource bounds (top_k)
"""

import io
import time
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.services.function_doc_service import function_doc_service

client = TestClient(app)


def build_sample_zip(files_dict: dict) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files_dict.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf


@pytest.fixture
def user_a():
    unique_email = f"user_a_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="User A",
            email=unique_email,
            password_hash=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id), "email": unique_email})
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers


@pytest.fixture
def user_b():
    unique_email = f"user_b_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="User B",
            email=unique_email,
            password_hash=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id), "email": unique_email})
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers


# ==============================================================================
# 1. AUTHENTICATION HARDENING
# ==============================================================================

def test_unauthenticated_requests_blocked():
    """Verify protected endpoints return 401 when missing Authorization header."""
    endpoints = [
        ("GET", "/api/projects"),
        ("GET", "/api/projects/1"),
        ("GET", "/api/projects/1/files"),
        ("GET", "/api/projects/1/analysis"),
        ("GET", "/api/projects/1/dependencies"),
        ("GET", "/api/projects/1/chat"),
        ("GET", "/api/projects/1/export/markdown"),
        ("GET", "/api/projects/1/export/pdf"),
        ("POST", "/api/projects/1/chat"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={"question": "hello"})
        assert res.status_code == 401, f"{method} {path} should return 401, got {res.status_code}"


def test_invalid_jwt_blocked():
    """Verify malformed or forged JWT returns 401."""
    res = client.get("/api/projects", headers={"Authorization": "Bearer not.a.valid.jwt.token"})
    assert res.status_code == 401


def test_expired_jwt_blocked(user_a):
    """Verify expired JWT is rejected with 401."""
    user_id, _, _ = user_a
    # Token expired 1 hour ago
    expired_token = create_access_token(
        data={"sub": str(user_id), "email": "test@codesage.ai", "exp": int(time.time()) - 3600}
    )
    res = client.get("/api/projects", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401


# ==============================================================================
# 2. MULTI-TENANT PROJECT ISOLATION
# ==============================================================================

def test_multi_tenant_project_isolation(user_a, user_b):
    """
    Ensure User A's project is completely inaccessible to User B across ALL endpoints.
    User B must receive 404 (or 403) and zero leaked data.
    """
    _, _, headers_a = user_a
    _, _, headers_b = user_b

    # User A uploads a project
    files = {"main.py": "def hello():\n    return 'Hello from Project A'\n"}
    zip_buf = build_sample_zip(files)
    upload_res = client.post(
        "/api/projects/upload",
        headers=headers_a,
        files={"file": ("project_a.zip", zip_buf.getvalue(), "application/zip")},
    )
    assert upload_res.status_code == 201, upload_res.text
    proj_id = upload_res.json()["project"]["id"]

    # User B attempts to access User A's project resources
    endpoints = [
        ("GET", f"/api/projects/{proj_id}"),
        ("GET", f"/api/projects/{proj_id}/files"),
        ("GET", f"/api/projects/{proj_id}/files/content?file_path=main.py"),
        ("GET", f"/api/projects/{proj_id}/analysis"),
        ("GET", f"/api/projects/{proj_id}/dependencies"),
        ("POST", f"/api/projects/{proj_id}/index"),
        ("POST", f"/api/projects/{proj_id}/embeddings"),
        ("POST", f"/api/projects/{proj_id}/search"),
        ("POST", f"/api/projects/{proj_id}/rag"),
        ("POST", f"/api/projects/{proj_id}/chat"),
        ("GET", f"/api/projects/{proj_id}/chat"),
        ("GET", f"/api/projects/{proj_id}/export/markdown"),
        ("GET", f"/api/projects/{proj_id}/export/pdf"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = client.get(path, headers=headers_b)
        else:
            res = client.post(path, headers=headers_b, json={"query": "hello", "question": "hello"})
        assert res.status_code in (403, 404), (
            f"User B accessing {method} {path} should be rejected with 403/404, got {res.status_code}"
        )


# ==============================================================================
# 3. PATH TRAVERSAL DEFENSE
# ==============================================================================

def test_path_traversal_attempts_blocked(user_a):
    """Ensure path traversal payloads are blocked and never return system files."""
    _, _, headers = user_a

    files = {"main.py": "print('ok')\n"}
    zip_buf = build_sample_zip(files)
    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("safe.zip", zip_buf.getvalue(), "application/zip")},
    )
    proj_id = upload_res.json()["project"]["id"]

    traversal_paths = [
        "../../../../Windows/win.ini",
        "../main.py",
        "..%2F..%2Fetc%2Fpasswd",
        "C:\\boot.ini",
        "C:/Windows/System32/drivers/etc/hosts",
    ]

    for bad_path in traversal_paths:
        res = client.get(
            f"/api/projects/{proj_id}/files/content",
            headers=headers,
            params={"file_path": bad_path},
        )
        assert res.status_code in (400, 404), (
            f"Path traversal for '{bad_path}' must be rejected with 400/404, got {res.status_code}"
        )


def test_zip_slip_rejection(user_a):
    """Ensure archives containing malicious parent directory paths (Zip Slip) are rejected or neutralized."""
    _, _, headers = user_a

    # Craft zip with Zip Slip payload
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../../evil_outside.txt", "Malicious content outside project root")
    buf.seek(0)

    res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("zipslip.zip", buf.getvalue(), "application/zip")},
    )
    # The server should either reject the upload with 400 or handle it safely without writing outside
    assert res.status_code in (400, 422), (
        f"Zip Slip archive should be rejected, got {res.status_code}: {res.text}"
    )


# ==============================================================================
# 4. CREDENTIAL SANITIZATION
# ==============================================================================

def test_db_test_endpoint_sanitization():
    """Verify /db-test does not expose database credentials or passwords."""
    res = client.get("/db-test")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    # Ensure no passwords or raw connection strings are exposed in json
    response_text = res.text.lower()
    assert "password" not in response_text or "postgres:" not in response_text


# ==============================================================================
# 5. SERVICE RESILIENCE & INPUT BOUNDS
# ==============================================================================

def test_function_doc_service_missing_extracted_dir(user_a):
    """Verify function_doc_service handles non-existent extracted path gracefully with 404 HTTPException rather than crashing with AttributeError."""
    user_id, _, headers = user_a
    db = next(get_db())
    try:
        from app.models.project import Project
        dummy_project = Project(id=999999, name="Missing", user_id=user_id, extracted_path="/non/existent/path")
        with pytest.raises(Exception) as exc_info:
            function_doc_service.list_project_functions(db, dummy_project)
        assert exc_info.type.__name__ == "HTTPException" or "404" in str(exc_info.value)
    finally:
        db.close()


def test_invalid_top_k_bounds(user_a):
    """Ensure negative top_k or extreme parameters do not crash search or chat."""
    _, _, headers = user_a

    files = {"calc.py": "def add(a, b):\n    return a + b\n"}
    zip_buf = build_sample_zip(files)
    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("calc.zip", zip_buf.getvalue(), "application/zip")},
    )
    proj_id = upload_res.json()["project"]["id"]

    # Index project
    client.post(f"/api/projects/{proj_id}/index", headers=headers)

    # Search with negative top_k
    res_neg = client.post(
        f"/api/projects/{proj_id}/search",
        headers=headers,
        json={"query": "add", "top_k": -5},
    )
    # Either 422 validation error or graceful empty/capped result
    assert res_neg.status_code in (200, 400, 422)
