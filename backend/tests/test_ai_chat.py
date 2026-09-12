import uuid
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.chat_history import ChatHistory

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a primary test user and return (user_id, token, headers)."""
    unique_email = f"chat_user_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Chat Primary User",
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
def second_user():
    """Create a secondary test user for tenancy isolation verification."""
    unique_email = f"chat_secondary_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Chat Secondary User",
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


def create_mock_project(user_id: int, name: str = "Chat Test Project") -> int:
    """Helper to create a Project record in PostgreSQL."""
    db = next(get_db())
    try:
        project = Project(
            name=name,
            original_filename=f"{name}.zip",
            storage_path=f"storage/projects/mock_{uuid.uuid4().hex[:6]}",
            extracted_path=f"storage/projects/mock_{uuid.uuid4().hex[:6]}/extracted",
            file_count=2,
            lines_of_code=40,
            status="completed",
            user_id=user_id,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project.id
    finally:
        db.close()


# ===================================================================
# Authentication & Tenancy Isolation Tests
# ===================================================================

def test_chat_unauthenticated():
    """POST, GET, DELETE /api/projects/{id}/chat without token must return 401."""
    res_post = client.post("/api/projects/1/chat", json={"question": "Explain authentication."})
    assert res_post.status_code == 401

    res_get = client.get("/api/projects/1/chat")
    assert res_get.status_code == 401

    res_delete = client.delete("/api/projects/1/chat")
    assert res_delete.status_code == 401


def test_chat_project_not_found(test_user):
    """Chat endpoints for non-existent project return 404."""
    _, _, headers = test_user
    res_post = client.post(
        "/api/projects/999999/chat",
        headers=headers,
        json={"question": "Explain authentication."},
    )
    assert res_post.status_code == 404
    assert "not found" in res_post.json()["detail"].lower()

    res_get = client.get("/api/projects/999999/chat", headers=headers)
    assert res_get.status_code == 404

    res_del = client.delete("/api/projects/999999/chat", headers=headers)
    assert res_del.status_code == 404


def test_chat_tenancy_isolation(test_user, second_user):
    """User B cannot chat with, view, or clear User A's project chat history."""
    user1_id, _, headers1 = test_user
    _, _, headers2 = second_user

    project_id = create_mock_project(user1_id, name="User1 Private Project")

    # User 2 tries to chat with User 1's project -> 404
    res_post = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers2,
        json={"question": "Where is the secret key?"},
    )
    assert res_post.status_code == 404
    assert "not found" in res_post.json()["detail"].lower()

    # User 2 tries to get User 1's chat history -> 404
    res_get = client.get(f"/api/projects/{project_id}/chat", headers=headers2)
    assert res_get.status_code == 404

    # User 2 tries to delete User 1's chat history -> 404
    res_del = client.delete(f"/api/projects/{project_id}/chat", headers=headers2)
    assert res_del.status_code == 404


# ===================================================================
# Request Validation Tests
# ===================================================================

def test_chat_validation_empty_question(test_user):
    """Empty or whitespace-only questions must be rejected with 400 or 422."""
    user_id, _, headers = test_user
    project_id = create_mock_project(user_id)

    # Empty string
    res = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": ""},
    )
    assert res.status_code in [400, 422]

    # Whitespace only
    res = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "    \n\t  "},
    )
    assert res.status_code in [400, 422]


def test_chat_validation_excessive_question(test_user):
    """Questions exceeding 5000 characters must be rejected with 400 or 422."""
    user_id, _, headers = test_user
    project_id = create_mock_project(user_id)

    oversized = "explain " * 750  # 6000 characters
    res = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": oversized},
    )
    assert res.status_code in [400, 422]


def test_chat_validation_top_k_bounds(test_user):
    """top_k must be between 1 and 10."""
    user_id, _, headers = test_user
    project_id = create_mock_project(user_id)

    # top_k = 0 (below min 1)
    res_zero = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Explain authentication", "top_k": 0},
    )
    assert res_zero.status_code in [400, 422]

    # top_k = 50 (above max 10)
    res_large = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Explain authentication", "top_k": 50},
    )
    assert res_large.status_code in [400, 422]


def test_chat_unindexed_project(test_user):
    """An unindexed project returns 400 indicating indexing is required."""
    user_id, _, headers = test_user
    project_id = create_mock_project(user_id, name="Unindexed Chat Project")

    res = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Explain this function."},
    )
    assert res.status_code == 400
    detail = res.json()["detail"].lower()
    assert "index" in detail or "context" in detail


# ===================================================================
# Live AI Chat & ChatHistory Persistence Tests
# ===================================================================

def test_chat_history_direct_persistence(test_user):
    """
    Directly verify ChatHistory model creation, query, and cascade deletion.
    """
    user_id, _, headers = test_user
    project_id = create_mock_project(user_id, name="History Test Project")

    db = next(get_db())
    try:
        entry = ChatHistory(
            user_id=user_id,
            project_id=project_id,
            message="Explain database connection.",
            response="Database connection is established via SQLAlchemy engine in app/database.py.",
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        entry_id = entry.id
    finally:
        db.close()

    # Retrieve chat history via API
    res = client.get(f"/api/projects/{project_id}/chat", headers=headers)
    assert res.status_code == 200
    history = res.json()
    assert len(history) >= 1
    found = next((item for item in history if item["id"] == entry_id), None)
    assert found is not None
    assert found["message"] == "Explain database connection."
    assert "SQLAlchemy" in found["response"]
    assert found["project_id"] == project_id
    assert found["user_id"] == user_id

    # Clear chat history via API
    del_res = client.delete(f"/api/projects/{project_id}/chat", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "cleared"

    # Confirm history is now empty
    res_after = client.get(f"/api/projects/{project_id}/chat", headers=headers)
    assert res_after.status_code == 200
    assert len(res_after.json()) == 0


def test_chat_live_qa_and_history(test_user):
    """
    End-to-End Live RAG + Chat Test using project #416 (or indexed project):
    1. Authenticate user and reassign project 416 ownership for testing.
    2. Ask: "Where is JWT authentication implemented?"
    3. Verify grounded response, source citations, and chat_id.
    4. Verify the exchange is persisted in ChatHistory table.
    5. Retrieve conversation history via GET /api/projects/416/chat.
    6. Verify clean history clearing via DELETE /api/projects/416/chat.
    """
    user_id, token, headers = test_user

    # Check if project 416 exists and assign ownership to test_user
    db = next(get_db())
    project_416 = db.get(Project, 416)
    if not project_416:
        db.close()
        pytest.skip("Project #416 not found in local database; skipping live RAG chat execution.")

    original_owner = project_416.user_id
    project_416.user_id = user_id
    db.commit()
    db.close()

    try:
        question = "Where is JWT authentication implemented?"
        res = client.post(
            f"/api/projects/416/chat",
            headers=headers,
            json={"question": question, "top_k": 3},
        )

        assert res.status_code == 200
        data = res.json()

        # Verify structured response schema
        assert data["project_id"] == 416
        assert data["question"] == question
        assert len(data["answer"]) > 10
        assert "sources" in data
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) > 0

        # Verify source metadata
        first_source = data["sources"][0]
        assert "file_path" in first_source
        assert "start_line" in first_source
        assert "end_line" in first_source
        assert "score" in first_source

        # Verify chat history persistence
        chat_id = data.get("chat_id")
        assert chat_id is not None
        assert isinstance(chat_id, int)
        assert data.get("created_at") is not None

        # Verify history retrieval
        get_res = client.get("/api/projects/416/chat", headers=headers)
        assert get_res.status_code == 200
        history_items = get_res.json()
        assert len(history_items) >= 1

        matched_item = next((h for h in history_items if h["id"] == chat_id), None)
        assert matched_item is not None
        assert matched_item["message"] == question
        assert matched_item["response"] == data["answer"]

        # Verify history clearing
        del_res = client.delete("/api/projects/416/chat", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "cleared"

        # Verify history is empty
        empty_res = client.get("/api/projects/416/chat", headers=headers)
        assert empty_res.status_code == 200
        assert len(empty_res.json()) == 0

    finally:
        # Restore original owner
        db = next(get_db())
        p = db.get(Project, 416)
        if p:
            p.user_id = original_owner
            db.commit()
        db.close()
