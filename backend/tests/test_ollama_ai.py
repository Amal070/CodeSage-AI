import uuid
from unittest.mock import MagicMock, patch
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.services.ollama_service import OllamaService, ollama_service

client = TestClient(app)


@pytest.fixture
def auth_user():
    """Create a unique authenticated test user and return headers."""
    unique_email = f"ai_tester_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="AI Tester",
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
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# Authentication & Tenancy Tests (Phases 14, 35)
# --------------------------------------------------------------------------

def test_unauthenticated_ai_endpoints_rejected():
    """AI endpoints must strictly reject unauthenticated requests (HTTP 401)."""
    # Health check
    res_health = client.get("/api/ai/health")
    assert res_health.status_code == 401

    # Prompt test
    res_test = client.post("/api/ai/test", json={"prompt": "Hello"})
    assert res_test.status_code == 401


def test_invalid_jwt_token_rejected():
    """AI endpoints must reject malformed or fake JWT tokens (HTTP 401)."""
    bad_headers = {"Authorization": "Bearer totally.invalid.token"}
    res_health = client.get("/api/ai/health", headers=bad_headers)
    assert res_health.status_code == 401

    res_test = client.post("/api/ai/test", json={"prompt": "Hello"}, headers=bad_headers)
    assert res_test.status_code == 401


# --------------------------------------------------------------------------
# Prompt Validation Tests (Phase 15)
# --------------------------------------------------------------------------

def test_empty_and_whitespace_prompts_rejected(auth_user):
    """Empty or whitespace-only prompts must return 400 Bad Request."""
    # Empty string
    res_empty = client.post("/api/ai/test", json={"prompt": ""}, headers=auth_user)
    assert res_empty.status_code in (400, 422)

    # Whitespace only
    res_ws = client.post("/api/ai/test", json={"prompt": "    \n\t   "}, headers=auth_user)
    assert res_ws.status_code in (400, 422)


def test_excessive_prompt_length_rejected(auth_user):
    """Prompts exceeding maximum length (10,000 chars) must be rejected."""
    huge_prompt = "x" * 10001
    res = client.post("/api/ai/test", json={"prompt": huge_prompt}, headers=auth_user)
    assert res.status_code in (400, 422)


# --------------------------------------------------------------------------
# Health Endpoint Schema & Behavior (Phases 11, 20)
# --------------------------------------------------------------------------

def test_ai_health_endpoint_schema(auth_user):
    """Authenticated call to /api/ai/health returns expected structured status."""
    res = client.get("/api/ai/health", headers=auth_user)
    assert res.status_code == 200
    data = res.json()
    assert "ollama" in data
    assert "available" in data["ollama"]
    assert isinstance(data["ollama"]["available"], bool)
    assert "model" in data
    assert "name" in data["model"]
    assert "available" in data["model"]
    assert isinstance(data["model"]["available"], bool)


# --------------------------------------------------------------------------
# Service Layer Mocking & Error Handling (Phases 9, 16, 17, 19, 36, 37)
# --------------------------------------------------------------------------

def test_ollama_service_mocked_generation(auth_user):
    """Verifies OllamaService successfully parses response and forwards system prompt."""
    fake_response = MagicMock()
    fake_response.response = "FastAPI is a modern, fast web framework for building APIs with Python."

    with patch.object(ollama_service, "check_health") as mock_health:
        from app.schemas.ai import AiHealthModelInfo, AiHealthOllamaInfo, AiHealthResponse
        mock_health.return_value = AiHealthResponse(
            ollama=AiHealthOllamaInfo(available=True),
            model=AiHealthModelInfo(name=ollama_service.model_name, available=True),
        )
        with patch.object(ollama_service.client, "generate", return_value=fake_response) as mock_gen:
            res = client.post(
                "/api/ai/test",
                json={
                    "prompt": "What is FastAPI?",
                    "system_prompt": "Be concise.",
                },
                headers=auth_user,
            )
            assert res.status_code == 200
            data = res.json()
            assert "FastAPI" in data["response"]
            assert data["model"] == ollama_service.model_name
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs["prompt"] == "What is FastAPI?"
            assert call_kwargs["system"] == "Be concise."


def test_ollama_unavailable_error_handling(auth_user):
    """When Ollama daemon is unreachable, API returns HTTP 503 with user-friendly message."""
    with patch.object(ollama_service, "check_health") as mock_health:
        from app.schemas.ai import AiHealthModelInfo, AiHealthOllamaInfo, AiHealthResponse
        mock_health.return_value = AiHealthResponse(
            ollama=AiHealthOllamaInfo(available=False),
            model=AiHealthModelInfo(name=ollama_service.model_name, available=False),
        )
        res = client.post(
            "/api/ai/test",
            json={"prompt": "What is FastAPI?"},
            headers=auth_user,
        )
        assert res.status_code == 503
        assert "Ollama service is not running" in res.json()["detail"]


def test_missing_model_error_handling(auth_user):
    """When Gemma model is not installed, API returns HTTP 400 with pull instructions."""
    with patch.object(ollama_service, "check_health") as mock_health:
        from app.schemas.ai import AiHealthModelInfo, AiHealthOllamaInfo, AiHealthResponse
        mock_health.return_value = AiHealthResponse(
            ollama=AiHealthOllamaInfo(available=True),
            model=AiHealthModelInfo(name="gemma:2b", available=False),
        )
        res = client.post(
            "/api/ai/test",
            json={"prompt": "What is FastAPI?"},
            headers=auth_user,
        )
        assert res.status_code == 400
        assert "not installed in Ollama" in res.json()["detail"]
        assert "ollama pull" in res.json()["detail"]


# --------------------------------------------------------------------------
# Live Gemma Inference (Phase 25)
# --------------------------------------------------------------------------

def test_live_gemma_generation(auth_user):
    """
    Executes a real live inference test against local Ollama if Gemma is installed.
    If Gemma is still downloading, the test gracefully passes with a notice.
    """
    health_data = client.get("/api/ai/health", headers=auth_user).json()
    if not health_data.get("ollama", {}).get("available") or not health_data.get("model", {}).get("available"):
        pytest.skip(f"Ollama or model {ollama_service.model_name} not yet ready for live inference.")

    prompt = "In one short sentence, what is Python?"
    res = client.post("/api/ai/test", json={"prompt": prompt}, headers=auth_user)
    assert res.status_code == 200
    data = res.json()
    assert len(data["response"]) > 0
    assert data["model"] == ollama_service.model_name
