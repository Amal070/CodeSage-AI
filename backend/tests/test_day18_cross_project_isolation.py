"""
CodeSage AI — Day 18 Test Suite: Cross-Project Isolation & Multi-User Tenancy

Tests:
1. Cross-project semantic isolation (Django vs React vs Python vector indices)
2. Multi-user tenancy isolation across all project API surfaces (Files, Analysis, Parsing, Indexing, Embeddings, FAISS, Retrieval, Chat)
3. Syntax error resilience and error recovery (Step 15 & 45)
"""

import io
import uuid
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from tests.fixtures.sample_projects import (
    DJANGO_PROJECT_FILES,
    REACT_PROJECT_FILES,
    PYTHON_PROJECT_FILES,
    build_project_zip,
)

client = TestClient(app)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def user_a():
    """Create User A."""
    unique_email = f"iso_user_a_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Isolation User A",
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
    """Create User B."""
    unique_email = f"iso_user_b_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Isolation User B",
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
# 1. CROSS-PROJECT ISOLATION (Step 39)
# ==============================================================================

def test_cross_project_isolation(user_a):
    """
    Step 39: Ensure vector search and context retrieval for Project A
    never bleed into or retrieve chunks from Project B or C.
    """
    user_id, token, headers = user_a

    # 1. Upload Django project
    res_django = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("django.zip", build_project_zip(DJANGO_PROJECT_FILES).getvalue(), "application/zip")},
    )
    django_id = res_django.json()["project"]["id"]

    # 2. Upload React project
    res_react = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("react.zip", build_project_zip(REACT_PROJECT_FILES).getvalue(), "application/zip")},
    )
    react_id = res_react.json()["project"]["id"]

    # 3. Index, embed, and build FAISS for both projects
    client.post(f"/api/projects/{django_id}/index", headers=headers)
    client.post(f"/api/projects/{django_id}/embeddings", headers=headers)
    client.post(f"/api/projects/{django_id}/vector-index", headers=headers)

    client.post(f"/api/projects/{react_id}/index", headers=headers)
    client.post(f"/api/projects/{react_id}/embeddings", headers=headers)
    client.post(f"/api/projects/{react_id}/vector-index", headers=headers)

    # 4. Ask Django project about React component
    django_query_res = client.post(
        f"/api/projects/{django_id}/context/retrieve",
        headers=headers,
        json={"query": "How does the React TaskCard component work?", "top_files": 5},
    )
    assert django_query_res.status_code == 200
    django_files = [f["file_path"].replace("\\", "/") for f in django_query_res.json()["files"]]
    # Must NOT contain any React files
    assert not any("TaskCard.jsx" in f or "src/App.jsx" in f for f in django_files)

    # 5. Ask React project about Django model
    react_query_res = client.post(
        f"/api/projects/{react_id}/context/retrieve",
        headers=headers,
        json={"query": "How does the Django CustomUser model work?", "top_files": 5},
    )
    assert react_query_res.status_code == 200
    react_files = [f["file_path"].replace("\\", "/") for f in react_query_res.json()["files"]]
    # Must NOT contain any Django files
    assert not any("accounts/models.py" in f or "settings.py" in f for f in react_files)


# ==============================================================================
# 2. MULTI-USER TENANCY ISOLATION (Step 40)
# ==============================================================================

def test_multi_user_tenancy_isolation(user_a, user_b):
    """
    Step 40: User B must receive HTTP 404 when attempting to access User A's project
    across all API endpoints.
    """
    _, _, headers_a = user_a
    _, _, headers_b = user_b

    # User A uploads a project
    res_a = client.post(
        "/api/projects/upload",
        headers=headers_a,
        files={"file": ("django.zip", build_project_zip(DJANGO_PROJECT_FILES).getvalue(), "application/zip")},
    )
    project_a_id = res_a.json()["project"]["id"]

    # User B attempts to access User A's project endpoints
    endpoints_to_test = [
        ("GET", f"/api/projects/{project_a_id}"),
        ("GET", f"/api/projects/{project_a_id}/files"),
        ("GET", f"/api/projects/{project_a_id}/file?path=manage.py"),
        ("GET", f"/api/projects/{project_a_id}/analysis"),
        ("GET", f"/api/projects/{project_a_id}/dependencies"),
        ("POST", f"/api/projects/{project_a_id}/index"),
        ("POST", f"/api/projects/{project_a_id}/embeddings"),
        ("POST", f"/api/projects/{project_a_id}/vector-index"),
        ("POST", f"/api/projects/{project_a_id}/context/retrieve"),
        ("POST", f"/api/projects/{project_a_id}/chat"),
    ]

    for method, path in endpoints_to_test:
        if method == "GET":
            resp = client.get(path, headers=headers_b)
        else:
            resp = client.post(path, headers=headers_b, json={"query": "test", "question": "test"})
        assert resp.status_code == 404, f"Endpoint {method} {path} should return 404 for User B, got {resp.status_code}"


# ==============================================================================
# 3. SYNTAX ERROR RESILIENCE & ERROR RECOVERY (Steps 15 & 45)
# ==============================================================================

def test_syntax_error_resilience(user_a):
    """
    Step 15 & 45: A project with a malformed source file must NOT crash analysis or indexing.
    The valid files must still be parsed and indexed successfully.
    """
    _, _, headers = user_a

    malformed_project_files = {
        "valid_module.py": (
            "def calculate_total(prices):\n"
            "    return sum(prices)\n"
        ),
        "broken_syntax.py": (
            "def broken_function(\n"  # Unterminated syntax
            "    print('incomplete'\n"
        ),
    }

    res_upload = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("malformed.zip", build_project_zip(malformed_project_files).getvalue(), "application/zip")},
    )
    assert res_upload.status_code == 201
    project_id = res_upload.json()["project"]["id"]

    # 1. Project Analysis succeeds
    analysis_res = client.get(f"/api/projects/{project_id}/analysis", headers=headers)
    assert analysis_res.status_code == 200

    # 2. Tree-sitter parsing on the broken file fails gracefully without crashing server
    parse_res = client.get(f"/api/projects/{project_id}/parse?path=broken_syntax.py", headers=headers)
    assert parse_res.status_code == 200
    assert parse_res.json()["file"] == "broken_syntax.py"

    # 3. Indexing continues and indexes the valid file
    index_res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert index_res.status_code == 200
    assert index_res.json()["status"] == "completed"
    assert index_res.json()["indexed_files"] >= 1
