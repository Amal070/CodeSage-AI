import io
import uuid
import zipfile
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.services.code_parser import code_parser_service

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a unique test user and return (user_id, token, headers)."""
    unique_email = f"parser_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Parser Tester",
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
    unique_email = f"second_parser_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Second Parser Tester",
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
    """Upload a project with Python, Java, JS, nested files, and unsupported files."""
    user_id, token, headers = test_user
    python_code = """import os
from fastapi import FastAPI

class UserService:

    def create_user(self):
        pass

def calculate_total(items):
    return sum(items)
"""
    java_code = """import java.util.List;

public class UserService {

    public void createUser() {
    }

    public int calculateTotal() {
        return 0;
    }
}
"""
    js_code = """import React from "react";
import axios from "axios";
const express = require("express");

class UserService {

    createUser() {
    }
}

function calculateTotal(items) {
    return items.reduce((a, b) => a + b, 0);
}
"""
    nested_python = """import math

def calculate_area(radius):
    return math.pi * radius * radius
"""
    malformed_python = "def broken_function("
    malformed_java = "public class Test {"
    malformed_js = "function test( {"

    files = {
        "src/main.py": python_code,
        "src/UserService.java": java_code,
        "src/app.js": js_code,
        "src/services/auth.py": nested_python,
        "src/broken.py": malformed_python,
        "src/broken.java": malformed_java,
        "src/broken.js": malformed_js,
        "docs/README.md": "# Readme",
        "assets/image.png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20,
        "docs/document.pdf": b"%PDF-1.4\n%test",
        "archive.zip": b"PK\x05\x06" + b"\x00" * 18,
    }
    zip_buf = create_zip_in_memory(files)
    res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("ParseTestProject.zip", zip_buf, "application/zip")},
    )
    assert res.status_code == 201
    return res.json()["project"]


# ============================================================
# 1. PARSER SERVICE UNIT TESTS
# ============================================================

def test_language_detection():
    assert code_parser_service.detect_language("main.py") == "python"
    assert code_parser_service.detect_language("src/model/User.java") == "java"
    assert code_parser_service.detect_language("index.js") == "javascript"
    assert code_parser_service.detect_language("style.css") is None
    assert code_parser_service.detect_language("document.pdf") is None
    assert code_parser_service.detect_language("image.png") is None


def test_python_parsing_unit():
    code = """import os
from fastapi import FastAPI

class UserService:

    def create_user(self):
        pass

def calculate_total(items):
    return sum(items)
"""
    res = code_parser_service.parse_source_code(code, "python", "src/main.py")
    assert res.language == "python"
    assert res.file == "src/main.py"

    # Classes
    assert len(res.classes) == 1
    assert res.classes[0].name == "UserService"
    assert res.classes[0].type == "class"
    assert res.classes[0].line_start == 4
    assert res.classes[0].line_end == 7

    # Functions
    func_names = [f.name for f in res.functions]
    assert "create_user" in func_names
    assert "calculate_total" in func_names

    method = next(f for f in res.functions if f.name == "create_user")
    assert method.type == "method"
    assert method.parent_class == "UserService"
    assert method.line_start == 6

    func = next(f for f in res.functions if f.name == "calculate_total")
    assert func.type == "function"
    assert func.parent_class is None
    assert func.line_start == 9

    # Imports
    import_names = [i.name for i in res.imports]
    assert "os" in import_names
    assert "fastapi" in import_names


def test_java_parsing_unit():
    code = """import java.util.List;

public class UserService {

    public void createUser() {
    }

    public int calculateTotal() {
        return 0;
    }
}
"""
    res = code_parser_service.parse_source_code(code, "java", "src/UserService.java")
    assert res.language == "java"

    # Classes
    assert len(res.classes) == 1
    assert res.classes[0].name == "UserService"
    assert res.classes[0].line_start == 3
    assert res.classes[0].line_end == 11

    # Methods
    method_names = [f.name for f in res.functions]
    assert "createUser" in method_names
    assert "calculateTotal" in method_names

    create_user = next(f for f in res.functions if f.name == "createUser")
    assert create_user.parent_class == "UserService"
    assert create_user.line_start == 5

    calc_total = next(f for f in res.functions if f.name == "calculateTotal")
    assert calc_total.parent_class == "UserService"
    assert calc_total.line_start == 8

    # Imports
    assert len(res.imports) == 1
    assert res.imports[0].name == "java.util.List"
    assert res.imports[0].line == 1


def test_javascript_parsing_unit():
    code = """import React from "react";
import axios from "axios";
const express = require("express");

class UserService {

    createUser() {
    }
}

function calculateTotal(items) {
    return items.reduce((a, b) => a + b, 0);
}
"""
    res = code_parser_service.parse_source_code(code, "javascript", "src/app.js")
    assert res.language == "javascript"

    # Classes
    assert len(res.classes) == 1
    assert res.classes[0].name == "UserService"

    # Functions
    func_names = [f.name for f in res.functions]
    assert "createUser" in func_names
    assert "calculateTotal" in func_names

    create_user = next(f for f in res.functions if f.name == "createUser")
    assert create_user.parent_class == "UserService"
    assert create_user.type == "method"

    calc_total = next(f for f in res.functions if f.name == "calculateTotal")
    assert calc_total.type == "function"
    assert calc_total.parent_class is None

    # Imports
    import_names = [i.name for i in res.imports]
    assert "react" in import_names
    assert "axios" in import_names
    assert "express" in import_names


# ============================================================
# 2. ENDPOINT INTEGRATION TESTS
# ============================================================

def test_api_parse_python(sample_project, test_user):
    user_id, token, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/parse?path=src/main.py", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "python"
    assert data["file"] == "src/main.py"
    assert any(c["name"] == "UserService" for c in data["classes"])
    assert any(f["name"] == "create_user" for f in data["functions"])
    assert any(f["name"] == "calculate_total" for f in data["functions"])
    assert any(i["name"] == "os" for i in data["imports"])
    assert any(i["name"] == "fastapi" for i in data["imports"])


def test_api_parse_java(sample_project, test_user):
    user_id, token, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/parse?path=src/UserService.java", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "java"
    assert any(c["name"] == "UserService" for c in data["classes"])
    assert any(f["name"] == "createUser" for f in data["functions"])
    assert any(f["name"] == "calculateTotal" for f in data["functions"])
    assert any(i["name"] == "java.util.List" for i in data["imports"])


def test_api_parse_javascript(sample_project, test_user):
    user_id, token, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/parse?path=src/app.js", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "javascript"
    assert any(c["name"] == "UserService" for c in data["classes"])
    assert any(f["name"] == "createUser" for f in data["functions"])
    assert any(f["name"] == "calculateTotal" for f in data["functions"])
    assert any(i["name"] == "react" for i in data["imports"])
    assert any(i["name"] == "axios" for i in data["imports"])
    assert any(i["name"] == "express" for i in data["imports"])


def test_api_parse_nested_file(sample_project, test_user):
    user_id, token, headers = test_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/parse?path=src/services/auth.py", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["language"] == "python"
    assert data["file"] == "src/services/auth.py"
    assert any(f["name"] == "calculate_area" for f in data["functions"])
    assert any(i["name"] == "math" for i in data["imports"])


def test_api_parse_malformed_syntax_no_crash(sample_project, test_user):
    """Ensure malformed source files do not crash the backend."""
    user_id, token, headers = test_user
    project_id = sample_project["id"]

    # Broken python
    res = client.get(f"/api/projects/{project_id}/parse?path=src/broken.py", headers=headers)
    assert res.status_code == 200

    # Broken java
    res = client.get(f"/api/projects/{project_id}/parse?path=src/broken.java", headers=headers)
    assert res.status_code == 200

    # Broken js
    res = client.get(f"/api/projects/{project_id}/parse?path=src/broken.js", headers=headers)
    assert res.status_code == 200


def test_api_parse_unsupported_files(sample_project, test_user):
    """Ensure unsupported file types are rejected with 400 Bad Request."""
    user_id, token, headers = test_user
    project_id = sample_project["id"]

    unsupported = [
        "assets/image.png",
        "docs/document.pdf",
        "archive.zip",
        "docs/README.md",
    ]
    for unsupp in unsupported:
        res = client.get(f"/api/projects/{project_id}/parse?path={unsupp}", headers=headers)
        assert res.status_code == 400
        assert "Tree-sitter parsing is not supported for this file type" in res.json()["detail"]


# ============================================================
# 3. SECURITY & TENANCY TESTS
# ============================================================

def test_api_parse_path_traversal_blocked(sample_project, test_user):
    user_id, token, headers = test_user
    project_id = sample_project["id"]

    traversal_paths = [
        "../secret.txt",
        "../../secret.txt",
        "../../../secret.txt",
        "..%2Fsecret.txt",
        "/etc/passwd",
        "C:\\Windows\\System32\\calc.exe",
    ]
    for bad_path in traversal_paths:
        res = client.get(f"/api/projects/{project_id}/parse?path={bad_path}", headers=headers)
        assert res.status_code == 400
        assert "Security violation" in res.json()["detail"]


def test_api_parse_tenancy_isolation(sample_project, second_user):
    """Second user must be denied access to first user's project."""
    user_id, token, headers = second_user
    project_id = sample_project["id"]

    res = client.get(f"/api/projects/{project_id}/parse?path=src/main.py", headers=headers)
    assert res.status_code == 404
    assert "permission" in res.json()["detail"] or "not found" in res.json()["detail"]


def test_api_parse_unauthenticated(sample_project):
    """Unauthenticated requests must be rejected with 401."""
    project_id = sample_project["id"]
    res = client.get(f"/api/projects/{project_id}/parse?path=src/main.py")
    assert res.status_code == 401
