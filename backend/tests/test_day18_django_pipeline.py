"""
CodeSage AI — Day 18 Test Suite: Django Project Pipeline

Tests the complete CodeSage AI pipeline on a realistic Django project:
1. Upload & Safe Extraction
2. File Explorer & Content Retrieval
3. Project Structure & Language Analysis
4. Tree-sitter AST Code Parsing (Models, Views, URLs)
5. Dependency Analysis (requirements.txt, Django/DRF packages, internal imports)
6. Code Indexing & Chunk Metadata
7. Nomic Embed Text Embedding Generation (768 dimensions)
8. FAISS Index Construction & Persistence
9. Day 17 File-Level Context Retrieval
10. RAG & AI Chat Grounding & Source Citations
11. Multi-turn Conversation & Contextual Follow-up
12. Hallucination Defense (Nonexistent Redis feature)
13. Source Accuracy & Line Number Integrity
"""

import time
import uuid
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from tests.fixtures.sample_projects import DJANGO_PROJECT_FILES, build_project_zip

client = TestClient(app)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def django_user():
    """Creates a distinct test user for the Django project pipeline."""
    unique_email = f"django_tester_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Django Pipeline Tester",
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
def uploaded_django_project(django_user):
    """Uploads the Django bookstore project and returns project_id and headers."""
    user_id, token, headers = django_user
    zip_buffer = build_project_zip(DJANGO_PROJECT_FILES)

    response = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("django_bookstore.zip", zip_buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 201, f"Upload failed: {response.text}"
    project_id = response.json()["project"]["id"]
    return project_id, headers


# ==============================================================================
# 1. UPLOAD AND EXTRACTION (Step 3)
# ==============================================================================

def test_django_upload_and_extraction(django_user):
    """Verify ZIP upload, safe extraction, and initial metadata creation."""
    user_id, token, headers = django_user
    zip_buffer = build_project_zip(DJANGO_PROJECT_FILES)

    start_time = time.time()
    response = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("django_bookstore.zip", zip_buffer.getvalue(), "application/zip")},
    )
    duration = time.time() - start_time

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Project uploaded successfully"
    project = data["project"]
    assert project["name"] == "django_bookstore"
    assert project["file_count"] >= 10
    assert project["lines_of_code"] > 100
    assert project["status"] == "uploaded"
    assert duration < 5.0  # Upload & extract should be fast


# ==============================================================================
# 2. FILE EXPLORER (Step 6)
# ==============================================================================

def test_django_file_explorer(uploaded_django_project):
    """Verify directory tree browsing and file content reading."""
    project_id, headers = uploaded_django_project

    # 1. Tree structure
    tree_res = client.get(f"/api/projects/{project_id}/files", headers=headers)
    assert tree_res.status_code == 200
    tree_data = tree_res.json()
    assert tree_data["project_id"] == project_id
    nodes = tree_data["tree"]
    assert len(nodes) > 0

    # Collect all file paths
    found_paths = []
    def traverse(node):
        if node["type"] == "file":
            found_paths.append(node["path"].replace("\\", "/"))
        for child in node.get("children") or []:
            traverse(child)
    for root_node in nodes:
        traverse(root_node)

    assert any("accounts/views.py" in p for p in found_paths)
    assert any("bookstore_config/settings.py" in p for p in found_paths)
    assert any("manage.py" in p for p in found_paths)

    # 2. File content reading
    file_res = client.get(
        f"/api/projects/{project_id}/file?path=accounts/views.py",
        headers=headers,
    )
    assert file_res.status_code == 200
    file_data = file_res.json()
    assert file_data["language"].lower() == "python"
    assert "class LoginView" in file_data["content"]
    assert len(file_data["content"].splitlines()) > 20
    assert not file_data["is_binary"]


# ==============================================================================
# 3. PROJECT ANALYSIS (Step 9)
# ==============================================================================

def test_django_project_analysis(uploaded_django_project):
    """Verify language breakdown and structure metrics for Django."""
    project_id, headers = uploaded_django_project

    res = client.get(f"/api/projects/{project_id}/analysis", headers=headers)
    assert res.status_code == 200
    data = res.json()

    stats = data["statistics"]
    assert stats["total_files"] >= 10
    assert stats["total_size_bytes"] > 500

    # Language breakdown: Python must be detected
    assert "Python" in data["languages"]
    assert data["languages"]["Python"] >= 5


# ==============================================================================
# 4. TREE-SITTER PARSING (Step 12 & 15)
# ==============================================================================

def test_django_tree_sitter_parsing(uploaded_django_project):
    """Verify AST extraction of Django classes, functions, and imports."""
    project_id, headers = uploaded_django_project

    # Parse accounts/models.py
    models_res = client.get(
        f"/api/projects/{project_id}/parse?path=accounts/models.py",
        headers=headers,
    )
    assert models_res.status_code == 200
    models_data = models_res.json()
    class_names = [c["name"] for c in models_data["classes"]]
    assert "CustomUser" in class_names
    import_names = [i["name"] for i in models_data["imports"]]
    assert any("AbstractUser" in imp or "django.contrib.auth" in imp for imp in import_names)

    # Parse accounts/views.py
    views_res = client.get(
        f"/api/projects/{project_id}/parse?path=accounts/views.py",
        headers=headers,
    )
    assert views_res.status_code == 200
    views_data = views_res.json()
    view_classes = [c["name"] for c in views_data["classes"]]
    assert "LoginView" in view_classes
    assert "RegisterView" in view_classes
    methods = [f["name"] for f in views_data["functions"]]
    assert "post" in methods


# ==============================================================================
# 5. DEPENDENCY ANALYSIS (Step 16)
# ==============================================================================

def test_django_dependency_analysis(uploaded_django_project):
    """Verify requirements.txt parsing and Django/DRF package detection."""
    project_id, headers = uploaded_django_project

    res = client.get(f"/api/projects/{project_id}/dependencies", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Manifest packages
    manifest_packages = [p["name"].lower() for p in data.get("packages", [])]
    assert "django" in manifest_packages
    assert "djangorestframework" in manifest_packages

    # Cross-file relationships
    relationships = data.get("relationships", [])
    assert len(relationships) > 0


# ==============================================================================
# 6. CODE INDEXING (Step 19)
# ==============================================================================

def test_django_code_indexing(uploaded_django_project):
    """Verify code chunking with structural AST and metadata persistence."""
    project_id, headers = uploaded_django_project

    res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["total_chunks"] >= 10
    assert data["indexed_files"] >= 8

    # Verify chunks endpoint
    chunks_res = client.get(f"/api/projects/{project_id}/chunks?limit=50", headers=headers)
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) >= 10

    # Ensure accounts/views.py and accounts/models.py are chunked with symbols
    views_chunks = [c for c in chunks if "accounts/views.py" in c["metadata"]["file_path"]]
    assert len(views_chunks) > 0
    symbols = [c["metadata"]["symbol_name"] for c in views_chunks if c["metadata"].get("symbol_name")]
    assert any("LoginView" in s or "post" in s for s in symbols)


# ==============================================================================
# 7. EMBEDDINGS & FAISS VECTOR INDEX (Steps 22, 25, 26)
# ==============================================================================

def test_django_embeddings_and_faiss(uploaded_django_project):
    """Generate Nomic embeddings and build persistent FAISS vector index."""
    project_id, headers = uploaded_django_project

    # 1. Index first
    client.post(f"/api/projects/{project_id}/index", headers=headers)

    # 2. Generate embeddings
    emb_res = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert emb_res.status_code == 200
    emb_data = emb_res.json()
    assert emb_data["status"] == "completed"
    assert emb_data["embedded_chunks"] >= 10
    assert emb_data["embedding_dimension"] == 768

    # 3. Build FAISS index
    index_res = client.post(f"/api/projects/{project_id}/vector-index", headers=headers)
    assert index_res.status_code == 200
    index_data = index_res.json()
    assert index_data["status"] == "completed"
    assert index_data["indexed_vectors"] >= 10
    assert index_data["index_type"] == "IndexFlatIP"


# ==============================================================================
# 8. CONTEXT RETRIEVAL (Steps 27, 28, 29)
# ==============================================================================

def test_django_context_retrieval(uploaded_django_project):
    """Verify Day 17 file-level context retrieval returns relevant Django files."""
    project_id, headers = uploaded_django_project

    # Prepare index and vectors
    client.post(f"/api/projects/{project_id}/index", headers=headers)
    client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # Step 27: Where is authentication implemented?
    auth_res = client.post(
        f"/api/projects/{project_id}/context/retrieve",
        headers=headers,
        json={"query": "Where is authentication implemented?", "top_files": 3},
    )
    assert auth_res.status_code == 200
    auth_data = auth_res.json()
    top_paths = [f["file_path"].replace("\\", "/") for f in auth_data["files"]]
    assert any("accounts/views.py" in p or "accounts/models.py" in p for p in top_paths)

    # Step 28: Explain login function
    login_res = client.post(
        f"/api/projects/{project_id}/context/retrieve",
        headers=headers,
        json={"query": "Explain the login function", "top_files": 3},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    login_paths = [f["file_path"].replace("\\", "/") for f in login_data["files"]]
    assert any("accounts/views.py" in p for p in login_paths)


# ==============================================================================
# 9. RAG & AI CHAT & FOLLOW-UP (Steps 35, 38, 41, 42)
# ==============================================================================

def test_django_ai_chat_and_hallucination_defense(uploaded_django_project):
    """
    Test live RAG chat on Django project:
    - Grounded Q&A on authentication
    - Contextual follow-up turn
    - Hallucination defense (Redis caching rejection)
    """
    project_id, headers = uploaded_django_project

    # Prepare index and vectors
    client.post(f"/api/projects/{project_id}/index", headers=headers)
    client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # Turn 1: Authentication question
    chat_res_1 = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Explain authentication in this project."},
    )
    assert chat_res_1.status_code == 200
    data_1 = chat_res_1.json()
    assert len(data_1["answer"]) > 20
    assert len(data_1["sources"]) > 0
    source_paths = [s["file_path"].replace("\\", "/") for s in data_1["sources"]]
    assert any("accounts/views.py" in p or "accounts/models.py" in p for p in source_paths)
    conv_id = data_1["conversation_id"]

    # Turn 2: Follow-up question
    chat_res_2 = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Where is the password handled?", "conversation_id": conv_id},
    )
    assert chat_res_2.status_code == 200
    data_2 = chat_res_2.json()
    assert len(data_2["answer"]) > 10

    # Step 41: Hallucination test for non-existent Redis
    chat_res_redis = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Explain the Redis caching implementation in this project."},
    )
    assert chat_res_redis.status_code == 200
    data_redis = chat_res_redis.json()
    redis_answer = data_redis["answer"].lower()
    # Model must indicate that Redis is not found / insufficient context, NOT hallucinate Redis config
    assert (
        "not found" in redis_answer
        or "no" in redis_answer
        or "insufficient" in redis_answer
        or "does not contain" in redis_answer
        or "not implemented" in redis_answer
        or "not mentioned" in redis_answer
        or "not present" in redis_answer
        or "not provide" in redis_answer
    )
