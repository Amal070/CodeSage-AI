import io
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.core.config import settings

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a unique test user and return (user_id, token, headers)."""
    unique_email = f"explorer_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Explorer Tester",
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
    unique_email = f"second_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Second Tester",
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
    """Upload a project with various files, nested folders, and binary files."""
    user_id, token, headers = test_user
    files = {
        "src/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "src/models/user.py": "class User:\n    pass\n",
        "src/utils/helpers.js": "export function greet(name) { return `Hello ${name}`; }\n",
        "docs/README.md": "# CodeSage Demo Project\nThis is a sample readme.",
        "assets/logo.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20,
        "config.json": '{"env": "production", "debug": false}',
    }
    zip_buf = create_zip_in_memory(files)
    res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("MyExplorerProject.zip", zip_buf, "application/zip")},
    )
    assert res.status_code == 201
    return res.json()["project"]


# ============================================================
# 1. FILE TREE API TESTS
# ============================================================

def test_file_tree_unauthenticated():
    """Unauthenticated requests to /files must be rejected with 401."""
    res = client.get("/api/projects/1/files")
    assert res.status_code == 401


def test_file_tree_success(test_user, sample_project):
    """Authenticated user should receive a hierarchical folder & file tree."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/files", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == project_id
    tree = data["tree"]
    assert isinstance(tree, list)
    assert len(tree) > 0

    # Verify top-level structure has folders first or recognized names
    names = [node["name"] for node in tree]
    assert "src" in names
    assert "docs" in names
    assert "assets" in names
    assert "config.json" in names

    # Verify nested children inside src
    src_node = next(n for n in tree if n["name"] == "src")
    assert src_node["type"] == "folder"
    assert src_node["children"] is not None
    src_child_names = [c["name"] for c in src_node["children"]]
    assert "main.py" in src_child_names
    assert "models" in src_child_names
    assert "utils" in src_child_names

    # Check relative path correctness (must be relative POSIX)
    main_node = next(c for c in src_node["children"] if c["name"] == "main.py")
    assert main_node["path"] == "src/main.py"
    assert main_node["type"] == "file"
    assert main_node["size"] > 0


def test_file_tree_cross_user_isolation(second_user, sample_project):
    """User B cannot view User A's project file tree (must return 404)."""
    _, _, headers = second_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/files", headers=headers)
    assert res.status_code == 404


def test_file_tree_nonexistent_project(test_user):
    """Requesting file tree for a nonexistent project returns 404."""
    _, _, headers = test_user
    res = client.get("/api/projects/999999/files", headers=headers)
    assert res.status_code == 404


# ============================================================
# 2. FILE CONTENT API TESTS
# ============================================================

def test_file_content_unauthenticated():
    """Unauthenticated requests to /file must be rejected with 401."""
    res = client.get("/api/projects/1/file?path=src/main.py")
    assert res.status_code == 401


def test_file_content_success_python(test_user, sample_project):
    """Retrieve Python file content, language detection, and metadata."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/file?path=src/main.py", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "main.py"
    assert data["path"] == "src/main.py"
    assert data["language"] == "python"
    assert data["is_binary"] is False
    assert "from fastapi import FastAPI" in data["content"]
    assert data["size"] > 0


def test_file_content_nested_javascript(test_user, sample_project):
    """Retrieve nested JS file with language detected as javascript."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/file?path=src/utils/helpers.js", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "helpers.js"
    assert data["language"] == "javascript"
    assert "greet(name)" in data["content"]


def test_file_content_markdown_and_json(test_user, sample_project):
    """Retrieve markdown and JSON files."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    # Markdown
    res_md = client.get(f"/api/projects/{project_id}/file?path=docs/README.md", headers=headers)
    assert res_md.status_code == 200
    assert res_md.json()["language"] == "markdown"

    # JSON
    res_json = client.get(f"/api/projects/{project_id}/file?path=config.json", headers=headers)
    assert res_json.status_code == 200
    assert res_json.json()["language"] == "json"


def test_file_content_binary_file(test_user, sample_project):
    """Binary files (.png) must be detected safely with clear message and content=None."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/file?path=assets/logo.png", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "logo.png"
    assert data["is_binary"] is True
    assert data["content"] is None
    assert "Binary files cannot be displayed" in data["message"]


def test_file_content_cross_user_forbidden(second_user, sample_project):
    """User B cannot read files belonging to User A's project."""
    _, _, headers = second_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/file?path=src/main.py", headers=headers)
    assert res.status_code == 404


def test_file_content_nonexistent_file(test_user, sample_project):
    """Requesting a nonexistent file inside the project returns 404."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/file?path=src/ghost.py", headers=headers)
    assert res.status_code == 404


def test_file_content_directory_path(test_user, sample_project):
    """Requesting a directory instead of a regular file returns 400."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/file?path=src", headers=headers)
    assert res.status_code == 400
    assert "directory" in res.json()["detail"].lower()


# ============================================================
# 3. SECURITY & PATH TRAVERSAL DEFENSE TESTS
# ============================================================

def test_file_content_path_traversal_dots(test_user, sample_project):
    """Rejects ../ traversal attempts with 400 Bad Request."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    traversal_paths = [
        "../original.zip",
        "../../etc/passwd",
        "src/../../original.zip",
        "..\\..\\Windows\\win.ini",
    ]
    for path in traversal_paths:
        res = client.get(f"/api/projects/{project_id}/file?path={path}", headers=headers)
        assert res.status_code == 400, f"Path '{path}' did not trigger 400 Bad Request"
        assert "traversal" in res.json()["detail"].lower() or "absolute" in res.json()["detail"].lower()


def test_file_content_absolute_path_injection(test_user, sample_project):
    """Rejects absolute paths (Windows drive C: or Unix root /) with 400."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    abs_paths = [
        "/etc/passwd",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "\\Windows\\win.ini",
    ]
    for path in abs_paths:
        res = client.get(f"/api/projects/{project_id}/file?path={path}", headers=headers)
        assert res.status_code == 400, f"Path '{path}' did not trigger 400 Bad Request"


def test_file_content_empty_path(test_user, sample_project):
    """Empty or whitespace path returns 400 Bad Request."""
    _, _, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/file?path=   ", headers=headers)
    assert res.status_code == 400


def test_file_content_large_file(test_user, monkeypatch):
    """Files exceeding MAX_VIEWABLE_FILE_SIZE_MB return 413 Request Entity Too Large."""
    user_id, token, headers = test_user

    # Create a small project with a 2KB file
    files = {"small.py": "x = 1\n" * 200}
    zip_buf = create_zip_in_memory(files)
    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("LimitProject.zip", zip_buf, "application/zip")},
    )
    assert upload_res.status_code == 201
    project_id = upload_res.json()["project"]["id"]

    # Temporarily set max viewable size to 0 MB (0 bytes) to test limit trigger
    monkeypatch.setattr(settings, "MAX_VIEWABLE_FILE_SIZE_MB", 0)

    res = client.get(f"/api/projects/{project_id}/file?path=small.py", headers=headers)
    assert res.status_code == 413
    assert "too large to preview" in res.json()["detail"].lower()
