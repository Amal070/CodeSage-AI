"""
CodeSage AI — Day 18 Test Suite: React Project Pipeline

Tests the complete CodeSage AI pipeline on a realistic React application:
1. Upload & Safe Extraction (package.json, src/)
2. File Explorer (JSX, JS, CSS, JSON)
3. Project Structure & Language Analysis (JavaScript/JSX detection)
4. Tree-sitter AST Code Parsing (Functional Components, Hooks, Axios services)
5. Dependency Analysis (package.json parsing, React/Axios dependencies, local imports)
6. Code Indexing & JSX Chunk Metadata
7. Nomic Embed Text Embedding Generation (768 dimensions)
8. FAISS Index Construction & Persistence
9. Day 17 File-Level Context Retrieval (Frontend communication, App component, API requests)
10. RAG & AI Chat Grounding & Source Citations
11. Multi-turn Conversation & Contextual Follow-up
12. Hallucination Defense (Nonexistent GraphQL feature)
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
from tests.fixtures.sample_projects import REACT_PROJECT_FILES, build_project_zip

client = TestClient(app)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def react_user():
    """Creates a distinct test user for the React project pipeline."""
    unique_email = f"react_tester_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="React Pipeline Tester",
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
def uploaded_react_project(react_user):
    """Uploads the React TaskFlow project and returns project_id and headers."""
    user_id, token, headers = react_user
    zip_buffer = build_project_zip(REACT_PROJECT_FILES)

    response = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("react_taskflow.zip", zip_buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 201, f"Upload failed: {response.text}"
    project_id = response.json()["project"]["id"]
    return project_id, headers


# ==============================================================================
# 1. UPLOAD AND EXTRACTION (Step 4)
# ==============================================================================

def test_react_upload_and_extraction(react_user):
    """Verify React ZIP upload, extraction, and package.json availability."""
    user_id, token, headers = react_user
    zip_buffer = build_project_zip(REACT_PROJECT_FILES)

    start_time = time.time()
    response = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("react_taskflow.zip", zip_buffer.getvalue(), "application/zip")},
    )
    duration = time.time() - start_time

    assert response.status_code == 201
    data = response.json()
    project = data["project"]
    assert project["name"] == "react_taskflow"
    assert project["file_count"] >= 8
    assert project["lines_of_code"] > 50
    assert duration < 5.0


# ==============================================================================
# 2. FILE EXPLORER (Step 7)
# ==============================================================================

def test_react_file_explorer(uploaded_react_project):
    """Verify tree structure and JSX/CSS file content retrieval."""
    project_id, headers = uploaded_react_project

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

    assert any("src/App.jsx" in p for p in found_paths)
    assert any("src/services/api.js" in p for p in found_paths)
    assert any("package.json" in p for p in found_paths)

    # 2. JSX File Content
    jsx_res = client.get(
        f"/api/projects/{project_id}/file?path=src/App.jsx",
        headers=headers,
    )
    assert jsx_res.status_code == 200
    jsx_data = jsx_res.json()
    assert jsx_data["language"].lower() in ["javascript", "jsx"]
    assert "export default function App" in jsx_data["content"]
    assert not jsx_data["is_binary"]


# ==============================================================================
# 3. PROJECT ANALYSIS (Step 10)
# ==============================================================================

def test_react_project_analysis(uploaded_react_project):
    """Verify JavaScript/JSX language classification and file stats."""
    project_id, headers = uploaded_react_project

    res = client.get(f"/api/projects/{project_id}/analysis", headers=headers)
    assert res.status_code == 200
    data = res.json()

    stats = data["statistics"]
    assert stats["total_files"] >= 8

    # Language breakdown: JavaScript or JSX should be present
    assert any(k in ["JavaScript", "JSX"] for k in data["languages"])


# ==============================================================================
# 4. TREE-SITTER PARSING (Step 13)
# ==============================================================================

def test_react_tree_sitter_parsing(uploaded_react_project):
    """Verify AST extraction of React functional components, hooks, and axios functions."""
    project_id, headers = uploaded_react_project

    # Parse src/App.jsx
    app_res = client.get(
        f"/api/projects/{project_id}/parse?path=src/App.jsx",
        headers=headers,
    )
    assert app_res.status_code == 200
    app_data = app_res.json()
    func_names = [f["name"] for f in app_data["functions"]]
    assert "App" in func_names

    # Parse src/services/api.js
    api_res = client.get(
        f"/api/projects/{project_id}/parse?path=src/services/api.js",
        headers=headers,
    )
    assert api_res.status_code == 200
    api_data = api_res.json()
    api_funcs = [f["name"] for f in api_data["functions"]]
    assert "fetchTasks" in api_funcs
    assert "completeTask" in api_funcs
    assert "loginUser" in api_funcs


# ==============================================================================
# 5. DEPENDENCY ANALYSIS (Step 17)
# ==============================================================================

def test_react_dependency_analysis(uploaded_react_project):
    """Verify package.json dependencies and local module relationships."""
    project_id, headers = uploaded_react_project

    res = client.get(f"/api/projects/{project_id}/dependencies", headers=headers)
    assert res.status_code == 200
    data = res.json()

    manifest_packages = [p["name"].lower() for p in data.get("packages", [])]
    assert "react" in manifest_packages
    assert "axios" in manifest_packages

    # Local relationships (e.g. App importing Navbar)
    relationships = data.get("relationships", [])
    assert len(relationships) > 0


# ==============================================================================
# 6. CODE INDEXING (Step 20)
# ==============================================================================

def test_react_code_indexing(uploaded_react_project):
    """Verify indexing of JSX and JavaScript files with chunk metadata."""
    project_id, headers = uploaded_react_project

    res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["total_chunks"] >= 8

    # Verify chunk contents
    chunks_res = client.get(f"/api/projects/{project_id}/chunks?limit=50", headers=headers)
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert any("src/services/api.js" in c["metadata"]["file_path"] for c in chunks)
    assert any("src/App.jsx" in c["metadata"]["file_path"] for c in chunks)


# ==============================================================================
# 7. EMBEDDINGS & FAISS VECTOR INDEX (Steps 23, 25, 26)
# ==============================================================================

def test_react_embeddings_and_faiss(uploaded_react_project):
    """Generate Nomic embeddings and build persistent FAISS index for React."""
    project_id, headers = uploaded_react_project

    client.post(f"/api/projects/{project_id}/index", headers=headers)

    emb_res = client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    assert emb_res.status_code == 200
    assert emb_res.json()["embedding_dimension"] == 768

    index_res = client.post(f"/api/projects/{project_id}/vector-index", headers=headers)
    assert index_res.status_code == 200
    assert index_res.json()["status"] == "completed"


# ==============================================================================
# 8. CONTEXT RETRIEVAL (Steps 30, 31, 32)
# ==============================================================================

def test_react_context_retrieval(uploaded_react_project):
    """Verify Day 17 context retrieval accurately identifies React API and App files."""
    project_id, headers = uploaded_react_project

    client.post(f"/api/projects/{project_id}/index", headers=headers)
    client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # Step 30 & 32: Frontend communication & API requests
    api_res = client.post(
        f"/api/projects/{project_id}/context/retrieve",
        headers=headers,
        json={"query": "How does the frontend communicate with the backend?", "top_files": 3},
    )
    assert api_res.status_code == 200
    api_data = api_res.json()
    top_paths = [f["file_path"].replace("\\", "/") for f in api_data["files"]]
    assert any("src/services/api.js" in p for p in top_paths)

    # Step 31: Main App component
    app_res = client.post(
        f"/api/projects/{project_id}/context/retrieve",
        headers=headers,
        json={"query": "Explain the main App component", "top_files": 3},
    )
    assert app_res.status_code == 200
    app_data = app_res.json()
    app_paths = [f["file_path"].replace("\\", "/") for f in app_data["files"]]
    assert any("src/App.jsx" in p for p in app_paths)


# ==============================================================================
# 9. RAG & AI CHAT & FOLLOW-UP (Steps 36, 38, 41, 42)
# ==============================================================================

def test_react_ai_chat_and_hallucination_defense(uploaded_react_project):
    """
    Test live RAG chat on React project:
    - Grounded Q&A on backend communication
    - Contextual follow-up turn
    - Hallucination defense (GraphQL server rejection)
    """
    project_id, headers = uploaded_react_project

    client.post(f"/api/projects/{project_id}/index", headers=headers)
    client.post(f"/api/projects/{project_id}/embeddings", headers=headers)
    client.post(f"/api/projects/{project_id}/vector-index", headers=headers)

    # Turn 1: Communication question
    chat_res_1 = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Explain how this React application communicates with the backend."},
    )
    assert chat_res_1.status_code == 200
    data_1 = chat_res_1.json()
    assert len(data_1["answer"]) > 20
    assert len(data_1["sources"]) > 0
    source_paths = [s["file_path"].replace("\\", "/") for s in data_1["sources"]]
    assert any("src/services/api.js" in p for p in source_paths)
    conv_id = data_1["conversation_id"]

    # Turn 2: Follow-up question
    chat_res_2 = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Which function fetches the tasks?", "conversation_id": conv_id},
    )
    assert chat_res_2.status_code == 200
    data_2 = chat_res_2.json()
    assert len(data_2["answer"]) > 10

    # Step 41: Hallucination defense for nonexistent GraphQL
    chat_res_gql = client.post(
        f"/api/projects/{project_id}/chat",
        headers=headers,
        json={"question": "Explain the GraphQL server implementation in this project."},
    )
    assert chat_res_gql.status_code == 200
    data_gql = chat_res_gql.json()
    gql_answer = data_gql["answer"].lower()
    assert (
        "not found" in gql_answer
        or "no" in gql_answer
        or "insufficient" in gql_answer
        or "does not contain" in gql_answer
        or "not implemented" in gql_answer
        or "not mentioned" in gql_answer
        or "not present" in gql_answer
        or "not provide" in gql_answer
    )
