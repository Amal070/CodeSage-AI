"""
CodeSage AI — Day 21 Automated Test Suite: Generate API Documentation

Tests:
1. Endpoint discovery across live FastAPI routers and sub-routers.
2. Tag and category grouping ('Authentication', 'Projects', 'AI & LLM', etc.).
3. Authentication requirements detection (Public vs Bearer JWT).
4. Source code introspection (relative file path, function name, line span).
5. Pydantic request schema field extraction.
6. Pydantic response schema field extraction.
7. Path and query parameters extraction.
8. Synthetic JSON example generation adherence to schema.
9. Full API documentation Markdown export.
10. HTTP GET /api/docs-api/endpoints with filtering.
11. HTTP GET /api/docs-api/endpoint detail and error cases.
12. HTTP POST /api/docs-api/generate with live/fallback generation.
"""

import uuid
import pytest
from unittest.mock import patch
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.schemas.ai import AiHealthResponse, AiHealthOllamaInfo, AiHealthModelInfo
from app.services.api_documentation_service import api_documentation_service
from app.services.ollama_service import ollama_service

client = TestClient(app)

MOCK_API_MARKDOWN = """## POST /api/auth/register

**Summary**
Register a new user

**Purpose & Overview**
Registers a new user account into CodeSage AI, hashing passwords securely.

**Authentication**
- Required: No (Public)

**Parameters**
- Path Parameters: None
- Query Parameters: None

**Request Body**
- Content-Type: application/json
- Schema / Model: UserRegisterRequest
- Fields:
  - `name` (str, required)
  - `email` (str, required)
  - `password` (str, required)

**Responses**
- `201 Created`
  - Schema: UserResponse
  - Fields:
    - `id` (int)
    - `email` (str)

**Dependencies & Services**
- PostgreSQL Session (get_db)

**Example Request**
```json
{
  "name": "Developer Alice",
  "email": "alice@example.com",
  "password": "Password123!"
}
```

**Example Response**
```json
{
  "id": 1,
  "email": "alice@example.com"
}
```

**Source Reference**
- File: `backend/app/api/auth.py`
- Handler: `register()`
- Range: Lines 65–97
"""


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def auth_user():
    """Creates a temporary authenticated test user."""
    email = f"day21_tester_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Day 21 Tester",
            email=email,
            password_hash=hash_password("SecurePassword123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id), "email": email})
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers


# ==============================================================================
# UNIT & INTROSPECTION TESTS
# ==============================================================================

def test_discover_all_endpoints():
    """Verifies that all live API routes are discovered from FastAPI."""
    catalog = api_documentation_service.discover_all_endpoints(app, force_refresh=True)

    assert catalog.total_endpoints >= 25, f"Expected at least 25 endpoints, found {catalog.total_endpoints}"
    assert "Authentication" in catalog.tags
    assert "Projects" in catalog.tags
    assert "AI & LLM" in catalog.tags
    assert "API Documentation" in catalog.tags

    paths = [ep.path for ep in catalog.endpoints]
    assert "/api/auth/register" in paths
    assert "/api/auth/login" in paths
    assert "/api/auth/me" in paths
    assert "/api/projects/upload" in paths
    assert "/api/projects/{project_id}/chat" in paths
    assert "/api/ai/health" in paths
    assert "/api/docs-api/endpoints" in paths


def test_auth_detection_accuracy():
    """Verifies public vs protected endpoint authentication detection."""
    catalog = api_documentation_service.discover_all_endpoints(app)
    by_key = {(ep.method, ep.path): ep for ep in catalog.endpoints}

    # Public endpoints
    reg_ep = by_key.get(("POST", "/api/auth/register"))
    assert reg_ep is not None
    assert reg_ep.auth_required is False
    assert "None" in reg_ep.auth_type

    login_ep = by_key.get(("POST", "/api/auth/login"))
    assert login_ep is not None
    assert login_ep.auth_required is False

    # Protected endpoints
    me_ep = by_key.get(("GET", "/api/auth/me"))
    assert me_ep is not None
    assert me_ep.auth_required is True
    assert "JWT" in me_ep.auth_type

    chat_ep = by_key.get(("POST", "/api/projects/{project_id}/chat"))
    assert chat_ep is not None
    assert chat_ep.auth_required is True
    assert "JWT" in chat_ep.auth_type


def test_source_location_introspection():
    """Verifies that endpoint handlers map to accurate source file and line spans."""
    catalog = api_documentation_service.discover_all_endpoints(app)
    by_key = {(ep.method, ep.path): ep for ep in catalog.endpoints}

    # Register endpoint in auth.py
    reg_ep = by_key[("POST", "/api/auth/register")]
    assert "auth.py" in reg_ep.source_file
    assert reg_ep.source_function == "register"
    assert reg_ep.source_start_line > 0
    assert reg_ep.source_end_line >= reg_ep.source_start_line
    assert "Lines " in reg_ep.source_line_range

    # Upload endpoint in project.py
    upload_ep = by_key[("POST", "/api/projects/upload")]
    assert "project.py" in upload_ep.source_file
    assert upload_ep.source_function == "upload_project"


def test_pydantic_schema_field_extraction():
    """Verifies that Pydantic request and response schemas are parsed into fields."""
    catalog = api_documentation_service.discover_all_endpoints(app)
    by_key = {(ep.method, ep.path): ep for ep in catalog.endpoints}

    # UserRegisterRequest
    reg_ep = by_key[("POST", "/api/auth/register")]
    assert reg_ep.request_model_name == "UserRegisterRequest"
    req_field_names = [f.name for f in reg_ep.request_fields]
    assert "name" in req_field_names
    assert "email" in req_field_names
    assert "password" in req_field_names

    # UserResponse
    assert reg_ep.response_model_name == "UserResponse"
    res_field_names = [f.name for f in reg_ep.response_fields]
    assert "id" in res_field_names
    assert "email" in res_field_names

    # ChatRequest
    chat_ep = by_key[("POST", "/api/projects/{project_id}/chat")]
    assert chat_ep.request_model_name == "ChatRequest"
    chat_fields = [f.name for f in chat_ep.request_fields]
    assert "question" in chat_fields
    assert "top_k" in chat_fields


def test_path_and_query_parameter_extraction():
    """Verifies extraction of path and query parameters with type information."""
    catalog = api_documentation_service.discover_all_endpoints(app)
    by_key = {(ep.method, ep.path): ep for ep in catalog.endpoints}

    # /api/projects/{project_id}/file has path param and query param 'path'
    file_ep = by_key[("GET", "/api/projects/{project_id}/file")]
    path_param_names = [p.name for p in file_ep.path_params]
    assert "project_id" in path_param_names

    query_param_names = [q.name for q in file_ep.query_params]
    assert "path" in query_param_names

    # /api/projects/{project_id}/chunks has 'limit' and 'offset' query params
    chunks_ep = by_key[("GET", "/api/projects/{project_id}/chunks")]
    q_names = [q.name for q in chunks_ep.query_params]
    assert "limit" in q_names
    assert "offset" in q_names


def test_example_generation_consistency():
    """Verifies that generated JSON examples adhere to actual schema fields."""
    catalog = api_documentation_service.discover_all_endpoints(app)
    by_key = {(ep.method, ep.path): ep for ep in catalog.endpoints}

    reg_ep = by_key[("POST", "/api/auth/register")]
    assert isinstance(reg_ep.example_request, dict)
    assert "email" in reg_ep.example_request
    assert "password" in reg_ep.example_request

    assert isinstance(reg_ep.example_response, dict)
    assert "id" in reg_ep.example_response
    assert "email" in reg_ep.example_response


def test_markdown_export():
    """Verifies full API markdown reference compilation."""
    export = api_documentation_service.export_all_markdown(app)

    assert export.total_endpoints >= 25
    assert "# CodeSage AI — API Documentation Reference" in export.markdown
    assert "## Table of Contents" in export.markdown
    assert "### Authentication" in export.markdown
    assert "POST /api/auth/register" in export.markdown
    assert "POST /api/projects/{project_id}/chat" in export.markdown


# ==============================================================================
# HTTP API ROUTE TESTS
# ==============================================================================

def test_api_list_endpoints_unauthorized():
    """Verifies that accessing documentation API requires authentication."""
    resp = client.get("/api/docs-api/endpoints")
    assert resp.status_code == 401


def test_api_list_endpoints_authorized(auth_user):
    """Verifies GET /api/docs-api/endpoints with filters."""
    _, _, headers = auth_user

    # Full catalog
    resp = client.get("/api/docs-api/endpoints", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_endpoints"] >= 25
    assert len(data["endpoints"]) == data["total_endpoints"]

    # Tag filter
    resp_tag = client.get("/api/docs-api/endpoints?tag=Authentication", headers=headers)
    assert resp_tag.status_code == 200
    tag_data = resp_tag.json()
    assert tag_data["total_endpoints"] >= 3
    for ep in tag_data["endpoints"]:
        assert ep["tag"] == "Authentication"

    # Search filter
    resp_search = client.get("/api/docs-api/endpoints?search=chat", headers=headers)
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert any("chat" in ep["path"] for ep in search_data["endpoints"])


def test_api_get_endpoint_detail(auth_user):
    """Verifies GET /api/docs-api/endpoint."""
    _, _, headers = auth_user

    resp = client.get("/api/docs-api/endpoint?path=/api/auth/login&method=POST", headers=headers)
    assert resp.status_code == 200
    ep = resp.json()
    assert ep["path"] == "/api/auth/login"
    assert ep["method"] == "POST"
    assert ep["request_model_name"] == "UserLoginRequest"

    # Non-existent endpoint
    resp_404 = client.get("/api/docs-api/endpoint?path=/nonexistent/path&method=GET", headers=headers)
    assert resp_404.status_code == 404


def test_api_generate_documentation(auth_user):
    """Verifies POST /api/docs-api/generate endpoint with mocked LLM output."""
    _, _, headers = auth_user

    payload = {
        "path": "/api/auth/register",
        "method": "POST",
    }
    healthy_resp = AiHealthResponse(
        ollama=AiHealthOllamaInfo(available=True),
        model=AiHealthModelInfo(name="gemma:2b", available=True),
    )
    with patch.object(ollama_service, "check_health", return_value=healthy_resp):
        with patch.object(ollama_service, "generate", return_value=MOCK_API_MARKDOWN):
            resp = client.post("/api/docs-api/generate", json=payload, headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["endpoint"]["path"] == "/api/auth/register"
            assert "POST /api/auth/register" in data["markdown"]
            assert "Authentication" in data["markdown"]
            assert "Parameters" in data["markdown"]
            assert "Request Body" in data["markdown"]
            assert "Responses" in data["markdown"]


def test_api_generate_documentation_fallback(auth_user):
    """Verifies POST /api/docs-api/generate deterministic fallback when LLM errors."""
    _, _, headers = auth_user

    payload = {
        "path": "/api/auth/register",
        "method": "POST",
    }
    # Simulate LLM unreachable
    with patch.object(ollama_service, "check_health", side_effect=Exception("Ollama offline")):
        resp = client.post("/api/docs-api/generate", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["endpoint"]["path"] == "/api/auth/register"
        assert "## POST /api/auth/register" in data["markdown"]
        assert "Purpose & Overview" in data["markdown"]
        assert "UserRegisterRequest" in data["markdown"]
        assert "UserResponse" in data["markdown"]
        assert "Lines 65" in data["markdown"]


def test_api_export_markdown_http(auth_user):
    """Verifies GET /api/docs-api/markdown endpoint."""
    _, _, headers = auth_user

    resp = client.get("/api/docs-api/markdown", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_endpoints"] >= 25
    assert len(data["markdown"]) > 500

