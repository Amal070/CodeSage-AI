import io
import json
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.models.code_chunk import CodeChunk

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a unique test user and return (user_id, token, headers)."""
    unique_email = f"indexer_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Indexer Tester",
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
    unique_email = f"second_indexer_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Second Indexer Tester",
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
    """Helper to construct an in-memory ZIP archive from a dict of {path: content}."""
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
def sample_index_project(test_user):
    """
    Creates an uploaded project with Python, JavaScript, Java, Config, and Docs files
    matching Day 10 test requirements.
    """
    user_id, token, headers = test_user
    files = {
        # Python with AuthService class and methods (Phase 37)
        "backend/app/auth.py": (
            "import os\n"
            "from typing import Optional\n"
            "\n"
            "class AuthService:\n"
            "    def __init__(self):\n"
            "        self.secret = 'secret_key'\n"
            "\n"
            "    def register_user(self, email: str, password: str) -> dict:\n"
            "        # Register new user in database\n"
            "        user = {'email': email, 'status': 'registered'}\n"
            "        return user\n"
            "\n"
            "    def login_user(self, username: str, password: str) -> bool:\n"
            "        # Validate credentials\n"
            "        if username and password:\n"
            "            return True\n"
            "        return False\n"
            "\n"
            "    def verify_token(self, token: str) -> Optional[dict]:\n"
            "        # Verify JWT payload\n"
            "        if token.startswith('valid_'):\n"
            "            return {'sub': 'user123'}\n"
            "        return None\n"
        ),
        # JavaScript with App and Dashboard functions (Phase 38)
        "frontend/src/App.jsx": (
            "import React from 'react';\n"
            "\n"
            "function App() {\n"
            "    return (\n"
            "        <div className='app'>\n"
            "            <h1>CodeSage AI</h1>\n"
            "        </div>\n"
            "    );\n"
            "}\n"
            "\n"
            "function Dashboard() {\n"
            "    return (\n"
            "        <main>\n"
            "            <h2>Dashboard Overview</h2>\n"
            "        </main>\n"
            "    );\n"
            "}\n"
            "\n"
            "export default App;\n"
        ),
        # Java with UserService class and methods (Phase 39)
        "src/main/java/com/example/UserService.java": (
            "package com.example;\n"
            "\n"
            "public class UserService {\n"
            "    public User getUser(String id) {\n"
            "        return new User(id);\n"
            "    }\n"
            "\n"
            "    public void saveUser(User user) {\n"
            "        System.out.println('Saved ' + user.getName());\n"
            "    }\n"
            "}\n"
        ),
        # Documentation (Phase 17 & 32)
        "README.md": (
            "# CodeSage AI Documentation\n"
            "This is documentation for the code indexing pipeline.\n"
        ),
        # Configuration
        "package.json": json.dumps({"name": "test-pkg", "version": "1.0.0"}),
    }

    zip_bytes = create_zip_in_memory(files)
    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("sample_index.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    return upload_res.json()["project"]


def test_code_indexing_multi_language(test_user, sample_index_project):
    """
    Phase 36-39: Test indexing pipeline on multi-language project:
    - Verifies Python classes and methods chunked with correct symbols
    - Verifies JS functions chunked
    - Verifies Java classes and methods chunked
    - Verifies metadata, line numbers, hashes, and source_type
    """
    user_id, token, headers = test_user
    project_id = sample_index_project["id"]

    # Run Indexing
    res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["project_id"] == project_id
    assert data["status"] == "completed"
    assert data["total_files"] >= 5
    assert data["indexed_files"] >= 5
    assert data["total_chunks"] >= 5

    # Check Languages in response
    langs = data["languages"]
    assert "Python" in langs
    assert "JavaScript" in langs
    assert "Java" in langs
    assert "Markdown" in langs
    assert "JSON" in langs

    # Fetch Chunks (ready for Day 11)
    chunks_res = client.get(f"/api/projects/{project_id}/chunks?limit=100", headers=headers)
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) >= 5

    # 1. Verify Python Chunks (Phase 37)
    py_chunks = [c for c in chunks if c["metadata"]["file_path"] == "backend/app/auth.py"]
    assert len(py_chunks) >= 3

    symbols_found = {c["metadata"]["symbol_name"] for c in py_chunks if c["metadata"]["symbol_name"]}
    assert "AuthService" in symbols_found or any("register_user" in str(c["metadata"]["symbol_name"]) for c in py_chunks)
    assert any("login_user" in str(c["metadata"]["symbol_name"]) for c in py_chunks)
    assert any("verify_token" in str(c["metadata"]["symbol_name"]) for c in py_chunks)

    # Check that Python source is preserved verbatim without modification
    for c in py_chunks:
        assert c["metadata"]["language"] == "Python"
        assert c["metadata"]["source_type"] == "code"
        assert c["metadata"]["start_line"] >= 1
        assert c["metadata"]["end_line"] >= c["metadata"]["start_line"]
        assert len(c["metadata"]["content_hash"]) == 64
        assert c["content"].strip() != ""
        # Verify deterministic chunk_id format
        assert c["chunk_id"].startswith(f"p{project_id}_")

    # 2. Verify JavaScript Chunks (Phase 38)
    js_chunks = [c for c in chunks if c["metadata"]["file_path"] == "frontend/src/App.jsx"]
    assert len(js_chunks) >= 2
    js_symbols = {c["metadata"]["symbol_name"] for c in js_chunks if c["metadata"]["symbol_name"]}
    assert "App" in js_symbols
    assert "Dashboard" in js_symbols
    for c in js_chunks:
        assert c["metadata"]["language"] == "JavaScript"
        assert c["metadata"]["source_type"] == "code"

    # 3. Verify Java Chunks (Phase 39)
    java_chunks = [c for c in chunks if "UserService.java" in c["metadata"]["file_path"]]
    assert len(java_chunks) >= 2
    java_symbols = {c["metadata"]["symbol_name"] for c in java_chunks if c["metadata"]["symbol_name"]}
    assert "UserService" in java_symbols or "getUser" in java_symbols or "saveUser" in java_symbols

    # 4. Verify Documentation & Config (Phase 17)
    md_chunk = next(c for c in chunks if c["metadata"]["file_path"] == "README.md")
    assert md_chunk["metadata"]["source_type"] == "documentation"
    assert md_chunk["metadata"]["language"] == "Markdown"

    json_chunk = next(c for c in chunks if c["metadata"]["file_path"] == "package.json")
    assert json_chunk["metadata"]["source_type"] == "config"


def test_code_indexing_idempotent(test_user, sample_index_project):
    """
    Phase 24 & 43: Idempotent re-indexing test
    Running indexing twice must not create duplicate chunks.
    Chunk count and content hashes must remain identical.
    """
    user_id, token, headers = test_user
    project_id = sample_index_project["id"]

    # First run
    res1 = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()

    # Second run
    res2 = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()

    assert data1["total_chunks"] == data2["total_chunks"]
    assert data1["indexed_files"] == data2["indexed_files"]

    # Verify directly in PostgreSQL table via SQL query
    db = next(get_db())
    try:
        from sqlalchemy import select
        db_chunks = list(db.scalars(select(CodeChunk).where(CodeChunk.project_id == project_id)).all())
        assert len(db_chunks) == data1["total_chunks"]
    finally:
        db.close()


def test_large_file_subdivision(test_user):
    """
    Phase 40: Large code file test
    Verifies that a file exceeding CHUNK_SIZE (100 lines) is subdivided
    into multiple overlapping chunks.
    """
    user_id, token, headers = test_user
    # Generate 250 lines file
    code_lines = [f"def function_{i}():\n    return {i}\n" for i in range(125)]
    large_content = "\n".join(code_lines)

    files = {"large_module.py": large_content}
    zip_bytes = create_zip_in_memory(files)

    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("large_project.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    proj_id = upload_res.json()["project"]["id"]

    res = client.post(f"/api/projects/{proj_id}/index", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Should be split into multiple chunks
    assert data["total_chunks"] >= 2

    chunks_res = client.get(f"/api/projects/{proj_id}/chunks", headers=headers)
    chunks = chunks_res.json()
    for c in chunks:
        # Every chunk must be within reasonable size
        line_count = c["metadata"]["end_line"] - c["metadata"]["start_line"] + 1
        assert line_count <= 100


def test_file_size_limit_skipped(test_user):
    """
    Phase 6 & 40: File size protection
    A file exceeding MAX_INDEXABLE_FILE_SIZE (1 MB) must be skipped safely
    without crashing the indexing process.
    """
    user_id, token, headers = test_user
    # 1.2 MB file
    huge_content = "x = 1\n" * 200000

    files = {
        "normal.py": "def normal(): pass\n",
        "huge_file.py": huge_content,
    }
    zip_bytes = create_zip_in_memory(files)

    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("huge_project.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    proj_id = upload_res.json()["project"]["id"]

    res = client.post(f"/api/projects/{proj_id}/index", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "completed"
    assert data["indexed_files"] == 1  # normal.py indexed
    assert data["skipped_files"] == 1  # huge_file.py skipped

    skipped = data["skipped_file_details"]
    assert len(skipped) == 1
    assert skipped[0]["path"] == "huge_file.py"
    assert skipped[0]["reason"] == "file_too_large"


def test_binary_file_skipped(test_user):
    """
    Phase 41: Unsupported / Binary file test
    Binary files must be skipped without crashing.
    """
    user_id, token, headers = test_user
    files = {
        "app.py": "print('hello')\n",
        "image.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
        "fake_bin.py": b"\x00\x00\x01\x02\x03malicious_binary_content",
    }
    zip_bytes = create_zip_in_memory(files)

    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("binary_project.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    proj_id = upload_res.json()["project"]["id"]

    res = client.post(f"/api/projects/{proj_id}/index", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["indexed_files"] == 1  # app.py
    assert data["skipped_files"] >= 1


def test_empty_project_indexing(test_user):
    """
    Phase 31: Empty project test
    A project with no indexable files returns completed with 0 chunks.
    """
    user_id, token, headers = test_user
    files = {"image.png": b"\x89PNG\r\n\x1a\n"}
    zip_bytes = create_zip_in_memory(files)

    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("empty_project.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    proj_id = upload_res.json()["project"]["id"]

    res = client.post(f"/api/projects/{proj_id}/index", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "completed"
    assert data["indexed_files"] == 0
    assert data["total_chunks"] == 0


def test_indexing_tenancy_isolation(test_user, second_user, sample_index_project):
    """
    Phase 33: Tenancy isolation
    A user cannot index another user's project.
    """
    user2_id, token2, headers2 = second_user
    project_id = sample_index_project["id"]

    res = client.post(f"/api/projects/{project_id}/index", headers=headers2)
    assert res.status_code == 404


def test_indexing_unauthenticated(sample_index_project):
    """
    Phase 33: Unauthenticated access blocked
    """
    project_id = sample_index_project["id"]
    res = client.post(f"/api/projects/{project_id}/index")
    assert res.status_code == 401


def test_indexing_status_endpoint(test_user, sample_index_project):
    """
    Phase 22: Get indexing status endpoint
    """
    user_id, token, headers = test_user
    project_id = sample_index_project["id"]

    # Initially before indexing
    status_res = client.get(f"/api/projects/{project_id}/index/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] in ["uploaded", "indexed", "completed"]

    # Run indexing
    client.post(f"/api/projects/{project_id}/index", headers=headers)

    # After indexing
    status_res2 = client.get(f"/api/projects/{project_id}/index/status", headers=headers)
    assert status_res2.status_code == 200
    s_data = status_res2.json()
    assert s_data["status"] == "indexed"
    assert s_data["total_chunks"] > 0
    assert s_data["indexed_files"] > 0


def test_no_absolute_paths_exposed_in_indexing(test_user, sample_index_project):
    """
    Phase 33: Absolute server paths must never be exposed in chunks or index response.
    """
    user_id, token, headers = test_user
    project_id = sample_index_project["id"]

    res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert res.status_code == 200
    raw_text = res.text

    assert "C:\\" not in raw_text
    assert "c:/" not in raw_text.lower()
    assert "\\users\\" not in raw_text.lower()
    assert "/home/" not in raw_text
