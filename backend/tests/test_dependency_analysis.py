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

client = TestClient(app)


@pytest.fixture
def test_user():
    """Create a unique test user and return (user_id, token, headers)."""
    unique_email = f"dep_tester_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Dependency Tester",
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
    unique_email = f"second_dep_tester_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Second Dependency Tester",
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
def sample_dep_project(test_user):
    """
    Upload a multi-language project matching Day 9 specifications (Phase 30):
    sample-project/
    ├── backend/
    │   ├── app/
    │   │   ├── main.py
    │   │   ├── database.py
    │   │   └── models.py
    │   └── requirements.txt
    ├── frontend/
    │   ├── src/
    │   │   ├── App.jsx
    │   │   ├── components/
    │   │   │   └── Navbar.jsx
    │   │   └── services/
    │   │       └── api.js
    │   └── package.json
    ├── java_src/
    │   ├── pom.xml
    │   └── src/main/java/com/example/
    │       ├── service/UserService.java
    │       └── model/User.java
    └── README.md
    """
    user_id, token, headers = test_user
    files = {
        "backend/requirements.txt": (
            "fastapi==0.104.1\n"
            "sqlalchemy>=2.0.0\n"
            "psycopg2-binary\n"
        ),
        "backend/app/main.py": (
            "import os\n"
            "import fastapi\n"
            "from app.database import get_db\n"
            "from app.models import User\n"
        ),
        "backend/app/database.py": (
            "import sqlite3\n"
            "def get_db(): return None\n"
        ),
        "backend/app/models.py": (
            "class User:\n"
            "    pass\n"
        ),
        "frontend/package.json": json.dumps({
            "dependencies": {
                "react": "^18.2.0",
                "axios": "^1.6.0"
            },
            "devDependencies": {
                "vite": "^5.0.0"
            }
        }),
        "frontend/src/App.jsx": (
            'import React from "react";\n'
            'import Navbar from "./components/Navbar";\n'
            'import { api } from "./services/api";\n'
            'export default function App() { return <div><Navbar /></div>; }\n'
        ),
        "frontend/src/components/Navbar.jsx": (
            'export default function Navbar() { return <nav>Nav</nav>; }\n'
        ),
        "frontend/src/services/api.js": (
            'import axios from "axios";\n'
            'export const api = axios.create();\n'
        ),
        "java_src/pom.xml": (
            '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
            '  <dependencies>\n'
            '    <dependency>\n'
            '      <groupId>org.springframework.boot</groupId>\n'
            '      <artifactId>spring-boot</artifactId>\n'
            '      <version>3.1.5</version>\n'
            '    </dependency>\n'
            '  </dependencies>\n'
            '</project>\n'
        ),
        "java_src/src/main/java/com/example/service/UserService.java": (
            "package com.example.service;\n"
            "import java.util.List;\n"
            "import com.example.model.User;\n"
            "public class UserService {}\n"
        ),
        "java_src/src/main/java/com/example/model/User.java": (
            "package com.example.model;\n"
            "public class User {}\n"
        ),
        "README.md": "# Sample Project for Day 9\n",
    }

    zip_bytes = create_zip_in_memory(files)
    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("sample_day9.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201, f"Project upload failed: {upload_res.text}"
    return upload_res.json()["project"]


def test_dependency_analysis_multi_language(test_user, sample_dep_project):
    """
    Test Day 9 dependency analysis on a full multi-language project:
    - Verifies Python, JavaScript, and Java imports detected
    - Verifies package manifests parsed correctly (requirements.txt, package.json, pom.xml)
    - Verifies local imports resolved to exact project relative paths
    - Verifies external packages identified
    - Verifies relationships and graph nodes/edges generated correctly
    """
    user_id, token, headers = test_user
    project_id = sample_dep_project["id"]

    res = client.get(f"/api/projects/{project_id}/dependencies", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["project_id"] == project_id
    assert data["project_name"] == sample_dep_project["name"]

    # 1. Packages Verification
    packages = data["packages"]
    assert len(packages) >= 5

    pkg_map = {p["name"]: p for p in packages}
    assert "fastapi" in pkg_map
    assert pkg_map["fastapi"]["ecosystem"] == "python"
    assert pkg_map["fastapi"]["version"] == "==0.104.1"
    assert pkg_map["fastapi"]["type"] == "dependency"

    assert "react" in pkg_map
    assert pkg_map["react"]["ecosystem"] == "javascript"
    assert pkg_map["react"]["version"] == "^18.2.0"
    assert pkg_map["react"]["type"] == "dependency"

    assert "vite" in pkg_map
    assert pkg_map["vite"]["ecosystem"] == "javascript"
    assert pkg_map["vite"]["type"] == "devDependency"

    assert "spring-boot" in pkg_map
    assert pkg_map["spring-boot"]["ecosystem"] == "java"
    assert pkg_map["spring-boot"]["version"] == "3.1.5"

    # 2. Imports Verification
    imports = data["imports"]
    assert len(imports) >= 8

    # Check Python imports in main.py
    main_imports = [i for i in imports if i["source"] == "backend/app/main.py"]
    main_imp_map = {i["name"]: i for i in main_imports}

    assert "os" in main_imp_map
    assert main_imp_map["os"]["type"] == "external"

    assert "fastapi" in main_imp_map
    assert main_imp_map["fastapi"]["type"] == "external"

    assert "app.database" in main_imp_map
    assert main_imp_map["app.database"]["type"] == "local"
    assert main_imp_map["app.database"]["target"] == "backend/app/database.py"

    assert "app.models" in main_imp_map
    assert main_imp_map["app.models"]["type"] == "local"
    assert main_imp_map["app.models"]["target"] == "backend/app/models.py"

    # Check JS imports in App.jsx
    app_imports = [i for i in imports if i["source"] == "frontend/src/App.jsx"]
    app_imp_map = {i["name"]: i for i in app_imports}

    assert "react" in app_imp_map
    assert app_imp_map["react"]["type"] == "external"

    assert "./components/Navbar" in app_imp_map
    assert app_imp_map["./components/Navbar"]["type"] == "local"
    assert app_imp_map["./components/Navbar"]["target"] == "frontend/src/components/Navbar.jsx"

    assert "./services/api" in app_imp_map
    assert app_imp_map["./services/api"]["type"] == "local"
    assert app_imp_map["./services/api"]["target"] == "frontend/src/services/api.js"

    # Check Java imports in UserService.java
    java_imports = [
        i for i in imports
        if "UserService.java" in i["source"]
    ]
    java_imp_map = {i["name"]: i for i in java_imports}

    assert "java.util.List" in java_imp_map
    assert java_imp_map["java.util.List"]["type"] == "external"

    assert "com.example.model.User" in java_imp_map
    assert java_imp_map["com.example.model.User"]["type"] == "local"
    assert "User.java" in java_imp_map["com.example.model.User"]["target"]

    # 3. Relationships Verification
    relationships = data["relationships"]
    assert len(relationships) >= 5

    # Check local relationships
    local_rels = [
        (r["source"], r["target"])
        for r in relationships
        if r.get("dependency_type") == "local"
    ]
    assert ("backend/app/main.py", "backend/app/database.py") in local_rels
    assert ("backend/app/main.py", "backend/app/models.py") in local_rels
    assert ("frontend/src/App.jsx", "frontend/src/components/Navbar.jsx") in local_rels

    # Check external relationships
    external_rels = [
        (r["source"], r["target"])
        for r in relationships
        if r.get("dependency_type") == "external"
    ]
    assert ("frontend/src/App.jsx", "react") in external_rels
    assert ("frontend/src/services/api.js", "axios") in external_rels

    # 4. Graph Verification
    graph = data["graph"]
    assert "nodes" in graph and len(graph["nodes"]) > 0
    assert "edges" in graph and len(graph["edges"]) > 0

    node_ids = {n["id"] for n in graph["nodes"]}
    assert "backend/app/main.py" in node_ids
    assert "backend/app/database.py" in node_ids
    assert "react" in node_ids
    assert "fastapi" in node_ids


def test_unresolved_import_handling(test_user):
    """
    Phase 35: Unresolved import test
    Imports that cannot be resolved must return type: 'unknown', target: None,
    and must not fabricate a target file or crash.
    """
    user_id, token, headers = test_user
    files = {
        "main.py": "from some_completely_unknown_module import something\n",
        "app.js": 'import missingItem from "./missing/path/item";\n',
    }
    zip_bytes = create_zip_in_memory(files)
    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("unresolved.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    proj_id = upload_res.json()["project"]["id"]

    res = client.get(f"/api/projects/{proj_id}/dependencies", headers=headers)
    assert res.status_code == 200
    data = res.json()

    for imp in data["imports"]:
        assert imp["type"] == "unknown"
        assert imp["target"] is None


def test_empty_project_dependencies(test_user):
    """
    Phase 25: Empty dependencies test
    An empty project returns valid empty arrays and 200 OK.
    """
    user_id, token, headers = test_user
    files = {
        "README.md": "# Just a readme\nNo code here\n",
    }
    zip_bytes = create_zip_in_memory(files)
    upload_res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("empty_deps.zip", zip_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    proj_id = upload_res.json()["project"]["id"]

    res = client.get(f"/api/projects/{proj_id}/dependencies", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["imports"] == []
    assert data["packages"] == []
    assert data["relationships"] == []
    assert data["graph"]["nodes"] == []
    assert data["graph"]["edges"] == []


def test_dependencies_tenancy_isolation(test_user, second_user, sample_dep_project):
    """
    Phase 3 & 28: Tenancy isolation
    A user cannot analyze another user's project by changing project_id.
    """
    user2_id, token2, headers2 = second_user
    project_id = sample_dep_project["id"]

    # User 2 tries to access User 1's project
    res = client.get(f"/api/projects/{project_id}/dependencies", headers=headers2)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_dependencies_unauthenticated(sample_dep_project):
    """
    Phase 28: Unauthenticated access blocked
    """
    project_id = sample_dep_project["id"]
    res = client.get(f"/api/projects/{project_id}/dependencies")
    assert res.status_code == 401


def test_dependencies_nonexistent_project(test_user):
    """
    Phase 24 & 28: Nonexistent project ID returns 404
    """
    user_id, token, headers = test_user
    res = client.get("/api/projects/99999999/dependencies", headers=headers)
    assert res.status_code == 404


def test_no_absolute_paths_exposed(test_user, sample_dep_project):
    """
    Phase 24 & 28: Absolute server paths must never be exposed.
    """
    user_id, token, headers = test_user
    project_id = sample_dep_project["id"]

    res = client.get(f"/api/projects/{project_id}/dependencies", headers=headers)
    assert res.status_code == 200
    raw_text = res.text

    # Verify no drive letters or server internals
    assert "C:\\" not in raw_text
    assert "c:/" not in raw_text.lower()
    assert "\\users\\" not in raw_text.lower()
    assert "/home/" not in raw_text
