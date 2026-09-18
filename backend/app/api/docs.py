import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, Response

from app.api.auth import get_current_user
from app.models.user import User
from app.schemas.api_documentation import (
    ApiCatalogResponse,
    EndpointDocItem,
    GenerateApiDocRequest,
    GenerateApiDocResponse,
    ApiMarkdownExportResponse,
)
from app.services.api_documentation_service import api_documentation_service
from app.services.export_service import export_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/docs-api", tags=["API Documentation"])


@router.get(
    "/endpoints",
    response_model=ApiCatalogResponse,
    summary="List all discovered API endpoints with schemas and metadata",
)
def list_api_endpoints(
    request: Request,
    tag: Optional[str] = Query(None, description="Optional tag/category filter"),
    method: Optional[str] = Query(None, description="Optional HTTP method filter"),
    search: Optional[str] = Query(None, description="Optional path or summary search query"),
    current_user: User = Depends(get_current_user),
) -> ApiCatalogResponse:
    """
    Day 21 API Introspection Endpoint:
    - Analyzes live FastAPI route definitions, Pydantic schemas, and dependencies.
    - Extracts path parameters, query parameters, request schemas, and response models.
    - Pinpoints exact source file, function name, and line range via Python inspection.
    - Supports filtering by tag, HTTP method, or search query.
    """
    catalog = api_documentation_service.discover_all_endpoints(request.app)
    
    filtered_endpoints = catalog.endpoints

    if tag:
        clean_tag = tag.strip().lower()
        filtered_endpoints = [
            ep for ep in filtered_endpoints if ep.tag.lower() == clean_tag
        ]

    if method:
        clean_method = method.strip().upper()
        filtered_endpoints = [
            ep for ep in filtered_endpoints if ep.method == clean_method
        ]

    if search:
        clean_q = search.strip().lower()
        filtered_endpoints = [
            ep for ep in filtered_endpoints
            if clean_q in ep.path.lower()
            or clean_q in ep.summary.lower()
            or clean_q in ep.description.lower()
        ]

    return ApiCatalogResponse(
        title=catalog.title,
        version=catalog.version,
        description=catalog.description,
        total_endpoints=len(filtered_endpoints),
        tags=catalog.tags,
        endpoints=filtered_endpoints,
    )


@router.get(
    "/endpoint",
    response_model=EndpointDocItem,
    summary="Get detailed introspected metadata for a single endpoint",
)
def get_endpoint_detail(
    request: Request,
    path: str = Query(..., description="Exact endpoint path (e.g. /api/auth/register)"),
    method: str = Query(..., description="HTTP Method (GET, POST, etc.)"),
    current_user: User = Depends(get_current_user),
) -> EndpointDocItem:
    """
    Retrieves full introspected documentation metadata for an individual endpoint.
    """
    endpoint = api_documentation_service.get_endpoint_by_path_and_method(
        request.app, path=path, method=method
    )
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint {method.upper()} {path} not found in FastAPI application.",
        )
    return endpoint


@router.post(
    "/generate",
    response_model=GenerateApiDocResponse,
    summary="Generate AI-powered developer documentation for endpoint",
)
def generate_endpoint_documentation(
    request: Request,
    doc_req: GenerateApiDocRequest,
    current_user: User = Depends(get_current_user),
) -> GenerateApiDocResponse:
    """
    Day 21 AI Endpoint Documentation Generation:
    - Introspects endpoint source, parameters, Pydantic schemas, and dependencies.
    - Synthesizes professional developer-friendly documentation using local Gemma 2B.
    - Strictly grounded in real code: zero hallucination of fields, parameters, or types.
    - Includes cURL and JSON examples matching real Pydantic models.
    """
    try:
        return api_documentation_service.generate_endpoint_documentation(
            app=request.app,
            path=doc_req.path,
            method=doc_req.method,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/markdown",
    response_model=ApiMarkdownExportResponse,
    summary="Export complete API documentation reference in Markdown",
)
def export_api_markdown(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiMarkdownExportResponse:
    """
    Exports comprehensive Markdown documentation for all endpoints in the application.
    """
    return api_documentation_service.export_all_markdown(request.app)


@router.get(
    "/export/markdown",
    summary="Download API Specification Reference in Markdown Format",
)
def download_api_markdown(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Day 22 API Markdown File Download Endpoint:
    - Generates full API documentation reference in Markdown format.
    - Returns text/markdown file download with Content-Disposition header.
    """
    export_data = api_documentation_service.export_all_markdown(request.app)
    filename = "CodeSage_AI_API_Reference.md"
    return Response(
        content=export_data.markdown.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/export/pdf",
    summary="Download API Specification Reference in PDF Format",
)
def download_api_pdf(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Day 22 API PDF File Download Endpoint:
    - Generates clean, publication-grade API specification PDF catalog using ReportLab.
    - Returns application/pdf binary download with Content-Disposition header.
    """
    pdf_bytes = export_service.generate_api_docs_pdf(request.app)
    filename = "CodeSage_AI_API_Reference.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

