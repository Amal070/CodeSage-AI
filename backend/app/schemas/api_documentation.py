from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EndpointParameterDoc(BaseModel):
    """Metadata for path or query parameters."""
    name: str = Field(..., description="Parameter name")
    in_type: str = Field(..., description="Location of parameter ('path' or 'query')")
    type: str = Field(..., description="Data type of parameter")
    required: bool = Field(..., description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value if optional")
    description: Optional[str] = Field(None, description="Parameter description or purpose")


class EndpointFieldDoc(BaseModel):
    """Metadata for request body or response schema fields."""
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Data type of field")
    required: bool = Field(..., description="Whether field is required")
    default: Optional[Any] = Field(None, description="Default value if present")
    description: Optional[str] = Field(None, description="Field description or purpose")


class EndpointDocItem(BaseModel):
    """Comprehensive documentation for a single API endpoint."""
    id: str = Field(..., description="Unique endpoint identifier")
    method: str = Field(..., description="HTTP Method (GET, POST, DELETE, etc.)")
    path: str = Field(..., description="Route URL path")
    tag: str = Field("General", description="Primary tag or group")
    summary: str = Field("", description="Short summary of endpoint purpose")
    description: str = Field("", description="Detailed description or docstring")
    auth_required: bool = Field(False, description="Whether authentication is required")
    auth_type: str = Field("None (Public)", description="Authentication mechanism")
    path_params: List[EndpointParameterDoc] = Field(default_factory=list, description="Path parameters")
    query_params: List[EndpointParameterDoc] = Field(default_factory=list, description="Query parameters")
    request_body_type: Optional[str] = Field(None, description="Content type (e.g. application/json)")
    request_model_name: Optional[str] = Field(None, description="Name of Pydantic request model")
    request_fields: List[EndpointFieldDoc] = Field(default_factory=list, description="Request body fields")
    response_status: int = Field(200, description="Primary HTTP response status code")
    response_model_name: Optional[str] = Field(None, description="Name of Pydantic response model")
    response_fields: List[EndpointFieldDoc] = Field(default_factory=list, description="Response fields")
    error_responses: List[Dict[str, Any]] = Field(default_factory=list, description="Documented error status codes")
    dependencies: List[str] = Field(default_factory=list, description="Service and injection dependencies")
    example_request: Optional[Any] = Field(None, description="Example JSON request body or payload")
    example_response: Optional[Any] = Field(None, description="Example JSON response body")
    source_file: str = Field(..., description="Relative file path where route is defined")
    source_function: str = Field(..., description="Python endpoint function name")
    source_line_range: str = Field(..., description="Line range format 'Lines X–Y'")
    source_start_line: int = Field(..., description="Starting line number in source file")
    source_end_line: int = Field(..., description="Ending line number in source file")


class ApiCatalogResponse(BaseModel):
    """Catalog of all discovered endpoints in the FastAPI application."""
    title: str = Field(..., description="API application title")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    total_endpoints: int = Field(..., description="Total number of endpoints discovered")
    tags: List[str] = Field(default_factory=list, description="List of unique tags/categories")
    endpoints: List[EndpointDocItem] = Field(default_factory=list, description="List of endpoint documentation items")


class GenerateApiDocRequest(BaseModel):
    """Request to generate deep AI-powered documentation for a specific endpoint."""
    path: str = Field(..., description="Exact endpoint path (e.g. /api/auth/register)")
    method: str = Field(..., description="HTTP method (GET, POST, etc.)")


class GenerateApiDocResponse(BaseModel):
    """AI-powered documentation response for a specific endpoint."""
    endpoint: EndpointDocItem
    markdown: str = Field(..., description="Full developer-friendly Markdown documentation")


class ApiMarkdownExportResponse(BaseModel):
    """Export of complete API documentation in Markdown format."""
    title: str
    version: str
    total_endpoints: int
    markdown: str
