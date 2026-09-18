import inspect
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

from fastapi import FastAPI
from fastapi.routing import APIRoute, _IncludedRouter
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from app.schemas.api_documentation import (
    EndpointDocItem,
    EndpointFieldDoc,
    EndpointParameterDoc,
    ApiCatalogResponse,
    GenerateApiDocResponse,
    ApiMarkdownExportResponse,
)
from app.services.prompts import (
    API_DOC_SYSTEM_INSTRUCTIONS,
    API_DOC_RESPONSE_REQUIREMENTS,
    API_DOC_PROMPT_TEMPLATE,
)
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)


class ApiDocumentationService:
    """
    Introspective API Documentation Service for CodeSage AI.
    Analyzes actual FastAPI route definitions, Pydantic schemas, dependencies,
    and Python source code to build grounded, production-grade documentation.
    """

    def __init__(self):
        self._cached_catalog: Optional[ApiCatalogResponse] = None

    def _extract_annotation(self, param: Any) -> Any:
        """Safely extracts the type annotation from a FastAPI ModelField or parameter."""
        if hasattr(param, "field_info") and hasattr(param.field_info, "annotation"):
            return param.field_info.annotation
        if hasattr(param, "annotation"):
            return param.annotation
        if hasattr(param, "type_"):
            return param.type_
        return str

    def _get_type_name(self, annotation: Any) -> str:
        """Returns clean human-readable type name for a type annotation."""
        if annotation is None:
            return "None"
        if hasattr(annotation, "__name__"):
            return annotation.__name__
        
        type_str = str(annotation)
        # Clean typing constructs like typing.Optional[str], typing.List[int]
        type_str = type_str.replace("typing.", "").replace("NoneType", "None")
        return type_str

    def _inspect_dependencies(self, dependant: Any) -> Tuple[bool, str, List[str]]:
        """
        Recursively inspects route dependencies to identify authentication
        and service dependencies.
        """
        auth_required = False
        auth_type = "None (Public)"
        service_names = []

        seen_calls = set()

        def scan(dep):
            nonlocal auth_required, auth_type
            call = getattr(dep, "call", None)
            if not call or call in seen_calls:
                return
            seen_calls.add(call)

            name = getattr(call, "__name__", str(call))
            if "current_user" in name.lower() or "bearer" in name.lower() or "auth" in name.lower():
                auth_required = True
                auth_type = "Bearer JWT"
            elif "db" in name.lower():
                service_names.append("PostgreSQL Session (get_db)")
            elif "service" in name.lower():
                service_names.append(name)

            for sub_dep in getattr(dep, "dependencies", []):
                scan(sub_dep)

        for dep in getattr(dependant, "dependencies", []):
            scan(dep)

        return auth_required, auth_type, list(dict.fromkeys(service_names))

    def _inspect_source_location(self, endpoint: Any) -> Tuple[str, str, int, int, str, str]:
        """
        Introspects the exact source file path, function name, and line numbers
        for an endpoint handler using Python's inspect module.
        """
        try:
            source_file = inspect.getsourcefile(endpoint) or "app/main.py"
            # Normalize to relative repository path
            p = Path(source_file)
            parts = p.parts
            if "backend" in parts:
                idx = parts.index("backend")
                rel_path = "/".join(parts[idx:])
            elif "app" in parts:
                idx = parts.index("app")
                rel_path = "backend/" + "/".join(parts[idx:])
            else:
                rel_path = p.name

            lines, start_line = inspect.getsourcelines(endpoint)
            end_line = start_line + len(lines) - 1
            line_range = f"Lines {start_line}–{end_line}"
            source_code = "".join(lines)
            function_name = getattr(endpoint, "__name__", "endpoint")
            return rel_path, function_name, start_line, end_line, line_range, source_code
        except Exception as e:
            logger.debug(f"Source introspection fallback for {endpoint}: {e}")
            return "backend/app/main.py", getattr(endpoint, "__name__", "endpoint"), 1, 1, "Lines 1–1", ""

    def _extract_pydantic_fields(self, model: Type[BaseModel]) -> List[EndpointFieldDoc]:
        """Extracts field details from a Pydantic model (Pydantic v2 compatible)."""
        fields = []
        if not (isinstance(model, type) and issubclass(model, BaseModel)):
            return fields

        model_fields = getattr(model, "model_fields", {})
        for name, field in model_fields.items():
            type_name = self._get_type_name(field.annotation)
            req = field.is_required() if hasattr(field, "is_required") else (field.default is PydanticUndefined)
            default_val = None if field.default is PydanticUndefined else field.default
            desc = field.description or ""
            fields.append(
                EndpointFieldDoc(
                    name=name,
                    type=type_name,
                    required=req,
                    default=str(default_val) if default_val is not None else None,
                    description=desc,
                )
            )
        return fields

    def _generate_example_from_model(self, model: Type[BaseModel]) -> Optional[Dict[str, Any]]:
        """Synthesizes a realistic JSON example strictly adhering to model fields."""
        if not (isinstance(model, type) and issubclass(model, BaseModel)):
            return None

        example = {}
        model_fields = getattr(model, "model_fields", {})
        for name, field in model_fields.items():
            type_str = self._get_type_name(field.annotation).lower()
            default = field.default if field.default is not PydanticUndefined else None

            if default is not None:
                example[name] = default
            elif "int" in type_str:
                example[name] = 1 if "id" in name else 5
            elif "bool" in type_str:
                example[name] = True
            elif "float" in type_str:
                example[name] = 0.95
            elif "list" in type_str:
                example[name] = ["item_1", "item_2"]
            elif "dict" in type_str:
                example[name] = {"key": "value"}
            elif "email" in name:
                example[name] = "developer@codesage.ai"
            elif "password" in name:
                example[name] = "SecurePassword123!"
            elif "name" in name:
                example[name] = "CodeSage Project"
            elif "query" in name or "question" in name or "prompt" in name:
                example[name] = "How does authentication work in this codebase?"
            elif "path" in name:
                example[name] = "app/services/auth.py"
            else:
                example[name] = f"sample_{name}"
        return example

    def discover_all_endpoints(self, app: FastAPI, force_refresh: bool = False) -> ApiCatalogResponse:
        """
        Scans the live FastAPI application and introspects all APIRoutes and included sub-routers.
        """
        if self._cached_catalog and not force_refresh:
            return self._cached_catalog

        items: List[EndpointDocItem] = []
        tags_set = set()

        # Helper to gather all APIRoute instances
        route_tuples: List[Tuple[str, APIRoute]] = []

        for r in app.routes:
            if isinstance(r, APIRoute):
                # Skip internal OpenAPI / docs endpoints
                if r.path in ("/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"):
                    continue
                route_tuples.append(("", r))
            elif isinstance(r, _IncludedRouter):
                prefix = r.include_context.prefix or ""
                for sub_r in r.original_router.routes:
                    if isinstance(sub_r, APIRoute):
                        route_tuples.append((prefix, sub_r))

        # Process each route
        for prefix, route in route_tuples:
            full_path = prefix + route.path if not route.path.startswith(prefix) else route.path
            
            # Extract HTTP methods (ignoring HEAD, OPTIONS)
            methods = [m for m in sorted(route.methods) if m not in ("HEAD", "OPTIONS")]
            if not methods:
                continue

            primary_tag = route.tags[0] if route.tags else "General"
            tags_set.add(primary_tag)

            auth_required, auth_type, services = self._inspect_dependencies(route.dependant)

            # Introspect source code
            source_file, func_name, s_line, e_line, line_range, source_code = self._inspect_source_location(route.endpoint)

            # Detect additional service calls in source
            known_services = [
                "chat_service", "context_retriever", "faiss_service",
                "function_doc_service", "ollama_service", "project_service",
                "auth_service"
            ]
            for svc in known_services:
                if svc in source_code and svc not in services:
                    services.append(svc)

            # Path & Query parameters
            path_params: List[EndpointParameterDoc] = []
            for param in getattr(route.dependant, "path_params", []):
                ann = self._extract_annotation(param)
                path_params.append(
                    EndpointParameterDoc(
                        name=param.name,
                        in_type="path",
                        type=self._get_type_name(ann),
                        required=True,
                        default=None,
                        description=getattr(param, "description", None) or f"Target {param.name} identifier",
                    )
                )

            query_params: List[EndpointParameterDoc] = []
            for param in getattr(route.dependant, "query_params", []):
                ann = self._extract_annotation(param)
                req = param.is_required() if hasattr(param, "is_required") else (param.default is PydanticUndefined)
                default_val = None if param.default is PydanticUndefined else param.default
                query_params.append(
                    EndpointParameterDoc(
                        name=param.name,
                        in_type="query",
                        type=self._get_type_name(ann),
                        required=req,
                        default=str(default_val) if default_val is not None else None,
                        description=getattr(param, "description", None) or "",
                    )
                )

            # Request body
            request_body_type = None
            request_model_name = None
            request_fields: List[EndpointFieldDoc] = []
            example_req = None

            body_params = getattr(route.dependant, "body_params", [])
            if body_params:
                first_body = body_params[0]
                annotation = self._extract_annotation(first_body)
                if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                    request_body_type = "application/json"
                    request_model_name = annotation.__name__
                    request_fields = self._extract_pydantic_fields(annotation)
                    example_req = self._generate_example_from_model(annotation)
                elif "UploadFile" in str(annotation):
                    request_body_type = "multipart/form-data"
                    request_model_name = "Multipart (File)"
                    request_fields.append(
                        EndpointFieldDoc(
                            name="file",
                            type="UploadFile (ZIP)",
                            required=True,
                            default=None,
                            description="Source code ZIP archive (.zip)",
                        )
                    )
                    example_req = "multipart/form-data; file=@project.zip"

            # Response model
            response_model_name = None
            response_fields: List[EndpointFieldDoc] = []
            example_res = None
            resp_model = getattr(route, "response_model", None)
            if resp_model and isinstance(resp_model, type) and issubclass(resp_model, BaseModel):
                response_model_name = resp_model.__name__
                response_fields = self._extract_pydantic_fields(resp_model)
                example_res = self._generate_example_from_model(resp_model)
            elif resp_model and hasattr(resp_model, "__origin__") and issubclass(getattr(resp_model, "__origin__", object), list):
                # E.g. List[ProjectResponse]
                inner = getattr(resp_model, "__args__", [None])[0]
                if inner and isinstance(inner, type) and issubclass(inner, BaseModel):
                    response_model_name = f"List[{inner.__name__}]"
                    response_fields = self._extract_pydantic_fields(inner)
                    sample = self._generate_example_from_model(inner)
                    example_res = [sample] if sample else []

            # Documented error responses
            error_responses = []
            if auth_required:
                error_responses.append({
                    "status_code": 401,
                    "name": "Unauthorized",
                    "description": "Missing, invalid, or expired JWT bearer access token",
                })
            if "{project_id}" in full_path or "project_id" in [p.name for p in path_params]:
                error_responses.append({
                    "status_code": 404,
                    "name": "Not Found",
                    "description": "Target project does not exist or user lacks tenancy permissions",
                })
            if request_fields or query_params:
                error_responses.append({
                    "status_code": 422,
                    "name": "Unprocessable Entity",
                    "description": "Request payload fails Pydantic schema validation or type constraints",
                })

            summary = route.summary or func_name.replace("_", " ").capitalize()
            description = (inspect.getdoc(route.endpoint) or route.description or "").strip()

            for method in methods:
                endpoint_id = f"{method.lower()}_{re.sub(r'[^a-zA-Z0-9]+', '_', full_path).strip('_')}"
                items.append(
                    EndpointDocItem(
                        id=endpoint_id,
                        method=method,
                        path=full_path,
                        tag=primary_tag,
                        summary=summary,
                        description=description,
                        auth_required=auth_required,
                        auth_type=auth_type,
                        path_params=path_params,
                        query_params=query_params,
                        request_body_type=request_body_type,
                        request_model_name=request_model_name,
                        request_fields=request_fields,
                        response_status=route.status_code or 200,
                        response_model_name=response_model_name,
                        response_fields=response_fields,
                        error_responses=error_responses,
                        dependencies=services,
                        example_request=example_req,
                        example_response=example_res,
                        source_file=source_file,
                        source_function=func_name,
                        source_line_range=line_range,
                        source_start_line=s_line,
                        source_end_line=e_line,
                    )
                )

        catalog = ApiCatalogResponse(
            title=app.title,
            version=app.version,
            description=app.description,
            total_endpoints=len(items),
            tags=sorted(tags_set),
            endpoints=items,
        )
        self._cached_catalog = catalog
        return catalog

    def get_endpoint_by_path_and_method(
        self, app: FastAPI, path: str, method: str
    ) -> Optional[EndpointDocItem]:
        """Finds a specific endpoint from the catalog."""
        catalog = self.discover_all_endpoints(app)
        clean_method = method.upper().strip()
        clean_path = path.strip().rstrip("/") or "/"
        
        for ep in catalog.endpoints:
            ep_path = ep.path.rstrip("/") or "/"
            if ep.method == clean_method and ep_path == clean_path:
                return ep
        return None

    def generate_endpoint_documentation(
        self, app: FastAPI, path: str, method: str
    ) -> GenerateApiDocResponse:
        """
        Generates comprehensive AI-powered developer documentation for a specific endpoint.
        Uses LangChain ChatOllama with Gemma 2B, falling back to structured deterministic generator.
        """
        endpoint = self.get_endpoint_by_path_and_method(app, path, method)
        if not endpoint:
            raise ValueError(f"Endpoint {method} {path} not found in FastAPI application.")

        # Read actual endpoint source
        _, _, _, _, _, source_code = self._inspect_source_location(
            self._resolve_endpoint_callable(app, endpoint.path, endpoint.method)
        )

        # Assemble prompt fields
        params_info_lines = []
        if endpoint.path_params:
            params_info_lines.append("Path Parameters:")
            for p in endpoint.path_params:
                params_info_lines.append(f"- `{p.name}` ({p.type}, required): {p.description}")
        if endpoint.query_params:
            params_info_lines.append("Query Parameters:")
            for q in endpoint.query_params:
                req_str = "required" if q.required else f"optional, default={q.default}"
                params_info_lines.append(f"- `{q.name}` ({q.type}, {req_str}): {q.description}")
        params_info = "\n".join(params_info_lines) if params_info_lines else "None"

        req_info_lines = []
        if endpoint.request_body_type:
            req_info_lines.append(f"Content-Type: {endpoint.request_body_type}")
            if endpoint.request_model_name:
                req_info_lines.append(f"Model: {endpoint.request_model_name}")
            for f in endpoint.request_fields:
                req_str = "required" if f.required else f"optional, default={f.default}"
                req_info_lines.append(f"- `{f.name}` ({f.type}, {req_str}): {f.description}")
        req_info = "\n".join(req_info_lines) if req_info_lines else "None (No request body)"

        resp_info_lines = [f"Status Code: {endpoint.response_status}"]
        if endpoint.response_model_name:
            resp_info_lines.append(f"Model: {endpoint.response_model_name}")
        for f in endpoint.response_fields:
            resp_info_lines.append(f"- `{f.name}` ({f.type}): {f.description}")
        resp_info = "\n".join(resp_info_lines)

        deps_info = ", ".join(endpoint.dependencies) if endpoint.dependencies else "None"

        response_requirements = API_DOC_RESPONSE_REQUIREMENTS.format(
            method=endpoint.method,
            path=endpoint.path,
            summary=endpoint.summary,
            source_file=endpoint.source_file,
            source_function=endpoint.source_function,
            source_line_range=endpoint.source_line_range,
        )

        prompt = API_DOC_PROMPT_TEMPLATE.format(
            system_instructions=API_DOC_SYSTEM_INSTRUCTIONS,
            method=endpoint.method,
            path=endpoint.path,
            tag=endpoint.tag,
            summary=endpoint.summary,
            description=endpoint.description,
            auth_type=endpoint.auth_type,
            auth_required=endpoint.auth_required,
            source_file=endpoint.source_file,
            source_function=endpoint.source_function,
            source_line_range=endpoint.source_line_range,
            parameters_info=params_info,
            request_schema_info=req_info,
            response_schema_info=resp_info,
            dependencies_info=deps_info,
            source_code=source_code,
            response_requirements=response_requirements,
        )

        # Attempt AI generation via Ollama / Gemma
        markdown = None
        try:
            health = ollama_service.check_health()
            if health.ollama.available:
                raw_ai = ollama_service.generate(prompt=prompt, system_prompt=API_DOC_SYSTEM_INSTRUCTIONS)
                if raw_ai and len(raw_ai.strip()) > 80:
                    markdown = raw_ai.strip()
                    if not markdown.startswith("##"):
                        markdown = f"## {endpoint.method} {endpoint.path}\n\n" + markdown
        except Exception as e:
            logger.warning(f"Ollama generation fallback for API doc: {e}")

        # Fallback to high-quality deterministic documentation generator
        if not markdown:
            markdown = self._build_deterministic_markdown(endpoint, source_code)

        return GenerateApiDocResponse(
            endpoint=endpoint,
            markdown=markdown,
        )

    def _resolve_endpoint_callable(self, app: FastAPI, path: str, method: str) -> Any:
        """Finds the actual Python function for an endpoint."""
        for r in app.routes:
            if isinstance(r, APIRoute) and r.path == path and method in r.methods:
                return r.endpoint
            elif isinstance(r, _IncludedRouter):
                prefix = r.include_context.prefix or ""
                for sub in r.original_router.routes:
                    if isinstance(sub, APIRoute):
                        full = prefix + sub.path if not sub.path.startswith(prefix) else sub.path
                        if full == path and method in sub.methods:
                            return sub.endpoint
        return lambda: None

    def _build_deterministic_markdown(self, ep: EndpointDocItem, source_code: str = "") -> str:
        """Constructs complete, professional Markdown documentation directly from metadata."""
        md = []
        md.append(f"## {ep.method} {ep.path}\n")
        md.append(f"**Summary**\n{ep.summary}\n")
        
        md.append("**Purpose & Overview**")
        desc = ep.description or f"Handles {ep.method} requests for {ep.path} within CodeSage AI."
        md.append(f"{desc}\n")

        md.append("**Authentication**")
        if ep.auth_required:
            md.append(f"- **Required**: Yes (`{ep.auth_type}`)")
            md.append("- Pass a valid signed JWT in the HTTP header: `Authorization: Bearer <access_token>`\n")
        else:
            md.append("- **Required**: No (Public access, no credentials needed)\n")

        md.append("**Parameters**")
        if ep.path_params:
            md.append("Path Parameters:")
            for p in ep.path_params:
                md.append(f"- `{p.name}` (`{p.type}`, required) — {p.description or 'Path identifier'}")
        else:
            md.append("- Path Parameters: None")

        if ep.query_params:
            md.append("Query Parameters:")
            for q in ep.query_params:
                req_text = "required" if q.required else f"optional, default={q.default}"
                md.append(f"- `{q.name}` (`{q.type}`, {req_text}) — {q.description or 'Filter/option parameter'}")
        else:
            md.append("- Query Parameters: None")
        md.append("")

        md.append("**Request Body**")
        if ep.request_body_type:
            md.append(f"- **Content-Type**: `{ep.request_body_type}`")
            if ep.request_model_name:
                md.append(f"- **Model Schema**: `{ep.request_model_name}`")
            if ep.request_fields:
                md.append("- **Fields**:")
                for f in ep.request_fields:
                    req_text = "required" if f.required else f"optional, default={f.default}"
                    desc_text = f" — {f.description}" if f.description else ""
                    md.append(f"  - `{f.name}` (`{f.type}`, {req_text}){desc_text}")
        else:
            md.append("- None (No request body)\n")
        md.append("")

        md.append("**Responses**")
        md.append(f"- **Primary Status**: `{ep.response_status}`")
        if ep.response_model_name:
            md.append(f"- **Response Model**: `{ep.response_model_name}`")
        if ep.response_fields:
            md.append("- **Response Fields**:")
            for f in ep.response_fields:
                desc_text = f" — {f.description}" if f.description else ""
                md.append(f"  - `{f.name}` (`{f.type}`){desc_text}")
        
        if ep.error_responses:
            md.append("\n**Error Status Codes**:")
            for err in ep.error_responses:
                md.append(f"- `{err['status_code']} {err['name']}` — {err['description']}")
        md.append("")

        md.append("**Dependencies & Related Services**")
        if ep.dependencies:
            for dep in ep.dependencies:
                md.append(f"- `{dep}`")
        else:
            md.append("- Standard FastAPI request handling")
        md.append("")

        if ep.example_request is not None:
            md.append("**Example Request**")
            if isinstance(ep.example_request, dict):
                md.append("```json\n" + json.dumps(ep.example_request, indent=2) + "\n```\n")
            else:
                md.append(f"```bash\n{ep.example_request}\n```\n")

        if ep.example_response is not None:
            md.append("**Example Response**")
            if isinstance(ep.example_response, (dict, list)):
                md.append("```json\n" + json.dumps(ep.example_response, indent=2) + "\n```\n")
            else:
                md.append(f"```json\n{ep.example_response}\n```\n")

        md.append("**Source Reference**")
        md.append(f"- File: `{ep.source_file}`")
        md.append(f"- Handler: `{ep.source_function}()`")
        md.append(f"- Range: {ep.source_line_range}")

        return "\n".join(md)

    def export_all_markdown(self, app: FastAPI) -> ApiMarkdownExportResponse:
        """Compiles full repository API documentation into a single comprehensive Markdown file."""
        catalog = self.discover_all_endpoints(app)
        
        sections = []
        sections.append(f"# {catalog.title} — API Documentation Reference\n")
        sections.append(f"> {catalog.description}")
        sections.append(f"> **Version**: {catalog.version} | **Total Endpoints**: {catalog.total_endpoints}\n")
        sections.append("---\n")

        # Table of contents
        sections.append("## Table of Contents\n")
        # Group by tag
        by_tag: Dict[str, List[EndpointDocItem]] = {}
        for ep in catalog.endpoints:
            by_tag.setdefault(ep.tag, []).append(ep)

        for tag, endpoints in by_tag.items():
            sections.append(f"### {tag}")
            for ep in endpoints:
                anchor = f"{ep.method.lower()}-{ep.path.lower().replace('/', '').replace('{', '').replace('}', '').replace('_', '-')}"
                auth_badge = "🔒" if ep.auth_required else "🌐"
                sections.append(f"- [{ep.method} {ep.path}](#{anchor}) — {auth_badge} {ep.summary}")
            sections.append("")

        sections.append("---\n")

        # Endpoint details
        for tag, endpoints in by_tag.items():
            sections.append(f"# Category: {tag}\n")
            for ep in endpoints:
                sections.append(self._build_deterministic_markdown(ep))
                sections.append("\n---\n")

        full_md = "\n".join(sections)
        return ApiMarkdownExportResponse(
            title=catalog.title,
            version=catalog.version,
            total_endpoints=catalog.total_endpoints,
            markdown=full_md,
        )


api_documentation_service = ApiDocumentationService()
