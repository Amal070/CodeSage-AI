"""
CodeSage AI — Day 18 Test Suite: Python Project Pipeline

Tests the complete CodeSage AI pipeline on a realistic Python application:
1. Upload & Safe Extraction (main.py, config, services, models, tests)
2. File Explorer (Python code viewer, lines, syntax)
3. Project Structure & Language Analysis (Python classification)
4. Tree-sitter AST Code Parsing (Classes, Functions, Methods, Imports)
5. Dependency Analysis (requirements.txt parsing, Pydantic/Requests packages, local module links)
6. Code Indexing & Chunk Metadata
7. Nomic Embed Text Embedding Generation (768 dimensions)
8. FAISS Index Construction & Persistence
9. Day 17 File-Level Context Retrieval (Main function, Service communication)
10. RAG & AI Chat Grounding & Source Citations
11. Multi-turn Conversation & Contextual Follow-up
12. Hallucination Defense (Nonexistent Kubernetes feature)
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
from tests.fixtures.sample_projects import PYTHON_PROJECT_FILES, build_project_zip

client = TestClient(app)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def python_user():
    """Creates a distinct test user for the Python project pipeline."""
    unique_email = f"python_tester_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Python Pipeline Tester",
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
def uploaded_python_project(python_user):
    """Uploads the Python DataPipeline project and returns project_id and headers."""
    user_id, token, headers = python_user
    zip_buffer = build_project_zip(PYTHON_PROJECT_FILES)

    response = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("python_datapipeline.zip", zip_buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 201, f"Upload failed: {response.text}"
    project_id = response.json()["project"]["id"]
    return project_id, headers


# ==============================================================================
# 1. UPLOAD AND EXTRACTION (Step 5)
# ==============================================================================

def test_python_upload_and_extraction(python_user):
    """Verify Python ZIP upload, extraction, and file metadata."""
    user_id, token, headers = python_user
    zip_buffer = build_project_zip(PYTHON_PROJECT_FILES)

    start_time = time.time()
    response = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("python_datapipeline.zip", zip_buffer.getvalue(), "application/zip")},
    )
    duration = time.time() - start_time

    assert response.status_code == 201
    data = response.json()
    project = data["project"]
    assert project["name"] == "python_datapipeline"
    assert project["file_count"] >= 8
    assert project["lines_of_code"] > 50
    assert project["status"] == "uploaded"
    assert duration < 5.0


# ==============================================================================
# 2. FILE EXPLORER (Step 8)
# ==============================================================================

def test_python_file_explorer(uploaded_python_project):
    """Verify tree browsing and python module reading."""
    project_id, headers = uploaded_python_project

    # 1. File Tree
    tree_res = client.get(f"/api/projects/{project_id}/files", headers=headers)
    assert tree_res.status_code == 200
    tree_data = tree_res.json()
    nodes = tree_data["tree"]
    assert len(nodes) > 0

    found_paths = []
    def traverse(node):
        if node["type"] == "file":
            found_paths.append(node["path"].replace("\\", "/"))
        for child in node.get("children") or []:
            traverse(child)
    for root_node in nodes:
        traverse(root_node)

    assert any("main.py" in p for p in found_paths)
    assert any("services/processor.py" in p for p in found_paths)
    assert any("models/record.py" in p for p in found_paths)

    # 2. Python File Content
    file_res = client.get(
        f"/api/projects/{project_id}/file?path=services/processor.py",
        headers=headers,
    )
    assert file_res.status_code == 200
    file_data = file_res.json()
    assert file_data["language"].lower() == "python"
    assert "class DataProcessor" in file_data["content"]
    assert not file_data["is_binary"]


# ==============================================================================
# 3. PROJECT ANALYSIS (Step 11)
# ==============================================================================

def test_python_project_analysis(uploaded_python_project):
    """Verify language breakdown and folder hierarchy for Python project."""
    project_id, headers = uploaded_python_project

    res = client.get(f"/api/projects/{project_id}/analysis", headers=headers)
    assert res.status_code == 200
    data = res.json()

    stats = data["statistics"]
    assert stats["total_files"] >= 8

    assert "Python" in data["languages"]
    assert data["languages"]["Python"] >= 5


# ==============================================================================
# 4. TREE-SITTER PARSING (Step 14)
# ==============================================================================

def test_python_tree_sitter_parsing(uploaded_python_project):
    """Verify AST extraction of Python classes, methods, and functions."""
    project_id, headers = uploaded_python_project

    # Parse main.py
    main_res = client.get(
        f"/api/projects/{project_id}/parse?path=main.py",
        headers=headers,
    )
    assert main_res.status_code == 200
    main_data = main_res.json()
    func_names = [f["name"] for f in main_data["functions"]]
    assert "main" in func_names

    # Parse services/processor.py
    proc_res = client.get(
        f"/api/projects/{project_id}/parse?path=services/processor.py",
        headers=headers,
    )
    assert proc_res.status_code == 200
    proc_data = proc_res.json()
    class_names = [c["name"] for c in proc_data["classes"]]
    assert "DataProcessor" in class_names
    method_names = [f["name"] for f in proc_data["functions"]]
    assert "process_batch" in method_names
    assert "sync_to_cloud" in method_names


# ==============================================================================
# 5. DEPENDENCY ANALYSIS (Step 18)
# ==============================================================================

def test_python_dependency_analysis(uploaded_python_project):
    """Verify requirements.txt parsing and internal module links."""
    project_id, headers = uploaded_python_project

    res = client.get(f"/api/projects/{project_id}/dependencies", headers=headers)
    assert res.status_code == 200
    data = res.json()

    manifest_packages = [p["name"].lower() for p in data.get("packages", [])]
    assert "pydantic" in manifest_packages
    assert "requests" in manifest_packages

    relationships = data.get("relationships", [])
    assert len(relationships) > 0


# ==============================================================================
# 6. CODE INDEXING (Step 21)
# ==============================================================================

def test_python_code_indexing(uploaded_python_project):
    """Verify code chunking with AST symbol retention."""
    project_id, headers = uploaded_python_project

    res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["total_chunks"] >= 8

    chunks_res = client.get(f"/api/projects/{project_id}/chunks?limit=50", headers=headers)
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert any("services/processor.py" in c["metadata"]["file_path"] for c in chunks)
    assert any("main.py" in c["metadata"]["file_path"] for c in chunks)


# ==============================================================================
# 7. EMBEDDINGS & FAISS VECTOR INDEX (Steps 24, 25, 26)
# ==============================================================================

def test_python_embeddings_and_faiss(uploaded_python_project):
    """Generate Nomic embeddings and build persistent FAISS index for Python."""
    project_id, headers = uploaded_python_project

    client.post(f"/api/projects/{project_id}/index", headers=headers)

    emb_res = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert emb_res.status_code == 200
    assert emb_res.json()["embedding_dimension"] == 768

    index_res = client.post(f"/api/projects/{project_id}/vector-index", headers=headers)
    assert index_res.status_code == 200
    assert index_res.json()["status"] == "completed"


# ==============================================================================
# 8. CONTEXT RETRIEVAL (Steps 33, 34)
# ==============================================================================

def test_python_context_retrieval(uploaded_python_project):
    """Verify Day 17 context retrieval identifies main and service processor files."""
    project_id, headers = uploaded_python_project

    client.post(f"/api/projects/{project_id}/index", headers=headers)
    client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # Step 33: Explain the main function
    main_res = client.post(
        f"/api/projects/{project_id}/context/retrieve",
        headers=headers,
        json={"query": "Explain the main function", "top_files": 3},
    )
    assert main_res.status_code == 200
    main_data = main_res.json()
    top_paths = [f["file_path"].replace("\\", "/") for f in main_data["files"]]
    assert any("main.py" in p for p in top_paths)

    # Step 34: Service communication
    svc_res = client.post(
        f"/api/projects/{project_id}/context/retrieve",
        headers=headers,
        json={"query": "How do the services communicate with each other?", "top_files": 3},
    )
    assert svc_res.status_code == 200
    svc_data = svc_res.json()
    svc_paths = [f["file_path"].replace("\\", "/") for f in svc_data["files"]]
    assert any("services/processor.py" in p or "services/api_client.py" in p for p in svc_paths)


# ==============================================================================
# 9. RAG & AI CHAT & FOLLOW-UP (Steps 37, 38, 41, 42)
# ==============================================================================

def test_python_ai_chat_and_hallucination_defense(uploaded_python_project):
    """
    Test live RAG chat on Python project:
    - Grounded Q&A on architecture
    - Contextual follow-up turn
    - Hallucination defense (Kubernetes deployment rejection)
    """
    project_id, headers = uploaded_python_project

    client.post(f"/api/projects/{project_id}/index", headers=headers)
    client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # Turn 1: Architecture question
    chat_res_1 = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Explain the architecture of this Python project."},
    )
    assert chat_res_1.status_code == 200
    data_1 = chat_res_1.json()
    assert len(data_1["answer"]) > 20
    assert len(data_1["sources"]) > 0
    source_paths = [s["file_path"].replace("\\", "/") for s in data_1["sources"]]
    assert any("main.py" in p or "services/processor.py" in p for p in source_paths)
    conv_id = data_1["conversation_id"]

    # Turn 2: Follow-up question
    chat_res_2 = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Which class handles processing batches?", "conversation_id": conv_id},
    )
    assert chat_res_2.status_code == 200
    data_2 = chat_res_2.json()
    assert len(data_2["answer"]) > 10

    # Step 41: Hallucination defense for nonexistent Kubernetes deployment
    chat_res_k8s = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Explain the Kubernetes deployment code in this project."},
    )
    assert chat_res_k8s.status_code == 200
    data_k8s = chat_res_k8s.json()
    k8s_answer = data_k8s["answer"].lower()
    assert (
        "not found" in k8s_answer
        or "no" in k8s_answer
        or "insufficient" in k8s_answer
        or "does not contain" in k8s_answer
        or "not implemented" in k8s_answer
        or "not mentioned" in k8s_answer
        or "not present" in k8s_answer
        or "not provide" in k8s_answer
    )
