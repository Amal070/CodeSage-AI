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
from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.services.faiss_service import FaissService, faiss_service

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a unique test user and return (user_id, token, headers)."""
    unique_email = f"faiss_tester_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="FAISS Tester",
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
    unique_email = f"second_faiss_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Second FAISS Tester",
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


def create_zip_in_memory(files_dict: dict) -> io.BytesIO:
    """Helper to construct an in-memory ZIP archive."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, content in files_dict.items():
            if isinstance(content, str):
                zf.writestr(file_path, content.encode("utf-8"))
            else:
                zf.writestr(file_path, content)
    zip_buffer.seek(0)
    return zip_buffer


@pytest.fixture
def sample_indexed_and_embedded_project(test_user):
    """
    Creates, indexes (Day 10), and embeds (Day 11) a sample project with:
    - Auth & JWT logic in backend/app/auth.py
    - PostgreSQL database engine in backend/app/database.py
    - React Dashboard UI in frontend/src/Dashboard.jsx
    """
    user_id, token, headers = test_user
    files = {
        "backend/app/auth.py": (
            "import jwt\n"
            "from datetime import datetime, timedelta\n\n"
            "SECRET_KEY = 'super-secret-jwt-key'\n\n"
            "def create_access_token(data: dict, expires_delta: timedelta = None) -> str:\n"
            "    '''Generates signed JWT access token for user authentication.'''\n"
            "    to_encode = data.copy()\n"
            "    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))\n"
            "    to_encode.update({'exp': expire})\n"
            "    return jwt.encode(to_encode, SECRET_KEY, algorithm='HS256')\n\n"
            "def verify_jwt_token(token: str) -> dict:\n"
            "    '''Decodes and validates JWT bearer authentication token.'''\n"
            "    return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])\n"
        ),
        "backend/app/database.py": (
            "from sqlalchemy import create_engine\n"
            "from sqlalchemy.orm import sessionmaker\n\n"
            "DATABASE_URL = 'postgresql+psycopg2://postgres:secret@localhost:5432/codesage_db'\n\n"
            "engine = create_engine(DATABASE_URL, pool_pre_ping=True)\n"
            "SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n\n"
            "def get_db_connection():\n"
            "    '''Yields transactional PostgreSQL database session.'''\n"
            "    db = SessionLocal()\n"
            "    try:\n"
            "        yield db\n"
            "    finally:\n"
            "        db.close()\n"
        ),
        "frontend/src/Dashboard.jsx": (
            "import React from 'react';\n\n"
            "export function DashboardView({ user, projects }) {\n"
            "    return (\n"
            "        <div className='dashboard-container'>\n"
            "            <h1>Welcome to CodeSage AI Dashboard</h1>\n"
            "            <p>User: {user.name}</p>\n"
            "            <p>Active Projects: {projects.length}</p>\n"
            "        </div>\n"
            "    );\n"
            "}\n"
        ),
    }

    zip_buf = create_zip_in_memory(files)
    upload_res = client.post(
        "/api/projects/upload",
        files={"file": ("project.zip", zip_buf, "application/zip")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    project_id = upload_res.json()["project"]["id"]

    # Day 10 Indexing
    index_res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert index_res.status_code == 200
    assert index_res.json()["total_chunks"] > 0

    # Day 11 Embedding Generation
    embed_res = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert embed_res.status_code == 200
    assert embed_res.json()["embedded_chunks"] > 0

    return project_id


# --------------------------------------------------------------------------
# Authentication and Tenancy Tests (Phases 23, 41)
# --------------------------------------------------------------------------

def test_unauthenticated_search_rejected():
    """Vector index and search endpoints must reject unauthenticated requests."""
    res_index = client.post("/api/projects/1/vector-index")
    assert res_index.status_code == 401

    res_search = client.get("/api/projects/1/search?query=test")
    assert res_search.status_code == 401


def test_unauthorized_search_rejected(test_user, second_user, sample_indexed_and_embedded_project):
    """User cannot build index or search another user's project."""
    project_id = sample_indexed_and_embedded_project
    _, _, second_headers = second_user

    # Attempt to build vector index
    res_index = client.post(f"/api/projects/{project_id}/vector-index", headers=second_headers)
    assert res_index.status_code == 404

    # Attempt to search
    res_search = client.get(
        f"/api/projects/{project_id}/search?query=auth", headers=second_headers
    )
    assert res_search.status_code == 404


def test_build_vector_index_without_embeddings_rejected(test_user):
    """Building vector index before generating embeddings must return clear 400 error (Phase 12)."""
    _, _, headers = test_user
    files = {"src/test.py": "def foo(): return 1"}
    zip_buf = create_zip_in_memory(files)
    upload_res = client.post(
        "/api/projects/upload",
        files={"file": ("unembedded.zip", zip_buf, "application/zip")},
        headers=headers,
    )
    project_id = upload_res.json()["project"]["id"]

    # Index project (Day 10) but DO NOT generate embeddings (skip Day 11)
    client.post(f"/api/projects/{project_id}/index", headers=headers)

    # Attempt to build vector index
    res = client.post(f"/api/projects/{project_id}/vector-index", headers=headers)
    assert res.status_code == 400
    assert "Generate embeddings before building the vector index" in res.json()["detail"]


# --------------------------------------------------------------------------
# FAISS Vector Index Construction & Persistence (Phases 5, 6, 7, 9, 10, 11)
# --------------------------------------------------------------------------

def test_build_vector_index_success(test_user, sample_indexed_and_embedded_project):
    """
    Verifies building FAISS vector index:
    - IndexFlatIP constructed with dimension 768.
    - index.faiss and mapping.json created on disk.
    - Vector count matches embedded chunks count.
    """
    user_id, token, headers = test_user
    project_id = sample_indexed_and_embedded_project

    # Status before build should be 'not_built'
    status_before = client.get(f"/api/projects/{project_id}/vector-index/status", headers=headers)
    assert status_before.status_code == 200
    assert status_before.json()["status"] == "not_built"

    # Build vector index
    res = client.post(f"/api/projects/{project_id}/vector-index", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == project_id
    assert data["status"] == "completed"
    assert data["indexed_vectors"] > 0
    assert data["embedding_dimension"] == 768
    assert data["index_type"] == "IndexFlatIP"
    assert data["metric"] == "cosine_similarity"

    # Verify files on disk (Phases 8 & 9)
    index_path, mapping_path = faiss_service.get_index_file_paths(project_id)
    assert index_path.exists()
    assert mapping_path.exists()

    # Status after build should be 'ready'
    status_after = client.get(f"/api/projects/{project_id}/vector-index/status", headers=headers)
    assert status_after.status_code == 200
    s_data = status_after.json()
    assert s_data["status"] == "ready"
    assert s_data["indexed_vectors"] == data["indexed_vectors"]
    assert s_data["embedding_dimension"] == 768


# --------------------------------------------------------------------------
# Semantic Code Search Relevance & Accuracy (Phases 16, 17, 18, 20, 21, 37)
# --------------------------------------------------------------------------

def test_semantic_search_retrieval_relevance(test_user, sample_indexed_and_embedded_project):
    """
    Natural language query for JWT authentication must return auth.py
    with high cosine similarity score (score > 0.6).
    """
    user_id, token, headers = test_user
    project_id = sample_indexed_and_embedded_project

    # Ensure vector index is built
    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # Search: "Where is JWT authentication implemented?"
    query = "Where is JWT authentication implemented?"
    res = client.get(f"/api/projects/{project_id}/search?query={query}&top_k=5", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["project_id"] == project_id
    assert data["query"] == query
    assert data["total_results"] > 0
    assert len(data["results"]) <= 5

    # Top result must be auth.py containing create_access_token or verify_jwt_token
    top_result = data["results"][0]
    assert "auth.py" in top_result["metadata"]["file_path"]
    assert top_result["score"] > 0.6
    assert any(term in top_result["content"] for term in ["create_access_token", "jwt", "SECRET_KEY"])

    # Verify metadata fields are complete
    assert top_result["metadata"]["file_name"] == "auth.py"
    assert top_result["metadata"]["language"] == "Python"
    assert top_result["metadata"]["start_line"] >= 1
    assert top_result["metadata"]["end_line"] >= top_result["metadata"]["start_line"]


def test_search_database_query_relevance(test_user, sample_indexed_and_embedded_project):
    """Query for PostgreSQL connection must return database.py."""
    user_id, token, headers = test_user
    project_id = sample_indexed_and_embedded_project

    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # Search: "How does the application connect to PostgreSQL database?"
    query = "How does the application connect to PostgreSQL database?"
    res = client.get(f"/api/projects/{project_id}/search?query={query}&top_k=5", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_results"] > 0

    top_result = data["results"][0]
    assert "database.py" in top_result["metadata"]["file_path"]
    assert top_result["score"] > 0.6
    assert "postgresql" in top_result["content"].lower() or "sessionmaker" in top_result["content"].lower()


# --------------------------------------------------------------------------
# Top-K Limits and Input Validation (Phases 19, 25, 26, 39)
# --------------------------------------------------------------------------

def test_top_k_limits(test_user, sample_indexed_and_embedded_project):
    """Validates top_k=1, top_k=3, and rejection of out-of-bounds top_k."""
    user_id, token, headers = test_user
    project_id = sample_indexed_and_embedded_project

    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # top_k = 1
    res1 = client.get(f"/api/projects/{project_id}/search?query=jwt&top_k=1", headers=headers)
    assert res1.status_code == 200
    assert len(res1.json()["results"]) == 1

    # top_k = 2
    res2 = client.get(f"/api/projects/{project_id}/search?query=jwt&top_k=2", headers=headers)
    assert res2.status_code == 200
    assert len(res2.json()["results"]) == 2

    # Out of bounds: top_k=0
    res_zero = client.get(f"/api/projects/{project_id}/search?query=jwt&top_k=0", headers=headers)
    assert res_zero.status_code in (400, 422)

    # Out of bounds: top_k > 20
    res_large = client.get(f"/api/projects/{project_id}/search?query=jwt&top_k=25", headers=headers)
    assert res_large.status_code in (400, 422)


def test_empty_query_rejected(test_user, sample_indexed_and_embedded_project):
    """Empty or whitespace-only query must be rejected with 400 (Phase 26)."""
    user_id, token, headers = test_user
    project_id = sample_indexed_and_embedded_project

    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    res = client.get(f"/api/projects/{project_id}/search?query=%20%20%20", headers=headers)
    assert res.status_code == 400
    assert "Search query cannot be empty" in res.json()["detail"]


# --------------------------------------------------------------------------
# Project Isolation & Tenancy Security (Phases 23, 24, 40)
# --------------------------------------------------------------------------

def test_project_isolation(test_user):
    """
    Creates Project A (Calculator) and Project B (Auth).
    Searching Project A must NEVER return Project B chunks and vice-versa.
    """
    user_id, token, headers = test_user

    # Project A: Calculator
    zip_a = create_zip_in_memory({"calc.py": "def calculate_sum(a, b):\n    return a + b\n"})
    up_a = client.post("/api/projects/upload", files={"file": ("a.zip", zip_a, "application/zip")}, headers=headers)
    pid_a = up_a.json()["project"]["id"]
    client.post(f"/api/projects/{pid_a}/index", headers=headers)
    client.post(f"/api/projects/{pid_a}/embeddings", headers=headers)
    client.post(f"/api/projects/{pid_a}/vector-index", headers=headers)

    # Project B: JWT Auth
    zip_b = create_zip_in_memory({"auth.py": "def authenticate_jwt_user(token):\n    return verify(token)\n"})
    up_b = client.post("/api/projects/upload", files={"file": ("b.zip", zip_b, "application/zip")}, headers=headers)
    pid_b = up_b.json()["project"]["id"]
    client.post(f"/api/projects/{pid_b}/index", headers=headers)
    client.post(f"/api/projects/{pid_b}/embeddings", headers=headers)
    client.post(f"/api/projects/{pid_b}/vector-index", headers=headers)

    # Search Project A for JWT authentication -> results must ONLY be from Project A
    res_a = client.get(f"/api/projects/{pid_a}/search?query=jwt+authentication&top_k=5", headers=headers)
    assert res_a.status_code == 200
    for item in res_a.json()["results"]:
        assert "auth.py" not in item["metadata"]["file_path"]
        assert "calc.py" in item["metadata"]["file_path"]

    # Search Project B for sum -> results must ONLY be from Project B
    res_b = client.get(f"/api/projects/{pid_b}/search?query=calculate+sum&top_k=5", headers=headers)
    assert res_b.status_code == 200
    for item in res_b.json()["results"]:
        assert "calc.py" not in item["metadata"]["file_path"]
        assert "auth.py" in item["metadata"]["file_path"]


# --------------------------------------------------------------------------
# Persistence Verification After Reload (Phase 36)
# --------------------------------------------------------------------------

def test_index_persistence_after_reload(test_user, sample_indexed_and_embedded_project):
    """
    Verifies that a fresh FaissService instance loads index.faiss and mapping.json
    from disk and executes identical semantic retrieval without re-indexing.
    """
    user_id, token, headers = test_user
    project_id = sample_indexed_and_embedded_project

    # Build index
    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # Perform initial search
    res1 = client.get(f"/api/projects/{project_id}/search?query=create+access+token&top_k=3", headers=headers)
    assert res1.status_code == 200
    top_chunk1 = res1.json()["results"][0]["chunk_id"]

    # Create completely new FaissService reading from disk (simulating backend reboot)
    fresh_faiss_service = FaissService()
    db = next(get_db())
    try:
        project = db.get(Project, project_id)
        results = fresh_faiss_service.search(db, project, "create access token", top_k=3)
        assert len(results) > 0
        assert results[0].chunk_id == top_chunk1
    finally:
        db.close()
