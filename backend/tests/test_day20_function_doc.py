"""
CodeSage AI — Day 20 Automated Test Suite: Generate Function Documentation

Tests:
1. Prompt engineering, structured sections, and strict grounding instructions.
2. Function discovery and listing across projects (Python, Django, React).
3. File-specific function filtering with `file_path`.
4. Bounded context extraction (preamble, enclosing class, semantic neighbors).
5. Grounded documentation generation with all 10 required sections.
6. Structured section parsing (purpose, parameters, returns, behavior, logic, dependencies, exceptions, source).
7. Nonexistent function and file handling (HTTP 404).
8. Path traversal security defense (HTTP 400).
9. Multi-tenant project isolation (User A vs User B).
10. Live Ollama Gemma 2B generation (conditional on local daemon health).
"""

import os
import uuid
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.services.prompts import (
    FUNCTION_DOC_SYSTEM_INSTRUCTIONS,
    FUNCTION_DOC_RESPONSE_REQUIREMENTS,
    FUNCTION_DOC_PROMPT_TEMPLATE,
)
from app.services.function_doc_service import function_doc_service
from app.services.ollama_service import ollama_service
from tests.fixtures.sample_projects import (
    PYTHON_PROJECT_FILES,
    DJANGO_PROJECT_FILES,
    REACT_PROJECT_FILES,
    build_project_zip,
)

client = TestClient(app)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def user_a():
    """Create test User A."""
    email = f"day20_user_a_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Day 20 User A",
            email=email,
            password_hash=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id), "email": email})
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers


@pytest.fixture
def user_b():
    """Create test User B for multi-tenant isolation tests."""
    email = f"day20_user_b_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Day 20 User B",
            email=email,
            password_hash=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id), "email": email})
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers


@pytest.fixture
def uploaded_python_project(user_a):
    """Uploads Python test project for User A."""
    user_id, token, headers = user_a
    zip_buf = build_project_zip(PYTHON_PROJECT_FILES)
    res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("python_project.zip", zip_buf.getvalue(), "application/zip")},
    )
    assert res.status_code == 201, f"Upload failed: {res.text}"
    project_id = res.json()["project"]["id"]
    return project_id, headers


@pytest.fixture
def uploaded_react_project(user_a):
    """Uploads React test project for User A."""
    user_id, token, headers = user_a
    zip_buf = build_project_zip(REACT_PROJECT_FILES)
    res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("react_project.zip", zip_buf.getvalue(), "application/zip")},
    )
    assert res.status_code == 201, f"Upload failed: {res.text}"
    project_id = res.json()["project"]["id"]
    return project_id, headers


# ==============================================================================
# 1. PROMPT ARCHITECTURE TESTS
# ==============================================================================

def test_day20_prompt_templates_and_grounding_rules():
    """Verify Day 20 prompt instructions contain all strict grounding rules and 10 required sections."""
    # 1. System instructions checks
    assert "Pure Code Grounding" in FUNCTION_DOC_SYSTEM_INSTRUCTIONS
    assert "Never invent parameters" in FUNCTION_DOC_SYSTEM_INSTRUCTIONS
    assert "Prompt Injection Defense" in FUNCTION_DOC_SYSTEM_INSTRUCTIONS
    assert "Privacy & Security" in FUNCTION_DOC_SYSTEM_INSTRUCTIONS

    # 2. Response format requirements checks: all 10 required sections
    assert "**Purpose**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS
    assert "**Parameters**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS
    assert "**Returns**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS
    assert "**Behavior**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS
    assert "**Important Logic**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS
    assert "**Dependencies**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS
    assert "**Exceptions / Errors**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS
    assert "**Usage Example**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS
    assert "**Related Symbols**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS
    assert "**Source**" in FUNCTION_DOC_RESPONSE_REQUIREMENTS

    # 3. Master prompt template checks
    assert "{system_instructions}" in FUNCTION_DOC_PROMPT_TEMPLATE
    assert "{function_name}" in FUNCTION_DOC_PROMPT_TEMPLATE
    assert "{surrounding_context}" in FUNCTION_DOC_PROMPT_TEMPLATE
    assert "{function_source}" in FUNCTION_DOC_PROMPT_TEMPLATE
    assert "{response_requirements}" in FUNCTION_DOC_PROMPT_TEMPLATE


# ==============================================================================
# 2. FUNCTION DISCOVERY & LISTING TESTS
# ==============================================================================

def test_day20_list_functions_python(uploaded_python_project):
    """Verify listing functions discovers functions and methods in Python project."""
    project_id, headers = uploaded_python_project

    res = client.get(f"/api/projects/{project_id}/functions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == project_id
    assert data["total_functions"] > 0
    functions = data["functions"]

    fn_names = {f["function_name"] for f in functions}
    assert "main" in fn_names
    assert "load_config" in fn_names
    assert "calculate_tax" in fn_names
    assert "process_batch" in fn_names

    # Check method metadata
    tax_fn = next(f for f in functions if f["function_name"] == "calculate_tax")
    assert tax_fn["type"] == "method"
    assert tax_fn["parent_class"] == "DataRecord"
    assert tax_fn["file_path"] == "models/record.py"
    assert tax_fn["start_line"] > 0
    assert tax_fn["end_line"] >= tax_fn["start_line"]
    assert tax_fn["language"] == "python"


def test_day20_list_functions_file_filter(uploaded_python_project):
    """Verify file_path query parameter restricts listing to only that file."""
    project_id, headers = uploaded_python_project

    res = client.get(f"/api/projects/{project_id}/functions?file_path=config.py", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_functions"] == 1
    assert data["functions"][0]["function_name"] == "load_config"
    assert data["functions"][0]["file_path"] == "config.py"


def test_day20_list_functions_javascript(uploaded_react_project):
    """Verify Tree-sitter discovers JavaScript functions in React project."""
    project_id, headers = uploaded_react_project

    res = client.get(f"/api/projects/{project_id}/functions", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_functions"] > 0
    fn_names = {f["function_name"] for f in data["functions"]}
    assert "Navbar" in fn_names


# ==============================================================================
# 3. BOUNDED CONTEXT EXTRACTION TESTS
# ==============================================================================

def test_day20_bounded_context_extraction(uploaded_python_project):
    """Verify function source, module preamble, and enclosing class header are extracted accurately."""
    project_id, headers = uploaded_python_project

    db = next(get_db())
    try:
        project = db.get(Project, project_id)
        extracted_dir = function_doc_service._get_project_extracted_dir(project)
        resolved_file = function_doc_service._safe_resolve_file_path(extracted_dir, "models/record.py")
        content = function_doc_service._read_file_safe(resolved_file)

        # 1. Source extraction
        source = function_doc_service._extract_function_source(content, 9, 11)
        assert "calculate_tax" in source
        assert "tax_rate" in source

        # 2. Preamble extraction
        preamble = function_doc_service._extract_file_preamble(content)
        assert "pydantic" in preamble

        # 3. Enclosing class header extraction
        class_hdr = function_doc_service._extract_parent_class_header(content, "DataRecord", "python")
        assert "class DataRecord" in class_hdr
    finally:
        db.close()


# ==============================================================================
# 4. STRUCTURED DOCUMENTATION GENERATION TESTS (MOCKED LLM)
# ==============================================================================

MOCK_DOC_MARKDOWN = """### calculate_tax

**Purpose**
Calculates the regional tax amount on the record value using the specified tax rate.

**Parameters**
- `tax_rate` (float, optional) — The fractional tax rate applied to the value. Defaults to 0.18.

**Returns**
A float representing the rounded tax amount computed from the record value.

**Behavior**
1. Receives the optional `tax_rate` argument (defaults to 0.18).
2. Multiplies the record's `value` attribute by `tax_rate`.
3. Rounds the result to two decimal places.
4. Returns the final rounded float.

**Important Logic**
- Uses Python `round(..., 2)` to avoid floating-point currency representation errors.

**Dependencies**
- `models.record.DataRecord` — Method belongs to this Pydantic model.

**Exceptions / Errors**
- `None identifiable` — Performs no explicit raise statements.

**Usage Example**
```python
record = DataRecord(id=1, value=100.0)
tax = record.calculate_tax(0.20)
print(tax)  # 20.0
```

**Related Symbols**
- `DataRecord` — Enclosing model class storing the value attribute.

**Source**
`models/record.py`
Lines 9–11"""


def test_day20_generate_function_doc_mocked(uploaded_python_project):
    """Test POST /api/projects/{id}/functions/document with mocked LLM output."""
    project_id, headers = uploaded_python_project

    with patch.object(function_doc_service, "_invoke_chain", return_value=MOCK_DOC_MARKDOWN):
        res = client.post(
            f"/api/projects/{project_id}/functions/document",
            headers=headers,
            json={
                "file_path": "models/record.py",
                "function_name": "calculate_tax",
                "start_line": 9,
                "end_line": 11,
                "parent_class": "DataRecord",
            },
        )

        assert res.status_code == 200
        data = res.json()
        assert data["project_id"] == project_id
        assert data["function_name"] == "calculate_tax"
        assert data["file_path"] == "models/record.py"
        assert data["language"] == "python"
        assert data["parent_class"] == "DataRecord"

        # Check parsed structured fields
        assert data["purpose"] is not None
        assert "Calculates the regional tax" in data["purpose"]
        assert len(data["parameters"]) == 1
        assert data["parameters"][0]["name"] == "tax_rate"
        assert data["parameters"][0]["type"] == "float, optional"
        assert data["returns"] is not None
        assert len(data["behavior"]) == 4
        assert len(data["logic"]) >= 1
        assert len(data["dependencies"]) >= 1
        assert data["usage_example"] is not None
        assert "calculate_tax" in data["source_code"]


def test_day20_strict_grounding_no_parameters(uploaded_python_project):
    """Test generating docs for a zero-parameter function (load_config)."""
    project_id, headers = uploaded_python_project

    mock_no_param_doc = """### load_config

**Purpose**
Loads application configuration settings from environment variables.

**Parameters**
- `None` — Accepts no parameters.

**Returns**
An `AppConfig` instance populated with environment values or defaults.

**Behavior**
1. Reads `BATCH_SIZE`, `PIPELINE_ENV`, and `TIMEOUT` from the environment.
2. Instantiates and returns an `AppConfig` object.

**Important Logic**
- Type casts string environment variables into integers with fallback defaults.

**Dependencies**
- `os` — Reads environment variables via `os.getenv`.
- `config.AppConfig` — Pydantic model for configuration.

**Exceptions / Errors**
- `ValueError` — Raised if `os.getenv` values cannot be parsed to integer.

**Usage Example**
```python
from config import load_config
cfg = load_config()
print(cfg.app_name)
```

**Related Symbols**
- `AppConfig` — Configuration schema class.

**Source**
`config.py`
Lines 11–17"""

    with patch.object(function_doc_service, "_invoke_chain", return_value=mock_no_param_doc):
        res = client.post(
            f"/api/projects/{project_id}/functions/document",
            headers=headers,
            json={
                "file_path": "config.py",
                "function_name": "load_config",
            },
        )

        assert res.status_code == 200
        data = res.json()
        assert data["function_name"] == "load_config"
        assert data["parameters"] == []  # Accurately identified zero parameters
        assert data["returns"] is not None


# ==============================================================================
# 5. ERROR HANDLING & SECURITY TESTS
# ==============================================================================

def test_day20_nonexistent_function_handling(uploaded_python_project):
    """Verify 404 is returned when requesting a function that does not exist in the file."""
    project_id, headers = uploaded_python_project

    res = client.post(
        f"/api/projects/{project_id}/functions/document",
        headers=headers,
        json={
            "file_path": "main.py",
            "function_name": "non_existent_function_12345",
        },
    )
    assert res.status_code == 404
    assert "was not found" in res.json()["detail"].lower()


def test_day20_nonexistent_file_handling(uploaded_python_project):
    """Verify 404 is returned when requesting a file not in project."""
    project_id, headers = uploaded_python_project

    res = client.post(
        f"/api/projects/{project_id}/functions/document",
        headers=headers,
        json={
            "file_path": "services/missing_file.py",
            "function_name": "any_func",
        },
    )
    assert res.status_code == 404


def test_day20_path_traversal_defense(uploaded_python_project):
    """Verify path traversal (..) is rejected with 400 Bad Request."""
    project_id, headers = uploaded_python_project

    res = client.post(
        f"/api/projects/{project_id}/functions/document",
        headers=headers,
        json={
            "file_path": "../../../etc/passwd",
            "function_name": "root",
        },
    )
    assert res.status_code == 400
    assert "traversal" in res.json()["detail"].lower()


def test_day20_multi_tenant_isolation(uploaded_python_project, user_b):
    """Verify User B cannot view functions or generate documentation for User A's project."""
    project_id, headers_a = uploaded_python_project
    user_b_id, token_b, headers_b = user_b

    # 1. Listing functions forbidden
    res_list = client.get(f"/api/projects/{project_id}/functions", headers=headers_b)
    assert res_list.status_code == 404

    # 2. Documenting function forbidden
    res_doc = client.post(
        f"/api/projects/{project_id}/functions/document",
        headers=headers_b,
        json={
            "file_path": "config.py",
            "function_name": "load_config",
        },
    )
    assert res_doc.status_code == 404


# ==============================================================================
# 6. LIVE OLLAMA GENERATION TEST (Step 38 validation)
# ==============================================================================

def test_day20_live_gemma_generation(uploaded_python_project):
    """
    Executes an actual end-to-end generation with local Gemma 2B if Ollama is running.
    Skips if Ollama daemon is offline.
    """
    health = ollama_service.check_health()
    if not health.ollama.available or not health.model.available:
        pytest.skip("Local Ollama or Gemma 2B model not available for live generation test.")

    project_id, headers = uploaded_python_project

    res = client.post(
        f"/api/projects/{project_id}/functions/document",
        headers=headers,
        json={
            "file_path": "config.py",
            "function_name": "load_config",
        },
    )

    assert res.status_code == 200
    data = res.json()
    doc = data["documentation"]

    # Verify key sections were generated by Gemma
    assert len(doc) > 50
    assert "load_config" in doc
    assert "config.py" in doc
    assert "Purpose" in doc
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Behavior" in doc
    assert "Source" in doc or "Lines" in doc
