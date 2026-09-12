import io
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.services.faiss_service import faiss_service
from app.services.rag_service import rag_service

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a unique test user and return (user_id, token, headers)."""
    unique_email = f"rag_tester_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="RAG Tester",
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
    """Create a second distinct user for tenancy isolation tests."""
    unique_email = f"second_rag_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Second RAG Tester",
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


def create_mock_project(user_id: int, name: str = "RAG Test Project") -> int:
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


# -------------------------------------------------------------------
# Phase 38, 42: Authentication & Tenancy Tests
# -------------------------------------------------------------------

def test_rag_unauthorized():
    """POST /api/projects/{id}/rag without token must return 401."""
    response = client.post("/api/projects/1/rag", json={"question": "Where is auth?"})
    assert response.status_code == 401


def test_rag_project_not_found(test_user):
    """POST /api/projects/999999/rag for non-existent project returns 404."""
    _, _, headers = test_user
    response = client.post(
        "/api/projects/999999/rag",
        headers=headers,
        json={"question": "Where is auth?"},
    )
    assert response.status_code == 404


def test_rag_tenancy_isolation(test_user, second_user):
    """User B cannot access User A's project RAG pipeline (returns 404)."""
    user_a_id, _, _ = test_user
    _, _, headers_b = second_user

    project_a_id = create_mock_project(user_a_id, "User A Secret Project")

    # User B attempts to access User A's project
    response = client.post(
        f"/api/projects/{project_a_id}/rag",
        headers=headers_b,
        json={"question": "Where is secret logic?"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# -------------------------------------------------------------------
# Phase 18: Request & Parameter Validation Tests
# -------------------------------------------------------------------

def test_rag_validation_empty_question(test_user):
    """Empty or whitespace-only question must return 400."""
    user_id, _, headers = test_user
    proj_id = create_mock_project(user_id)

    # Empty string
    res1 = client.post(f"/api/projects/{proj_id}/rag", headers=headers, json={"question": ""})
    assert res1.status_code == 422 or res1.status_code == 400

    # Whitespace only
    res2 = client.post(f"/api/projects/{proj_id}/rag", headers=headers, json={"question": "   "})
    assert res2.status_code == 400
    assert "empty" in res2.json()["detail"].lower()


def test_rag_validation_excessive_question(test_user):
    """Question exceeding MAX_RAG_QUESTION_LENGTH must return 400 or 422."""
    user_id, _, headers = test_user
    proj_id = create_mock_project(user_id)

    giant_q = "what is this code? " * 500  # > 5000 chars
    res = client.post(f"/api/projects/{proj_id}/rag", headers=headers, json={"question": giant_q})
    assert res.status_code in (400, 422)


def test_rag_validation_top_k_bounds(test_user):
    """top_k out of range (< 1 or > 10) must be rejected with 400 or 422."""
    user_id, _, headers = test_user
    proj_id = create_mock_project(user_id)

    res_low = client.post(f"/api/projects/{proj_id}/rag", headers=headers, json={"question": "hello", "top_k": 0})
    assert res_low.status_code in (400, 422)

    res_high = client.post(f"/api/projects/{proj_id}/rag", headers=headers, json={"question": "hello", "top_k": 100})
    assert res_high.status_code in (400, 422)


# -------------------------------------------------------------------
# Phase 34, 36: Unindexed Project Handling
# -------------------------------------------------------------------

def test_rag_unindexed_project(test_user):
    """Unindexed project returns 400 guiding user to index code first."""
    user_id, _, headers = test_user
    proj_id = create_mock_project(user_id, "Fresh Unindexed Project")

    res = client.post(
        f"/api/projects/{proj_id}/rag",
        headers=headers,
        json={"question": "Where is JWT implemented?"},
    )
    assert res.status_code == 400
    detail = res.json()["detail"].lower()
    assert "index" in detail or "available" in detail


# -------------------------------------------------------------------
# Phase 17: Route Aliases (/rag and /ask)
# -------------------------------------------------------------------

def test_rag_ask_alias(test_user):
    """POST /api/projects/{id}/ask works as an alias for /rag."""
    user_id, _, headers = test_user
    proj_id = create_mock_project(user_id, "Alias Test Project")

    res = client.post(
        f"/api/projects/{proj_id}/ask",
        headers=headers,
        json={"question": "How does this work?"},
    )
    # Should reach project index check and return 400 (not 404)
    assert res.status_code == 400


# -------------------------------------------------------------------
# Phase 43, 44, 48, 49: Live RAG Pipeline Tests on Project 416
# -------------------------------------------------------------------

def test_rag_live_jwt_question():
    """
    Live RAG pipeline test on existing project #416 (Phase 43):
    - Retrieves relevant chunks via FAISS
    - Converts to LangChain Documents
    - Invokes Gemma 2B
    - Returns grounded answer with authentic source citations
    """
    db = next(get_db())
    try:
        project = db.query(Project).filter(Project.id == 416).first()
        if not project:
            pytest.skip("Project 416 not found in local database")

        user = db.query(User).filter(User.id == project.user_id).first()
        proj_id = project.id
        user_id = user.id
        user_email = user.email
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id), "email": user_email})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        f"/api/projects/{proj_id}/rag",
        headers=headers,
        json={"question": "Where is JWT authentication implemented?", "top_k": 5},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["project_id"] == 416
    assert data["question"] == "Where is JWT authentication implemented?"
    assert len(data["answer"]) > 10
    assert len(data["sources"]) > 0

    # Verify source structure and metadata authenticity (Phase 49)
    top_source = data["sources"][0]
    assert "chunk_id" in top_source
    assert "file_path" in top_source
    assert "start_line" in top_source
    assert "end_line" in top_source
    assert "score" in top_source
    assert "auth.py" in top_source["file_path"]


def test_rag_live_insufficient_context():
    """
    Live RAG test for question not present in context (Phase 48):
    Gemma must report insufficient context rather than hallucinating Kubernetes files.
    """
    db = next(get_db())
    try:
        project = db.query(Project).filter(Project.id == 416).first()
        if not project:
            pytest.skip("Project 416 not found in local database")

        user = db.query(User).filter(User.id == project.user_id).first()
        proj_id = project.id
        user_id = user.id
        user_email = user.email
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id), "email": user_email})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        f"/api/projects/{proj_id}/rag",
        headers=headers,
        json={"question": "Where is the Kubernetes deployment configuration?", "top_k": 3},
    )
    assert res.status_code == 200
    data = res.json()

    answer_lower = data["answer"].lower()
    # Verify no hallucination of k8s manifests
    assert "deployment.yaml" not in answer_lower
    assert "k8s" not in answer_lower
    # Gemma indicates context lacks this information
    assert (
        "insufficient" in answer_lower
        or "does not" in answer_lower
        or "not found" in answer_lower
        or "cannot" in answer_lower
        or "no information" in answer_lower
    )


def test_rag_project_isolation_semantic(test_user):
    """
    Mandatory Phase 47 Project Isolation Test:
    Verify that Project A's code chunks are NEVER retrieved or returned
    when executing RAG queries for Project B.
    """
    user_id, token, headers = test_user
    db = next(get_db())

    try:
        # Create Project A with authentication code
        proj_a = Project(
            name="Project A Auth",
            original_filename="proj_a.zip",
            storage_path=f"storage/projects/iso_a_{uuid.uuid4().hex[:6]}",
            extracted_path=f"storage/projects/iso_a_{uuid.uuid4().hex[:6]}/extracted",
            file_count=1,
            lines_of_code=10,
            status="completed",
            user_id=user_id,
        )
        db.add(proj_a)

        # Create Project B with payment code
        proj_b = Project(
            name="Project B Payment",
            original_filename="proj_b.zip",
            storage_path=f"storage/projects/iso_b_{uuid.uuid4().hex[:6]}",
            extracted_path=f"storage/projects/iso_b_{uuid.uuid4().hex[:6]}/extracted",
            file_count=1,
            lines_of_code=10,
            status="completed",
            user_id=user_id,
        )
        db.add(proj_b)
        db.commit()
        db.refresh(proj_a)
        db.refresh(proj_b)

        # Add embedded chunk to Project A
        from app.services.embedding_service import embedding_service
        vec_auth = embedding_service.generate_query_embedding("def authenticate_user(): return True")
        chunk_a = CodeChunk(
            project_id=proj_a.id,
            chunk_id=f"p{proj_a.id}_auth_c1",
            file_path="auth/service.py",
            file_name="service.py",
            file_extension=".py",
            language="Python",
            source_type="code",
            start_line=1,
            end_line=10,
            symbol_name="authenticate_user",
            symbol_type="function",
            chunk_index=0,
            content_hash="hash_a",
            content="def authenticate_user():\n    '''Authenticates user credentials.'''\n    return True",
            embedding=vec_auth,
            embedding_status="completed",
            embedding_dimension=768,
        )
        db.add(chunk_a)

        # Add embedded chunk to Project B
        vec_pay = embedding_service.generate_query_embedding("def payment_service(): return 'paid'")
        chunk_b = CodeChunk(
            project_id=proj_b.id,
            chunk_id=f"p{proj_b.id}_payment_c1",
            file_path="billing/payment.py",
            file_name="payment.py",
            file_extension=".py",
            language="Python",
            source_type="code",
            start_line=1,
            end_line=10,
            symbol_name="payment_service",
            symbol_type="function",
            chunk_index=0,
            content_hash="hash_b",
            content="def payment_service():\n    '''Handles credit card payments.'''\n    return 'paid'",
            embedding=vec_pay,
            embedding_status="completed",
            embedding_dimension=768,
        )
        db.add(chunk_b)
        db.commit()

        # Build FAISS vector indexes for both
        faiss_service.build_project_index(db, proj_a)
        faiss_service.build_project_index(db, proj_b)

        # Query Project A for authentication
        res_a = client.post(
            f"/api/projects/{proj_a.id}/rag",
            headers=headers,
            json={"question": "Where is authentication implemented?", "top_k": 5},
        )
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert any("auth/service.py" in s["file_path"] for s in data_a["sources"])
        assert all(s["chunk_id"].startswith(f"p{proj_a.id}_") for s in data_a["sources"])

        # Query Project B for authentication
        res_b = client.post(
            f"/api/projects/{proj_b.id}/rag",
            headers=headers,
            json={"question": "Where is authentication implemented?", "top_k": 5},
        )
        assert res_b.status_code == 200
        data_b = res_b.json()

        # STRICT ISOLATION ASSERTIONS:
        # None of Project A's chunk IDs or file paths should appear in Project B's sources!
        for s in data_b["sources"]:
            assert not s["chunk_id"].startswith(f"p{proj_a.id}_")
            assert s["file_path"] != "auth/service.py"
            assert s["symbol_name"] != "authenticate_user"

    finally:
        db.close()
