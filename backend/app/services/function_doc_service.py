"""
CodeSage AI — Day 20 Function Documentation Service

Provides grounded, AI-powered documentation generation for individual functions and methods
extracted from uploaded projects using Tree-sitter AST parsing, CodeChunk metadata,
and LangChain ChatOllama.
"""

import logging
import os
import posixpath
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.schemas.function_doc import (
    FunctionDocRequest,
    FunctionDocItem,
    FunctionListResponse,
    FunctionDocResponse,
    ParameterDoc,
)
from app.services.code_parser import code_parser_service
from app.services.faiss_service import faiss_service
from app.services.project_analyzer import EXCLUDED_DIRECTORIES
from app.services.prompts import (
    FUNCTION_DOC_SYSTEM_INSTRUCTIONS,
    FUNCTION_DOC_RESPONSE_REQUIREMENTS,
    FUNCTION_DOC_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)


class FunctionDocService:
    """
    Service responsible for Day 20 AI Function Documentation:
    - Lists functions across an uploaded project or within a single file.
    - Resolves function code using Tree-sitter AST and indexed CodeChunk metadata.
    - Extracts bounded surrounding context (preamble, imports, enclosing class, semantic neighbors).
    - Generates grounded, professional Markdown documentation via LangChain + Gemma 2B.
    - Parses documentation into structured fields (purpose, parameters, returns, behavior, etc.).
    """

    def __init__(self) -> None:
        self.prompt_template = PromptTemplate.from_template(FUNCTION_DOC_PROMPT_TEMPLATE)
        self.output_parser = StrOutputParser()

    def get_llm(self) -> ChatOllama:
        """
        Initializes LangChain ChatOllama wrapper with low temperature for grounded generation.
        """
        timeout = getattr(settings, "OLLAMA_TIMEOUT", 30.0)
        base_url = (
            settings.OLLAMA_BASE_URL.replace("localhost", "127.0.0.1")
            if hasattr(settings, "OLLAMA_BASE_URL")
            else "http://127.0.0.1:11434"
        )
        return ChatOllama(
            base_url=base_url,
            model=settings.OLLAMA_MODEL,
            temperature=0.1,
            request_timeout=timeout,
        )

    def _get_project_extracted_dir(self, project: Project) -> Path:
        """
        Returns validated extracted directory path for project.
        """
        if project.extracted_path:
            extracted_dir = Path(project.extracted_path).resolve()
            if extracted_dir.exists() and extracted_dir.is_dir():
                return extracted_dir

        # Fallback to default extracted directory location
        storage_base = getattr(
            settings,
            "STORAGE_DIR",
            str(Path(__file__).resolve().parent.parent.parent / "storage")
        )
        extracted_dir = (Path(storage_base) / "projects" / str(project.id) / "extracted").resolve()
        if extracted_dir.exists() and extracted_dir.is_dir():
            return extracted_dir

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extracted project directory not found. Please re-upload or re-extract the project.",
        )

    def _safe_resolve_file_path(self, extracted_dir: Path, rel_path: str) -> Path:
        """
        Validates and safely resolves relative file path within project root, preventing traversal.
        """
        clean_rel = rel_path.strip().replace("\\", "/")
        if ".." in clean_rel.split("/") or ".." in clean_rel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Path traversal detected.",
            )

        clean_rel = clean_rel.lstrip("/")
        full_path = (extracted_dir / clean_rel).resolve()
        try:
            full_path.relative_to(extracted_dir.resolve())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access denied: file path is outside project root.",
            )

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source file '{clean_rel}' not found in project.",
            )

        return full_path

    def _read_file_safe(self, file_path: Path) -> str:
        """
        Safely reads file with multiple encoding fallbacks.
        """
        for enc in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as err:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error reading file: {str(err)}",
                )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File could not be decoded with supported encodings.",
        )

    # ==========================================================================
    # FUNCTION DISCOVERY & LISTING
    # ==========================================================================

    def list_project_functions(
        self,
        db: Session,
        project: Project,
        file_path: Optional[str] = None,
    ) -> FunctionListResponse:
        """
        Lists all functions and methods in the project.
        - If indexed chunks exist, reads from database for speed.
        - If unindexed or file_path is specified, parses source files on-the-fly with Tree-sitter.
        """
        extracted_dir = self._get_project_extracted_dir(project)
        functions: List[FunctionDocItem] = []

        if file_path:
            # Single file requested: parse directly with Tree-sitter
            target_file = self._safe_resolve_file_path(extracted_dir, file_path)
            content = self._read_file_safe(target_file)
            file_name = target_file.name
            ts_lang = code_parser_service.detect_language(file_name)
            if not ts_lang:
                return FunctionListResponse(project_id=project.id, total_functions=0, functions=[])

            rel_posix = target_file.relative_to(extracted_dir).as_posix()
            parsed = code_parser_service.parse_source_code(content, ts_lang, rel_posix)
            for fn in parsed.functions:
                functions.append(
                    FunctionDocItem(
                        function_name=fn.name,
                        type=fn.type,
                        file_path=rel_posix,
                        start_line=fn.line_start,
                        end_line=fn.line_end,
                        parent_class=fn.parent_class,
                        language=ts_lang,
                        chunk_id=None,
                    )
                )
            return FunctionListResponse(
                project_id=project.id,
                total_functions=len(functions),
                functions=functions,
            )

        # Check if project has indexed code chunks
        stmt = (
            select(CodeChunk)
            .where(
                CodeChunk.project_id == project.id,
                CodeChunk.symbol_type.in_(["function", "method"]),
            )
            .order_by(CodeChunk.file_path, CodeChunk.start_line)
        )
        chunks = db.execute(stmt).scalars().all()

        if chunks:
            for c in chunks:
                functions.append(
                    FunctionDocItem(
                        function_name=c.symbol_name or "unknown",
                        type=c.symbol_type or "function",
                        file_path=c.file_path,
                        start_line=c.start_line,
                        end_line=c.end_line,
                        parent_class=c.parent_symbol,
                        language=c.language,
                        chunk_id=c.chunk_id,
                    )
                )
            return FunctionListResponse(
                project_id=project.id,
                total_functions=len(functions),
                functions=functions,
            )

        # Fallback: scan supported source files on-the-fly with Tree-sitter
        supported_exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".java"}
        for root, dirs, files in os.walk(extracted_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRECTORIES and not d.startswith(".")]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in supported_exts:
                    full_p = Path(root) / f
                    try:
                        rel = full_p.relative_to(extracted_dir).as_posix()
                        ts_lang = code_parser_service.detect_language(f)
                        if not ts_lang:
                            continue
                        code_str = self._read_file_safe(full_p)
                        parsed = code_parser_service.parse_source_code(code_str, ts_lang, rel)
                        for fn in parsed.functions:
                            functions.append(
                                FunctionDocItem(
                                    function_name=fn.name,
                                    type=fn.type,
                                    file_path=rel,
                                    start_line=fn.line_start,
                                    end_line=fn.line_end,
                                    parent_class=fn.parent_class,
                                    language=ts_lang,
                                    chunk_id=None,
                                )
                            )
                    except Exception as err:
                        logger.warning("Error parsing file %s for functions: %s", full_p, err)
                        continue

        # Sort alphabetically by file and start line
        functions.sort(key=lambda x: (x.file_path, x.start_line))
        return FunctionListResponse(
            project_id=project.id,
            total_functions=len(functions),
            functions=functions,
        )

    # ==========================================================================
    # CONTEXT EXTRACTION (BOUNDED & ISOLATED)
    # ==========================================================================

    def _extract_function_source(
        self,
        content: str,
        start_line: int,
        end_line: int,
    ) -> str:
        """
        Extracts exact function source code by 1-based line bounds.
        """
        lines = content.splitlines(keepends=False)
        total_lines = len(lines)
        s = max(1, min(start_line, total_lines))
        e = max(s, min(end_line, total_lines))
        return "\n".join(lines[s - 1 : e])

    def _extract_file_preamble(self, content: str, max_lines: int = 40) -> str:
        """
        Extracts module preamble and top-level imports to inform dependencies.
        """
        lines = content.splitlines(keepends=False)
        import_lines = []
        for i, line in enumerate(lines[:max_lines]):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ", "const ", "require(", "package ", "using ")):
                import_lines.append(line)
        if not import_lines and lines:
            # Fallback to first 25 lines if no obvious import keywords
            return "\n".join(lines[:25])
        return "\n".join(import_lines)

    def _extract_parent_class_header(
        self,
        content: str,
        parent_class: Optional[str],
        language: str,
    ) -> str:
        """
        If the function is a method, extracts the enclosing class declaration and docstring.
        """
        if not parent_class:
            return "Standalone function (no parent class)."

        lines = content.splitlines(keepends=False)
        pattern = rf"class\s+{re.escape(parent_class)}\b"
        for i, line in enumerate(lines):
            if re.search(pattern, line):
                # Grab up to 10 lines of class header & docstring
                header_lines = lines[i : min(i + 12, len(lines))]
                return "\n".join(header_lines)

        return f"Enclosing Class: {parent_class}"

    def _extract_semantic_neighbors(
        self,
        project_id: int,
        function_name: str,
        parent_class: Optional[str],
    ) -> str:
        """
        Retrieves 1-2 bounded neighbor chunks from FAISS (if vector index exists)
        to identify callers, callee helpers, or related symbols.
        """
        index_path, mapping_path = faiss_service.get_index_file_paths(project_id)
        if not index_path.exists() or not mapping_path.exists():
            return "No vector index available for neighbor retrieval."

        try:
            query = f"{function_name} {parent_class or ''}"
            search_res = faiss_service.search(project_id=project_id, query=query, top_k=2)
            if not search_res.results:
                return "No related chunks retrieved."

            snippets = []
            for r in search_res.results:
                # Exclude the function itself if exact duplicate
                if r.symbol_name == function_name and not parent_class:
                    continue
                snippet_lines = r.content.splitlines(keepends=False)[:10]
                snippets.append(
                    f"Related Symbol: `{r.symbol_name}` ({r.symbol_type or 'code'}) in `{r.file_path}`:\n"
                    + "\n".join(snippet_lines)
                )

            return "\n\n".join(snippets) if snippets else "No external callers detected."
        except Exception as err:
            logger.warning("Error querying semantic neighbors for function doc: %s", err)
            return "Neighbor retrieval skipped."

    # ==========================================================================
    # STRUCTURED OUTPUT PARSER
    # ==========================================================================

    def _parse_documentation_sections(
        self,
        doc_text: str,
        default_function_name: str,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> Dict[str, Any]:
        """
        Parses the generated Markdown documentation into structured fields for frontend consumption.
        """
        data: Dict[str, Any] = {
            "purpose": None,
            "parameters": [],
            "returns": None,
            "behavior": [],
            "logic": [],
            "dependencies": [],
            "exceptions": [],
            "usage_example": None,
            "related_symbols": [],
        }

        # Extract Purpose
        purpose_match = re.search(r"\*\*Purpose\*\*\s*\n+([^\n*#]+)", doc_text, re.IGNORECASE)
        if purpose_match:
            data["purpose"] = purpose_match.group(1).strip()

        # Extract Parameters
        params_match = re.search(r"\*\*Parameters\*\*\s*\n+(.*?)(?=\n+\*\*[A-Za-z ]+\*\*|\Z)", doc_text, re.DOTALL | re.IGNORECASE)
        if params_match:
            param_block = params_match.group(1).strip()
            if "none" not in param_block.lower() or len(param_block) > 10:
                for line in param_block.splitlines():
                    p_match = re.match(r"^-\s*`?([A-Za-z0-9_]+)`?\s*(?:\(([^)]+)\))?\s*[—\-–:]\s*(.*)$", line.strip())
                    if p_match:
                        p_name = p_match.group(1).strip()
                        if p_name.lower() != "none":
                            p_type = p_match.group(2).strip() if p_match.group(2) else None
                            p_desc = p_match.group(3).strip() if p_match.group(3) else None
                            data["parameters"].append(
                                ParameterDoc(name=p_name, type=p_type, description=p_desc)
                            )

        # Extract Returns
        returns_match = re.search(r"\*\*Returns\*\*\s*\n+([^\n*#]+)", doc_text, re.IGNORECASE)
        if returns_match:
            data["returns"] = returns_match.group(1).strip()

        # Extract Behavior
        behavior_match = re.search(r"\*\*Behavior\*\*\s*\n+(.*?)(?=\n+\*\*[A-Za-z ]+\*\*|\Z)", doc_text, re.DOTALL | re.IGNORECASE)
        if behavior_match:
            b_block = behavior_match.group(1).strip()
            for line in b_block.splitlines():
                clean_line = re.sub(r"^\d+\.\s*", "", line.strip())
                if clean_line:
                    data["behavior"].append(clean_line)

        # Extract Important Logic
        logic_match = re.search(r"\*\*Important Logic\*\*\s*\n+(.*?)(?=\n+\*\*[A-Za-z ]+\*\*|\Z)", doc_text, re.DOTALL | re.IGNORECASE)
        if logic_match:
            l_block = logic_match.group(1).strip()
            for line in l_block.splitlines():
                clean_line = re.sub(r"^-\s*", "", line.strip())
                if clean_line:
                    data["logic"].append(clean_line)

        # Extract Dependencies
        dep_match = re.search(r"\*\*Dependencies\*\*\s*\n+(.*?)(?=\n+\*\*[A-Za-z ]+\*\*|\Z)", doc_text, re.DOTALL | re.IGNORECASE)
        if dep_match:
            d_block = dep_match.group(1).strip()
            for line in d_block.splitlines():
                clean_line = re.sub(r"^-\s*", "", line.strip())
                if clean_line and "none" not in clean_line.lower():
                    data["dependencies"].append(clean_line)

        # Extract Exceptions
        exc_match = re.search(r"\*\*Exceptions\s*/\s*Errors\*\*\s*\n+(.*?)(?=\n+\*\*[A-Za-z ]+\*\*|\Z)", doc_text, re.DOTALL | re.IGNORECASE)
        if exc_match:
            e_block = exc_match.group(1).strip()
            for line in e_block.splitlines():
                clean_line = re.sub(r"^-\s*", "", line.strip())
                if clean_line and "none" not in clean_line.lower():
                    data["exceptions"].append(clean_line)

        # Extract Usage Example
        example_match = re.search(r"\*\*Usage Example\*\*\s*\n+(```[a-z]*\n.*?\n```)", doc_text, re.DOTALL | re.IGNORECASE)
        if example_match:
            data["usage_example"] = example_match.group(1).strip()

        # Extract Related Symbols
        related_match = re.search(r"\*\*Related Symbols\*\*\s*\n+(.*?)(?=\n+\*\*Source\*\*|\Z)", doc_text, re.DOTALL | re.IGNORECASE)
        if related_match:
            r_block = related_match.group(1).strip()
            for line in r_block.splitlines():
                clean_line = re.sub(r"^-\s*", "", line.strip())
                if clean_line and "none" not in clean_line.lower():
                    data["related_symbols"].append(clean_line)

        return data

    # ==========================================================================
    # MAIN DOCUMENTATION GENERATION PIPELINE
    # ==========================================================================

    def _invoke_chain(self, prompt_inputs: Dict[str, Any]) -> str:
        """
        Invokes LangChain LCEL chain with ChatOllama and Gemma 2B.
        """
        llm = self.get_llm()
        chain = self.prompt_template | llm | self.output_parser
        return chain.invoke(prompt_inputs)

    def generate_function_doc(
        self,
        db: Session,
        project: Project,
        request: FunctionDocRequest,
    ) -> FunctionDocResponse:
        """
        Generates AI-powered documentation for a selected function from the project.
        """
        extracted_dir = self._get_project_extracted_dir(project)
        resolved_file = self._safe_resolve_file_path(extracted_dir, request.file_path)
        file_content = self._read_file_safe(resolved_file)
        rel_path = resolved_file.relative_to(extracted_dir).as_posix()
        file_name = resolved_file.name

        ts_lang = code_parser_service.detect_language(file_name) or "python"

        # Locate function in file using line ranges or Tree-sitter AST
        start_line = request.start_line
        end_line = request.end_line
        parent_class = request.parent_class
        function_name = request.function_name.strip()

        # If lines not specified, use Tree-sitter to pinpoint exact bounds
        if not start_line or not end_line:
            parsed = code_parser_service.parse_source_code(file_content, ts_lang, rel_path)
            matched_fn = None
            for fn in parsed.functions:
                if fn.name == function_name:
                    if parent_class and fn.parent_class != parent_class:
                        continue
                    matched_fn = fn
                    break

            if not matched_fn:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Function '{function_name}' was not found in '{rel_path}'.",
                )

            start_line = matched_fn.line_start
            end_line = matched_fn.line_end
            if not parent_class:
                parent_class = matched_fn.parent_class

        # Extract function source code
        function_source = self._extract_function_source(file_content, start_line, end_line)
        if not function_source.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not extract function source code for '{function_name}' between lines {start_line} and {end_line}.",
            )

        # Extract bounded surrounding context
        preamble = self._extract_file_preamble(file_content)
        parent_info = self._extract_parent_class_header(file_content, parent_class, ts_lang)
        neighbors = self._extract_semantic_neighbors(project.id, function_name, parent_class)

        surrounding_context = (
            f"=== MODULE IMPORTS / PREAMBLE ===\n{preamble}\n\n"
            f"=== ENCLOSING CLASS ===\n{parent_info}\n\n"
            f"=== RELATED PROJECT SYMBOLS ===\n{neighbors}"
        )

        response_requirements = FUNCTION_DOC_RESPONSE_REQUIREMENTS.format(
            function_name=function_name,
            file_path=rel_path,
            start_line=start_line,
            end_line=end_line,
        )

        # Format LangChain prompt
        prompt_inputs = {
            "system_instructions": FUNCTION_DOC_SYSTEM_INSTRUCTIONS,
            "function_name": function_name,
            "parent_class": parent_class or "None (standalone)",
            "file_path": rel_path,
            "language": ts_lang,
            "start_line": start_line,
            "end_line": end_line,
            "surrounding_context": surrounding_context,
            "function_source": function_source,
            "response_requirements": response_requirements,
        }

        # Invoke Gemma LLM via LangChain LCEL
        try:
            raw_doc = self._invoke_chain(prompt_inputs)
        except HTTPException:
            raise
        except Exception as err:
            logger.error("LangChain LLM invocation failed for function documentation: %s", err)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ollama LLM service is currently unreachable or timed out. Please ensure Ollama is running.",
            )

        # Ensure function header is present
        doc_markdown = raw_doc.strip()
        header_prefix = f"### {function_name}"
        if not doc_markdown.startswith("### "):
            doc_markdown = f"{header_prefix}\n\n{doc_markdown}"

        # Ensure source footer is present in the markdown
        source_footer = f"**Source**\n`{rel_path}`\nLines {start_line}–{end_line}"
        if "**Source**" not in doc_markdown:
            doc_markdown = f"{doc_markdown}\n\n{source_footer}"

        # Parse structured sections for rich UI representation
        parsed_fields = self._parse_documentation_sections(
            doc_text=doc_markdown,
            default_function_name=function_name,
            file_path=rel_path,
            start_line=start_line,
            end_line=end_line,
        )

        return FunctionDocResponse(
            project_id=project.id,
            function_name=function_name,
            file_path=rel_path,
            language=ts_lang,
            start_line=start_line,
            end_line=end_line,
            parent_class=parent_class,
            documentation=doc_markdown,
            purpose=parsed_fields.get("purpose"),
            parameters=parsed_fields.get("parameters", []),
            returns=parsed_fields.get("returns"),
            behavior=parsed_fields.get("behavior", []),
            logic=parsed_fields.get("logic", []),
            dependencies=parsed_fields.get("dependencies", []),
            exceptions=parsed_fields.get("exceptions", []),
            usage_example=parsed_fields.get("usage_example"),
            related_symbols=parsed_fields.get("related_symbols", []),
            source_code=function_source,
        )


function_doc_service = FunctionDocService()
