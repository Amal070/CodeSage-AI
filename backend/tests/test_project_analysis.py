import io
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a unique test user and return (user_id, token, headers)."""
    unique_email = f"analyzer_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Analyzer Tester",
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
    unique_email = f"second_analyzer_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Second Analyzer Tester",
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
def sample_project(test_user):
    """
    Upload a multi-language project matching Day 8 specifications:
    sample-project/
    ├── backend/
    │   ├── main.py
    │   └── database.py
    ├── frontend/
    │   ├── App.jsx
    │   └── main.js
    ├── styles/
    │   └── style.css
    ├── tests/
    │   └── test_main.py
    └── README.md
    """
    user_id, token, headers = test_user
    files = {
        "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "backend/database.py": "from sqlalchemy import create_engine\n",
        "frontend/App.jsx": "export default function App() { return <div>App</div>; }\n",
        "frontend/main.js": "import React from 'react';\n",
        "styles/style.css": "body { margin: 0; background: #000; }\n",
        "tests/test_main.py": "def test_app(): assert True\n",
        "README.md": "# Sample Project\nCodeSage AI Day 8 test\n",
    }
    zip_buf = create_zip_in_memory(files)
    res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("SampleAnalysisProject.zip", zip_buf, "application/zip")},
    )
    assert res.status_code == 201
    return res.json()["project"]


@pytest.fixture
def nested_project(test_user):
    """
    Upload a project with deep nesting:
    project/
    └── src/
        └── modules/
            └── services/
                └── auth/
                    └── auth.py
    """
    user_id, token, headers = test_user
    files = {
        "src/modules/services/auth/auth.py": "def authenticate(): pass\n",
        "README.md": "# Nested Project\n",
    }
    zip_buf = create_zip_in_memory(files)
    res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("NestedProject.zip", zip_buf, "application/zip")},
    )
    assert res.status_code == 201
    return res.json()["project"]


@pytest.fixture
def empty_project(test_user):
    """Upload an empty ZIP archive project."""
    user_id, token, headers = test_user
    files = {
        ".gitkeep": "",
    }
    zip_buf = create_zip_in_memory(files)
    res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("EmptyProject.zip", zip_buf, "application/zip")},
    )
    assert res.status_code == 201
    return res.json()["project"]


# ============================================================
# 1. CORE ANALYSIS TESTS
# ============================================================

def test_project_analysis_statistics(sample_project, test_user):
    user_id, token, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/analysis", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Project metadata
    assert data["project_id"] == project_id
    assert "SampleAnalysisProject" in data["project_name"]

    # Statistics
    stats = data["statistics"]
    assert stats["total_files"] == 7
    # Folders: backend, frontend, styles, tests
    assert stats["total_folders"] == 4
    assert stats["total_size_bytes"] > 0
    assert stats["total_size_kb"] > 0
    assert isinstance(stats["total_size_mb"], float)

    # Languages
    langs = data["languages"]
    # 3 Python files (.py), 2 JavaScript files (.jsx, .js), 1 CSS (.css), 1 Markdown (.md)
    assert langs["Python"] == 3
    assert langs["JavaScript"] == 2
    assert langs["CSS"] == 1
    assert langs["Markdown"] == 1

    # File counts by extension
    exts = data["file_count"]["by_extension"]
    assert exts[".py"] == 3
    assert exts[".jsx"] == 1
    assert exts[".js"] == 1
    assert exts[".css"] == 1
    assert exts[".md"] == 1
    assert data["file_count"]["total"] == 7

    # Folder hierarchy
    hierarchy = data["folder_hierarchy"]
    assert hierarchy["type"] == "folder"
    children_names = [c["name"] for c in hierarchy["children"]]
    assert "backend" in children_names
    assert "frontend" in children_names
    assert "styles" in children_names
    assert "tests" in children_names
    assert "README.md" in children_names

    # Check relative paths, no absolute paths
    for child in hierarchy["children"]:
        if child["type"] == "file":
            assert not child["path"].startswith("/")
            assert not child["path"].startswith("\\")
            assert ":" not in child["path"]


def test_nested_directory_analysis(nested_project, test_user):
    user_id, token, headers = test_user
    project_id = nested_project["id"]

    res = client.get(f"/api/projects/{project_id}/analysis", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Verify deep folder hierarchy
    stats = data["statistics"]
    assert stats["total_files"] == 2
    # Folders: src, src/modules, src/modules/services, src/modules/services/auth
    assert stats["total_folders"] == 4

    # Traverse hierarchy to find auth.py
    hierarchy = data["folder_hierarchy"]
    src_node = next(c for c in hierarchy["children"] if c["name"] == "src")
    modules_node = next(c for c in src_node["children"] if c["name"] == "modules")
    services_node = next(c for c in modules_node["children"] if c["name"] == "services")
    auth_node = next(c for c in services_node["children"] if c["name"] == "auth")
    auth_file = next(c for c in auth_node["children"] if c["name"] == "auth.py")
    assert auth_file["type"] == "file"
    assert auth_file["path"] == "src/modules/services/auth/auth.py"


def test_empty_project_analysis(empty_project, test_user):
    user_id, token, headers = test_user
    project_id = empty_project["id"]

    res = client.get(f"/api/projects/{project_id}/analysis", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Empty project (.gitkeep is a file)
    assert data["statistics"]["total_files"] >= 0
    assert isinstance(data["statistics"]["total_folders"], int)
    assert isinstance(data["languages"], dict)
    assert isinstance(data["file_count"]["by_extension"], dict)
    assert data["folder_hierarchy"]["type"] == "folder"


# ============================================================
# 2. SECURITY & TENANCY TESTS
# ============================================================

def test_analysis_tenancy_isolation(sample_project, second_user):
    """Second user must be denied access to first user's project analysis."""
    user_id, token, headers = second_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/analysis", headers=headers)
    assert res.status_code == 404
    assert "permission" in res.json()["detail"] or "not found" in res.json()["detail"]


def test_analysis_unauthenticated(sample_project):
    """Unauthenticated requests must be rejected with 401."""
    project_id = sample_project["id"]
    res = client.get(f"/api/projects/{project_id}/analysis")
    assert res.status_code == 401


def test_analysis_nonexistent_project(test_user):
    """Non-existent project must return 404."""
    user_id, token, headers = test_user
    res = client.get("/api/projects/999999/analysis", headers=headers)
    assert res.status_code == 404
