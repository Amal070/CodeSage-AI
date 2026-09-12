import io
import math
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.services.embedding_service import embedding_service

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a unique test user and return (user_id, token, headers)."""
    unique_email = f"embedder_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Embedding Tester",
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
    unique_email = f"second_embedder_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Second Embedder",
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
def sample_multi_lang_project(test_user):
    """Creates and indexes a multi-language project (Python, JS, Java)."""
    user_id, token, headers = test_user
    files = {
        "src/calculator.py": (
            "def add(a: int, b: int) -> int:\n"
            "    '''Add two numbers.'''\n"
            "    return a + b\n\n"
            "def multiply(a: int, b: int) -> int:\n"
            "    '''Multiply two numbers.'''\n"
            "    return a * b\n"
        ),
        "src/utils.js": (
            "function formatGreeting(name) {\n"
            "    return `Hello, ${name}!`;\n"
            "}\n\n"
            "export { formatGreeting };\n"
        ),
        "src/Main.java": (
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        System.out.println(\"Hello CodeSage\");\n"
            "    }\n"
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

    # Index project with Day 10
    index_res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert index_res.status_code == 200
    assert index_res.json()["status"] == "completed"
    assert index_res.json()["total_chunks"] > 0

    return project_id


# --------------------------------------------------------------------------
# Authentication and Tenancy Tests (Phases 30 & 33)
# --------------------------------------------------------------------------

def test_unauthenticated_embedding_rejected():
    """Embedding endpoint must require JWT authentication."""
    res = client.post("/api/projects/1/embeddings")
    assert res.status_code == 401


def test_unauthorized_embedding_rejected(test_user, second_user, sample_multi_lang_project):
    """User cannot generate embeddings for another user's project."""
    project_id = sample_multi_lang_project
    _, _, second_headers = second_user

    res = client.post(f"/api/projects/{project_id}/embeddings", headers=second_headers)
    assert res.status_code == 404


def test_unindexed_project_rejected(test_user):
    """Embedding generation before code indexing must return clear 400 error."""
    _, _, headers = test_user
    files = {"src/app.py": "print('hello')"}
    zip_buf = create_zip_in_memory(files)
    upload_res = client.post(
        "/api/projects/upload",
        files={"file": ("unindexed.zip", zip_buf, "application/zip")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    project_id = upload_res.json()["project"]["id"]

    # Attempt embedding generation before indexing (Phase 20)
    res = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert res.status_code == 400
    assert "Run code indexing first" in res.json()["detail"]


def test_empty_project_embedding(test_user):
    """Gracefully handles indexed project with no indexable code chunks (Phase 21)."""
    _, _, headers = test_user
    # Binary file that is skipped by Day 10 indexer, resulting in 0 code chunks
    files = {"assets/logo.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"}
    zip_buf = create_zip_in_memory(files)
    upload_res = client.post(
        "/api/projects/upload",
        files={"file": ("empty_chunks.zip", zip_buf, "application/zip")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    project_id = upload_res.json()["project"]["id"]

    # Index project with Day 10 (yields 0 chunks)
    index_res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert index_res.status_code == 200
    assert index_res.json()["total_chunks"] == 0

    res = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["total_chunks"] == 0
    assert data["embedded_chunks"] == 0
    assert data["skipped_chunks"] == 0
    assert data["failed_chunks"] == 0


# --------------------------------------------------------------------------
# Embedding Generation & Vector Verification (Phases 11, 12, 19, 34)
# --------------------------------------------------------------------------

def test_embedding_generation_success(test_user, sample_multi_lang_project):
    """
    Verifies full embedding generation:
    - 768-dimensional vectors from Nomic Embed Text.
    - Persistent storage in PostgreSQL.
    - L2 normalization.
    - Association with project, chunk_id, content_hash.
    """
    user_id, token, headers = test_user
    project_id = sample_multi_lang_project

    res = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["project_id"] == project_id
    assert data["status"] == "completed"
    assert data["total_chunks"] > 0
    assert data["embedded_chunks"] == data["total_chunks"]
    assert data["skipped_chunks"] == 0
    assert data["failed_chunks"] == 0
    assert data["embedding_dimension"] == 768
    assert "nomic" in data["model"].lower()

    # Verify directly in PostgreSQL
    db = next(get_db())
    try:
        chunks = list(
            db.scalars(
                select(CodeChunk).where(CodeChunk.project_id == project_id)
            ).all()
        )
        assert len(chunks) == data["total_chunks"]
        for c in chunks:
            assert c.embedding is not None
            assert len(c.embedding) == 768
            assert c.embedding_status == "completed"
            assert c.embedding_dimension == 768
            assert c.embedded_hash == c.content_hash

            # Verify L2 normalization: sum of squares should be ~1.0 (Phase 11)
            norm = math.sqrt(sum(x * x for x in c.embedding))
            assert pytest.approx(norm, abs=1e-3) == 1.0
    finally:
        db.close()


# --------------------------------------------------------------------------
# Idempotency and Re-generation Tests (Phases 17, 18, 36)
# --------------------------------------------------------------------------

def test_idempotent_reembedding(test_user, sample_multi_lang_project):
    """Running embedding generation a second time must skip all unchanged chunks."""
    user_id, token, headers = test_user
    project_id = sample_multi_lang_project

    # First run: generates embeddings
    res1 = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["embedded_chunks"] == data1["total_chunks"]
    assert data1["skipped_chunks"] == 0

    # Second run: unchanged chunks must be skipped (Phase 18)
    res2 = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total_chunks"] == data1["total_chunks"]
    assert data2["embedded_chunks"] == 0
    assert data2["skipped_chunks"] == data1["total_chunks"]
    assert data2["failed_chunks"] == 0


def test_changed_chunk_reembedding(test_user, sample_multi_lang_project):
    """Modifying one chunk's content hash triggers re-embedding for only that chunk."""
    user_id, token, headers = test_user
    project_id = sample_multi_lang_project

    # Initial embedding run
    res1 = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert res1.status_code == 200
    total = res1.json()["total_chunks"]

    # Artificially alter one chunk's content_hash to simulate file edit & re-index
    db = next(get_db())
    try:
        first_chunk = db.scalars(
            select(CodeChunk).where(CodeChunk.project_id == project_id)
        ).first()
        first_chunk.content = "def updated_function(): return 'changed'"
        first_chunk.content_hash = "different_hash_from_edit_12345678"
        db.commit()
    finally:
        db.close()

    # Re-run embeddings: only the changed chunk should be re-embedded
    res2 = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total_chunks"] == total
    assert data2["embedded_chunks"] == 1
    assert data2["skipped_chunks"] == total - 1
    assert data2["failed_chunks"] == 0


# --------------------------------------------------------------------------
# Embedding Status Endpoint Test (Phase 16)
# --------------------------------------------------------------------------

def test_embedding_status_endpoint(test_user, sample_multi_lang_project):
    """GET /api/projects/{id}/embeddings/status returns accurate counts and readiness."""
    user_id, token, headers = test_user
    project_id = sample_multi_lang_project

    # Before generating embeddings
    status_res1 = client.get(f"/api/projects/{project_id}/embeddings/status", headers=headers)
    assert status_res1.status_code == 200
    s1 = status_res1.json()
    assert s1["status"] in ("not_generated", "pending")
    assert s1["embedded_chunks"] == 0

    # Generate embeddings
    client.post(f"/api/projects/{project_id}/embeddings", headers=headers)

    # After generating embeddings
    status_res2 = client.get(f"/api/projects/{project_id}/embeddings/status", headers=headers)
    assert status_res2.status_code == 200
    s2 = status_res2.json()
    assert s2["status"] == "ready"
    assert s2["total_chunks"] > 0
    assert s2["embedded_chunks"] == s2["total_chunks"]
    assert s2["embedding_dimension"] == 768
    assert s2["last_embedded_at"] is not None


# --------------------------------------------------------------------------
# Multi-Language Verification (Phase 37)
# --------------------------------------------------------------------------

def test_multilanguage_embeddings(test_user, sample_multi_lang_project):
    """Verifies that chunks for Python, JS, and Java receive valid embeddings."""
    user_id, token, headers = test_user
    project_id = sample_multi_lang_project

    client.post(f"/api/projects/{project_id}/embeddings", headers=headers)

    db = next(get_db())
    try:
        py_chunks = list(
            db.scalars(
                select(CodeChunk).where(
                    CodeChunk.project_id == project_id,
                    CodeChunk.language == "Python",
                )
            ).all()
        )
        js_chunks = list(
            db.scalars(
                select(CodeChunk).where(
                    CodeChunk.project_id == project_id,
                    CodeChunk.language == "JavaScript",
                )
            ).all()
        )
        java_chunks = list(
            db.scalars(
                select(CodeChunk).where(
                    CodeChunk.project_id == project_id,
                    CodeChunk.language == "Java",
                )
            ).all()
        )

        assert len(py_chunks) > 0
        assert len(js_chunks) > 0
        assert len(java_chunks) > 0

        for c in py_chunks + js_chunks + java_chunks:
            assert c.embedding_status == "completed"
            assert len(c.embedding) == 768
    finally:
        db.close()
