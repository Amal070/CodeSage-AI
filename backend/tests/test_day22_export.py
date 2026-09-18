"""
CodeSage AI — Day 22 Automated Test Suite: Markdown & PDF Export

Tests:
1. Reusable Export Service:
   - generate_project_markdown(): Grounded report structure, statistics, ASCII tree, language breakdown.
   - generate_project_pdf(): Binary ReportLab generation, %PDF-1. magic bytes, multi-page numbering.
   - generate_function_markdown() & generate_function_pdf(): Single function documentation export.
   - generate_api_docs_pdf(): Full FastAPI catalog ReportLab PDF generation.
2. Secure FastAPI Export Endpoints:
   - GET /api/projects/{project_id}/export/markdown (File attachment, text/markdown)
   - GET /api/projects/{project_id}/export/pdf (File attachment, application/pdf)
   - POST /api/projects/{project_id}/functions/export/markdown (Function doc .md attachment)
   - POST /api/projects/{project_id}/functions/export/pdf (Function doc .pdf attachment)
   - GET /api/docs-api/export/markdown (API catalog .md attachment)
   - GET /api/docs-api/export/pdf (API catalog .pdf attachment)
3. Security & Multi-Tenant Authorization:
   - Strict 401 Unauthorized when unauthenticated.
   - Cross-project isolation: User B cannot export User A's project (404 Not Found).
   - Nonexistent project id returns 404.
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.schemas.function_doc import FunctionDocRequest
from app.services.export_service import export_service
from app.services.function_doc_service import function_doc_service
from tests.fixtures.sample_projects import (
    PYTHON_PROJECT_FILES,
    DJANGO_PROJECT_FILES,
    REACT_PROJECT_FILES,
    build_project_zip,
)

client = TestClient(app)

MOCK_FUNCTION_DOC_MARKDOWN = """### calculate_tax

**Purpose**
Calculates the total tax for an item based on price and state tax rate.

**Parameters**
- `price` (float): The subtotal price of the item.
- `tax_rate` (float): The local decimal tax rate.

**Returns**
- `float`: Computed tax amount rounded to two decimals.

**Behavior**
1. Multiplies price by tax_rate.
2. Formats to 2 decimal places.

**Important Logic**
Standard rounding rules apply.

**Dependencies**
- `decimal` module

**Exceptions**
- `ValueError` if price is negative.

**Usage / Example**
```python
tax = calculate_tax(100.0, 0.08)
```

**Related Classes / Functions**
- `InvoiceService.calculate_total()`

**Source Reference**
- File: `services/tax.py`
- Lines: 10–25
"""


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def user_a():
    """Create test User A."""
    email = f"day22_user_a_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Day 22 User A",
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
    email = f"day22_user_b_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Day 22 User B",
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
def uploaded_project(user_a):
    """Uploads and indexes a Python test project for User A."""
    user_id, token, headers = user_a
    zip_buf = build_project_zip(PYTHON_PROJECT_FILES)
    res = client.post(
        "/api/projects/upload",
        headers=headers,
        files={"file": ("python_sample.zip", zip_buf.getvalue(), "application/zip")},
    )
    assert res.status_code == 201, f"Upload failed: {res.text}"
    project_id = res.json()["project"]["id"]

    # Index project so code chunks are available
    idx_res = client.post(f"/api/projects/{project_id}/index", headers=headers)
    assert idx_res.status_code == 200, f"Indexing failed: {idx_res.text}"

    return project_id, headers


# ==============================================================================
# 1. EXPORT SERVICE UNIT TESTS
# ==============================================================================

def test_generate_project_markdown_structure(uploaded_project):
    """Verifies that Markdown report generation produces clean, structured, and complete documentation."""
    project_id, headers = uploaded_project
    db = next(get_db())
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        assert project is not None

        md = export_service.generate_project_markdown(db=db, project=project)

        # 1. Header & Overview
        assert "Project Documentation Report" in md
        assert "CodeSage AI" in md
        assert "## Project Overview" in md
        assert "Project Owner" in md

        # 2. Statistics & Diagnostics
        assert "## System Statistics & Diagnostics" in md
        assert "Total Source Files" in md
        assert "Total Folders" in md
        assert "Total Lines of Code" in md

        # 3. Language Breakdown
        assert "## Programming Language Distribution" in md
        assert "Python" in md

        # 4. Dependencies
        assert "## Architecture & Dependencies" in md

        # 5. Directory Hierarchy
        assert "## Project Directory Hierarchy" in md

        # 6. Functions Catalog
        assert "## Functions & Methods Catalog" in md
        assert "load_config" in md
        assert "calculate_tax" in md

        # 7. Grounding checks: No leaked local drive roots
        assert "C:\\projects" not in md
        assert "C:\\Users" not in md
    finally:
        db.close()


def test_generate_project_pdf_binary(uploaded_project):
    """Verifies that PDF report generation produces valid binary ReportLab PDF."""
    project_id, headers = uploaded_project
    db = next(get_db())
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        assert project is not None

        pdf_bytes = export_service.generate_project_pdf(db=db, project=project)

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000, f"PDF output too small ({len(pdf_bytes)} bytes)"
        assert pdf_bytes.startswith(b"%PDF-1."), "Invalid PDF magic header bytes"
    finally:
        db.close()


def test_generate_function_markdown_and_pdf(uploaded_project):
    """Verifies standalone function documentation export in Markdown and PDF formats."""
    project_id, headers = uploaded_project
    db = next(get_db())
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        req = FunctionDocRequest(
            function_name="calculate_tax",
            file_path="models/record.py",
            start_line=9,
            end_line=11,
            language="python",
        )

        with patch.object(function_doc_service, "_invoke_chain", return_value=MOCK_FUNCTION_DOC_MARKDOWN):
            # Markdown export
            fn_md = export_service.generate_function_markdown(db=db, project=project, req=req)
            assert "### calculate_tax" in fn_md
            assert "**Purpose**" in fn_md
            assert "**Parameters**" in fn_md
            assert "**Returns**" in fn_md

            # PDF export
            fn_pdf = export_service.generate_function_pdf(db=db, project=project, req=req)
            assert isinstance(fn_pdf, bytes)
            assert len(fn_pdf) > 800
            assert fn_pdf.startswith(b"%PDF-1.")
    finally:
        db.close()


def test_generate_api_docs_pdf():
    """Verifies API specification PDF catalog generation across all FastAPI endpoints."""
    pdf_bytes = export_service.generate_api_docs_pdf(app)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000, f"API PDF too small ({len(pdf_bytes)} bytes)"
    assert pdf_bytes.startswith(b"%PDF-1.")


# ==============================================================================
# 2. FASTAPI ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_endpoint_export_project_markdown(uploaded_project):
    """Tests GET /api/projects/{project_id}/export/markdown returns file attachment."""
    project_id, headers = uploaded_project
    res = client.get(f"/api/projects/{project_id}/export/markdown", headers=headers)

    assert res.status_code == 200
    assert "text/markdown" in res.headers.get("content-type", "")
    cd = res.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "Report.md" in cd
    assert "Project Documentation Report" in res.text


def test_endpoint_export_project_pdf(uploaded_project):
    """Tests GET /api/projects/{project_id}/export/pdf returns PDF file attachment."""
    project_id, headers = uploaded_project
    res = client.get(f"/api/projects/{project_id}/export/pdf", headers=headers)

    assert res.status_code == 200
    assert "application/pdf" in res.headers.get("content-type", "")
    cd = res.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "Report.pdf" in cd
    assert res.content.startswith(b"%PDF-1.")
    assert len(res.content) > 1000


def test_endpoint_export_function_markdown_and_pdf(uploaded_project):
    """Tests function documentation export endpoints."""
    project_id, headers = uploaded_project
    payload = {
        "function_name": "calculate_tax",
        "file_path": "models/record.py",
        "start_line": 9,
        "end_line": 11,
        "language": "python",
    }

    with patch.object(function_doc_service, "_invoke_chain", return_value=MOCK_FUNCTION_DOC_MARKDOWN):
        # Markdown
        res_md = client.post(
            f"/api/projects/{project_id}/functions/export/markdown",
            json=payload,
            headers=headers,
        )
        assert res_md.status_code == 200
        assert "text/markdown" in res_md.headers.get("content-type", "")
        assert "calculate_tax_doc.md" in res_md.headers.get("content-disposition", "")
        assert "### calculate_tax" in res_md.text

        # PDF
        res_pdf = client.post(
            f"/api/projects/{project_id}/functions/export/pdf",
            json=payload,
            headers=headers,
        )
        assert res_pdf.status_code == 200
        assert "application/pdf" in res_pdf.headers.get("content-type", "")
        assert "calculate_tax_doc.pdf" in res_pdf.headers.get("content-disposition", "")
        assert res_pdf.content.startswith(b"%PDF-1.")


def test_endpoint_export_api_markdown_and_pdf(user_a):
    """Tests GET /api/docs-api/export/markdown and GET /api/docs-api/export/pdf."""
    user_id, token, headers = user_a

    # Markdown download
    res_md = client.get("/api/docs-api/export/markdown", headers=headers)
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers.get("content-type", "")
    assert "CodeSage_AI_API_Reference.md" in res_md.headers.get("content-disposition", "")
    assert "# CodeSage AI" in res_md.text

    # PDF download
    res_pdf = client.get("/api/docs-api/export/pdf", headers=headers)
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers.get("content-type", "")
    assert "CodeSage_AI_API_Reference.pdf" in res_pdf.headers.get("content-disposition", "")
    assert res_pdf.content.startswith(b"%PDF-1.")
    assert len(res_pdf.content) > 1000


# ==============================================================================
# 3. SECURITY & TENANCY ISOLATION TESTS
# ==============================================================================

def test_export_authentication_required(uploaded_project):
    """Verifies that all export endpoints strictly require Bearer JWT authentication."""
    project_id, _ = uploaded_project

    # Project exports without token
    res1 = client.get(f"/api/projects/{project_id}/export/markdown")
    assert res1.status_code == 401

    res2 = client.get(f"/api/projects/{project_id}/export/pdf")
    assert res2.status_code == 401

    # Function exports without token
    payload = {
        "function_name": "test_fn",
        "file_path": "test.py",
        "start_line": 1,
        "end_line": 5,
        "language": "python",
    }
    res3 = client.post(f"/api/projects/{project_id}/functions/export/markdown", json=payload)
    assert res3.status_code == 401

    res4 = client.post(f"/api/projects/{project_id}/functions/export/pdf", json=payload)
    assert res4.status_code == 401

    # API catalog exports without token
    res5 = client.get("/api/docs-api/export/markdown")
    assert res5.status_code == 401

    res6 = client.get("/api/docs-api/export/pdf")
    assert res6.status_code == 401


def test_export_cross_tenant_isolation(uploaded_project, user_b):
    """Verifies that User B cannot export User A's project (404 Not Found)."""
    project_id, _ = uploaded_project
    _, _, headers_b = user_b

    # User B tries to export User A's project report as Markdown
    res_md = client.get(f"/api/projects/{project_id}/export/markdown", headers=headers_b)
    assert res_md.status_code == 404

    # User B tries to export User A's project report as PDF
    res_pdf = client.get(f"/api/projects/{project_id}/export/pdf", headers=headers_b)
    assert res_pdf.status_code == 404

    # User B tries to export User A's function docs
    payload = {
        "function_name": "test_fn",
        "file_path": "test.py",
        "start_line": 1,
        "end_line": 5,
        "language": "python",
    }
    res_fn_md = client.post(
        f"/api/projects/{project_id}/functions/export/markdown",
        json=payload,
        headers=headers_b,
    )
    assert res_fn_md.status_code == 404

    res_fn_pdf = client.post(
        f"/api/projects/{project_id}/functions/export/pdf",
        json=payload,
        headers=headers_b,
    )
    assert res_fn_pdf.status_code == 404


def test_export_nonexistent_project(user_a):
    """Verifies that attempting to export an invalid or non-existent project returns 404."""
    _, _, headers = user_a
    invalid_id = 9999999

    res_md = client.get(f"/api/projects/{invalid_id}/export/markdown", headers=headers)
    assert res_md.status_code == 404

    res_pdf = client.get(f"/api/projects/{invalid_id}/export/pdf", headers=headers)
    assert res_pdf.status_code == 404
