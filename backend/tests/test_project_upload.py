import io
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.database import get_db
from app.models.user import User
from app.core.security import hash_password

client = TestClient(app)


@pytest.fixture
def test_user_token():
    """Create a unique test user and return (user_id, token, headers)."""
    unique_email = f"uploader_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Upload Tester",
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
            zf.writestr(file_path, content)
    zip_buffer.seek(0)
    return zip_buffer


# ============================================================
# 1. AUTHENTICATION REQUIREMENT
# ============================================================

def test_upload_unauthenticated():
    """Upload endpoint must reject unauthenticated requests with 401."""
    zip_buf = create_zip_in_memory({"test.py": "print('hello')"})
    response = client.post(
        "/api/projects/upload",
        files={"file": ("test.zip", zip_buf, "application/zip")},
    )
    assert response.status_code == 401


# ============================================================
# 2. FILE TYPE AND EXTENSION VALIDATION
# ============================================================

@pytest.mark.parametrize("bad_filename,content,content_type", [
    ("malicious.exe", b"MZ\x90\x00executable", "application/octet-stream"),
    ("document.pdf", b"%PDF-1.4...", "application/pdf"),
    ("script.txt", b"plain text", "text/plain"),
    ("archive.rar", b"Rar!\x1a\x07\x00", "application/x-rar-compressed"),
    ("archive.7z", b"7z\xbc\xaf\x27\x1c", "application/x-7z-compressed"),
])
def test_upload_invalid_file_extension(test_user_token, bad_filename, content, content_type):
    """Only .zip files are allowed; all other formats must return 400."""
    _, _, headers = test_user_token
    response = client.post(
        "/api/projects/upload",
        files={"file": (bad_filename, io.BytesIO(content), content_type)},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Only ZIP files are allowed" in response.json().get("detail", "")


# ============================================================
# 3. CORRUPTED AND EMPTY ZIP VALIDATION
# ============================================================

def test_upload_corrupted_zip(test_user_token):
    """Files with .zip extension but invalid contents must return 400."""
    _, _, headers = test_user_token
    corrupted_data = b"This is not a zip file at all"
    response = client.post(
        "/api/projects/upload",
        files={"file": ("corrupted.zip", io.BytesIO(corrupted_data), "application/zip")},
        headers=headers,
    )
    assert response.status_code == 400
    assert "valid ZIP" in response.json().get("detail", "")


def test_upload_empty_zip(test_user_token):
    """Empty ZIP archives must be rejected with 400."""
    _, _, headers = test_user_token
    empty_zip = io.BytesIO()
    with zipfile.ZipFile(empty_zip, "w") as zf:
        pass
    empty_zip.seek(0)

    response = client.post(
        "/api/projects/upload",
        files={"file": ("empty.zip", empty_zip, "application/zip")},
        headers=headers,
    )
    assert response.status_code == 400


# ============================================================
# 4. ZIP SLIP / PATH TRAVERSAL SECURITY DEFENSE
# ============================================================

def test_upload_zip_slip_security(test_user_token):
    """
    CRITICAL SECURITY TEST:
    A ZIP archive with path traversal ('../../evil.txt') must be rejected,
    preventing any files from being written outside the isolated extraction directory.
    """
    _, _, headers = test_user_token
    malicious_zip = io.BytesIO()
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        # Create a Zip Slip entry
        zf.writestr("../../evil_payload.txt", "MALICIOUS CONTENT")
    malicious_zip.seek(0)

    response = client.post(
        "/api/projects/upload",
        files={"file": ("exploit.zip", malicious_zip, "application/zip")},
        headers=headers,
    )
    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "path traversal" in detail.lower() or "security violation" in detail.lower()


# ============================================================
# 5. VALID PROJECT ZIP UPLOAD & EXTRACTION
# ============================================================

def test_upload_valid_project_zip(test_user_token):
    """
    Legitimate ZIP upload must succeed:
    - 201 Created
    - Name derived from ZIP filename (MyAwesomeApp.zip -> MyAwesomeApp)
    - Metadata saved in PostgreSQL
    - Correct user ownership
    """
    user_id, _, headers = test_user_token
    project_files = {
        "main.py": "def main():\n    print('Hello CodeSage')\n",
        "utils/helpers.py": "def add(a, b):\n    return a + b\n",
        "README.md": "# My Awesome App\nSample project for Day 5.\n",
    }
    zip_buf = create_zip_in_memory(project_files)

    response = client.post(
        "/api/projects/upload",
        files={"file": ("MyAwesomeApp.zip", zip_buf, "application/zip")},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data.get("message") == "Project uploaded successfully"
    project = data.get("project")
    assert project is not None
    assert project.get("name") == "MyAwesomeApp"
    assert project.get("original_filename") == "MyAwesomeApp.zip"
    assert project.get("status") == "uploaded"
    assert project.get("user_id") == user_id
    assert project.get("file_count") == 3
    assert project.get("lines_of_code") > 0

    project_id = project.get("id")

    # Verify listing user projects includes the new project
    list_res = client.get("/api/projects", headers=headers)
    assert list_res.status_code == 200
    projects_list = list_res.json()
    assert any(p["id"] == project_id for p in projects_list)

    # Verify retrieving project by ID
    get_res = client.get(f"/api/projects/{project_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "MyAwesomeApp"


# ============================================================
# 6. USER DATA ISOLATION (CROSS-USER PERMISSION CHECK)
# ============================================================

def test_project_cross_user_isolation(test_user_token):
    """Users must not be able to retrieve other users' projects."""
    _, _, headers1 = test_user_token

    # Upload project for user 1
    zip_buf = create_zip_in_memory({"file.py": "x = 1\n"})
    res = client.post(
        "/api/projects/upload",
        files={"file": ("PrivateProject.zip", zip_buf, "application/zip")},
        headers=headers1,
    )
    assert res.status_code == 201
    project1_id = res.json()["project"]["id"]

    # Create user 2
    unique_email2 = f"uploader2_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user2 = User(
            name="User Two",
            email=unique_email2,
            password_hash=hash_password("Password123!"),
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)
        token2 = create_access_token(data={"sub": str(user2.id), "email": unique_email2})
    finally:
        db.close()

    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 2 listing should NOT include user 1's project
    list2_res = client.get("/api/projects", headers=headers2)
    assert list2_res.status_code == 200
    assert not any(p["id"] == project1_id for p in list2_res.json())

    # User 2 attempting to access user 1's project by ID must return 404
    get2_res = client.get(f"/api/projects/{project1_id}", headers=headers2)
    assert get2_res.status_code == 404
