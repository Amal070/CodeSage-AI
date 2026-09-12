import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.models.project import Project
from app.models.uploaded_file import UploadedFile
from app.models.code_chunk import CodeChunk
from app.services.code_parser import code_parser_service
from app.schemas.code_parser import CodeParseResponse
from app.services.project_analyzer import project_analyzer_service
from app.schemas.project_analysis import ProjectAnalysisResponse
from app.services.dependency_analyzer import dependency_analyzer_service
from app.schemas.dependency_analysis import DependencyAnalysisResponse
from app.services.code_indexer import code_indexer_service
from app.schemas.code_index import (
    ChunkMetadata,
    CodeChunkResponse,
    ProjectIndexResponse,
    ProjectIndexStatusResponse,
)
from app.services.embedding_service import embedding_service
from app.schemas.embedding import (
    ProjectEmbeddingResponse,
    ProjectEmbeddingStatusResponse,
)
from app.services.faiss_service import faiss_service
from app.schemas.semantic_search import (
    VectorIndexBuildResponse,
    VectorIndexStatusResponse,
    SearchResponse,
)
from app.services.rag_service import rag_service
from app.schemas.rag import RagResponse


def get_user_projects(db: Session, user_id: int) -> List[Project]:
    """
    Retrieve all projects belonging to the given user, sorted by most recent.
    """
    stmt = select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
    return list(db.scalars(stmt).all())


def get_project_by_id(db: Session, project_id: int, user_id: int) -> Optional[Project]:
    """
    Retrieve a project by its primary key, ensuring it belongs to the authenticated user.
    """
    stmt = select(Project).where(Project.id == project_id, Project.user_id == user_id)
    return db.scalars(stmt).first()


async def process_project_upload(
    db: Session,
    file: UploadFile,
    user_id: int,
) -> Project:
    """
    Validates, stores, safely extracts, and registers an uploaded project archive.
    Enforces:
    - ZIP extension and format validation
    - Maximum upload size (MAX_UPLOAD_SIZE_MB)
    - Zip Slip / path traversal defense
    - File system isolation under storage/projects/<uuid>/
    - Database transaction integrity with automated cleanup on failure
    """
    # 1. Filename and extension validation
    filename = file.filename or ""
    if not filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file selected or filename is empty.",
        )

    ext = Path(filename).suffix.lower()
    if ext != ".zip":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ZIP files are allowed (.zip).",
        )

    # 2. Derive project name from ZIP filename (without .zip)
    raw_name = Path(filename).stem.strip()
    project_name = raw_name[:100] if raw_name else "Untitled Project"

    # 3. Setup isolated storage location
    storage_root = Path(settings.STORAGE_DIR) / "projects"
    project_uuid = uuid.uuid4().hex
    project_dir = storage_root / project_uuid
    extracted_dir = project_dir / "extracted"

    try:
        project_dir.mkdir(parents=True, exist_ok=True)
        extracted_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize storage directory on server.",
        )

    zip_dest = project_dir / "original.zip"
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_bytes = 0

    try:
        # 4. Stream file to disk while enforcing max file size limit
        with open(zip_dest, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                    )
                buffer.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes).",
            )

        # 5. Validate ZIP file integrity
        if not zipfile.is_zipfile(zip_dest):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid ZIP archive.",
            )

        try:
            with zipfile.ZipFile(zip_dest, "r") as zf:
                # Test for corruption
                bad_file = zf.testzip()
                if bad_file:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Corrupted entry detected in ZIP archive: {bad_file}",
                    )

                infolist = zf.infolist()
                if not infolist:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="The uploaded ZIP archive contains no files.",
                    )

                # 6. Safe extraction with Zip Slip defense
                resolved_extracted_dir = extracted_dir.resolve()
                file_count = 0
                lines_of_code = 0
                extracted_file_records = []

                for member in infolist:
                    # Resolve destination path
                    member_path = (extracted_dir / member.filename).resolve()

                    # Zip Slip Security check: ensure path remains within extracted_dir
                    try:
                        member_path.relative_to(resolved_extracted_dir)
                    except ValueError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Security violation: ZIP file contains forbidden path traversal entry.",
                        )

                    # Extract entry
                    zf.extract(member, path=extracted_dir)

                    if not member.is_dir():
                        file_count += 1
                        file_size = member.file_size
                        file_ext = Path(member.filename).suffix.lower()

                        # Basic line count estimate for text code files (< 2MB)
                        loc = 0
                        if file_size < 2 * 1024 * 1024 and file_ext in {
                            ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
                            ".json", ".md", ".sql", ".yaml", ".yml", ".txt", ".c", ".cpp", ".h"
                        }:
                            try:
                                with open(member_path, "r", encoding="utf-8", errors="ignore") as f:
                                    loc = sum(1 for _ in f)
                                    lines_of_code += loc
                            except Exception:
                                pass

                        extracted_file_records.append(
                            UploadedFile(
                                name=Path(member.filename).name,
                                path=str(member.filename),
                                file_type=file_ext if file_ext else "unknown",
                                size=file_size,
                                content=None,
                            )
                        )

        except HTTPException:
            raise
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded archive is corrupted or not a valid ZIP file.",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to read and unpack ZIP archive.",
            )

        # 7. Persist metadata in PostgreSQL
        project = Project(
            name=project_name,
            original_filename=filename,
            storage_path=str(project_dir),
            extracted_path=str(extracted_dir),
            status="uploaded",
            file_count=file_count,
            lines_of_code=lines_of_code,
            user_id=user_id,
        )

        db.add(project)
        db.flush()  # obtain project.id

        # Associate extracted files with project
        for f_record in extracted_file_records:
            f_record.project_id = project.id
            db.add(f_record)

        db.commit()
        db.refresh(project)
        return project

    except Exception:
        # Cleanup files on any failure to prevent orphaned data
        db.rollback()
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
        raise


# ============================================================
# DAY 6 — FILE EXPLORER & CODE VIEWER SERVICES
# ============================================================

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff", ".svgz",
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".dmg", ".msi",
    ".class", ".pyc", ".pyd", ".o", ".a", ".lib",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".woff", ".woff2", ".ttf", ".eot", ".otf"
}

EXTENSION_LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".json": "json",
    ".md": "markdown",
    ".markdown": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".bat": "batch",
    ".cmd": "batch",
    ".ps1": "powershell",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".r": "r",
    ".lua": "lua",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "plaintext",
    ".txt": "plaintext",
    ".env": "plaintext",
    ".gitignore": "plaintext",
    ".dockerignore": "plaintext",
    ".editorconfig": "plaintext",
}


def detect_language(filename: str) -> str:
    """
    Detect programming language from file extension or return plaintext.
    """
    suffix = Path(filename).suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(suffix, "plaintext")


def is_binary_file(file_path: Path) -> bool:
    """
    Check if a file is binary via extension or inspection of initial null bytes.
    """
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
    except Exception:
        return True
    return False


def build_file_tree(base_dir: Path, current_dir: Path) -> list[dict]:
    """
    Recursively walk current_dir and build a nested tree structure.
    Folders are sorted first, followed by files alphabetically.
    Paths returned are strictly relative to base_dir (POSIX style).
    """
    nodes = []
    try:
        entries = sorted(list(current_dir.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
    except Exception:
        return []

    for entry in entries:
        # Ignore VCS and OS artifacts
        if entry.name in {".git", "__MACOSX", ".DS_Store", "Thumbs.db"}:
            continue

        rel_path = str(entry.relative_to(base_dir)).replace("\\", "/")

        if entry.is_dir():
            child_nodes = build_file_tree(base_dir, entry)
            nodes.append({
                "name": entry.name,
                "type": "folder",
                "path": rel_path,
                "size": None,
                "children": child_nodes
            })
        elif entry.is_file():
            try:
                f_size = entry.stat().st_size
            except Exception:
                f_size = 0
            nodes.append({
                "name": entry.name,
                "type": "file",
                "path": rel_path,
                "size": f_size,
                "children": None
            })

    return nodes


def get_project_file_tree(db: Session, project_id: int, user_id: int) -> dict:
    """
    Retrieve recursive folder and file tree for an authenticated user's project.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it."
        )

    if not project.extracted_path:
        return {"project_id": project.id, "tree": []}

    extracted_dir = Path(project.extracted_path)
    if not extracted_dir.exists() or not extracted_dir.is_dir():
        return {"project_id": project.id, "tree": []}

    tree = build_file_tree(extracted_dir, extracted_dir)
    return {"project_id": project.id, "tree": tree}


def get_project_file_content(db: Session, project_id: int, user_id: int, relative_path: str) -> dict:
    """
    Safely retrieve file content from an extracted project.
    Guarantees:
    - User ownership verification
    - Path traversal prevention
    - File size limits (MAX_VIEWABLE_FILE_SIZE_MB)
    - Binary file detection
    - Safe UTF-8 decoding with fallback
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it."
        )

    clean_path = (relative_path or "").strip()
    if not clean_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File path cannot be empty."
        )

    # Security: Disallow absolute Windows/Unix paths or colon drive specs
    if clean_path.startswith("/") or clean_path.startswith("\\") or ":" in clean_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Absolute file paths are not allowed."
        )

    path_obj = Path(clean_path)
    if ".." in path_obj.parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Path traversal detected."
        )

    if not project.extracted_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project files are not available on server."
        )

    extracted_dir = Path(project.extracted_path).resolve()
    target_path = (extracted_dir / path_obj).resolve()

    # Verify target remains strictly inside extracted_dir
    try:
        target_path.relative_to(extracted_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Path escapes project directory."
        )

    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {clean_path}"
        )

    if not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested path is a directory, not a file."
        )

    file_size = target_path.stat().st_size
    max_size = settings.MAX_VIEWABLE_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        status_code = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)
        raise HTTPException(
            status_code=status_code,
            detail=f"This file is too large to preview ({round(file_size / (1024 * 1024), 2)}MB exceeds {settings.MAX_VIEWABLE_FILE_SIZE_MB}MB limit)."
        )

    # Binary file detection
    if is_binary_file(target_path):
        return {
            "name": target_path.name,
            "path": clean_path.replace("\\", "/"),
            "language": "binary",
            "size": file_size,
            "is_binary": True,
            "content": None,
            "message": "Binary files cannot be displayed."
        }

    # Safe text decoding
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(target_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(target_path, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception:
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file content."
        )

    language = detect_language(target_path.name)

    return {
        "name": target_path.name,
        "path": clean_path.replace("\\", "/"),
        "language": language,
        "size": file_size,
        "is_binary": False,
        "content": content,
        "message": None
    }


def parse_project_source_file(
    db: Session,
    project_id: int,
    user_id: int,
    relative_path: str,
) -> CodeParseResponse:
    """
    Safely parses a supported source file within an extracted project using Tree-sitter.
    Guarantees:
    - User ownership verification
    - Path traversal prevention (.., absolute paths, drive letters, boundary checks)
    - File existence and file type checks
    - File size limits (MAX_VIEWABLE_FILE_SIZE_MB)
    - Language support verification (.py, .java, .js only)
    - Safe UTF-8 decoding with fallback
    - Graceful syntax error handling
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    clean_path = (relative_path or "").strip()
    if not clean_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File path cannot be empty.",
        )

    # Security: Disallow absolute Windows/Unix paths or colon drive specs
    if clean_path.startswith("/") or clean_path.startswith("\\") or ":" in clean_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Absolute file paths are not allowed.",
        )

    path_obj = Path(clean_path)
    if ".." in path_obj.parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Path traversal detected.",
        )

    if not project.extracted_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project files are not available on server.",
        )

    extracted_dir = Path(project.extracted_path).resolve()
    target_path = (extracted_dir / path_obj).resolve()

    # Verify target remains strictly inside extracted_dir
    try:
        target_path.relative_to(extracted_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security violation: Path escapes project directory.",
        )

    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {clean_path}",
        )

    if not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested path is a directory, not a file.",
        )

    # Check supported language for Tree-sitter
    language = code_parser_service.detect_language(target_path.name)
    if not language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tree-sitter parsing is not supported for this file type.",
        )

    file_size = target_path.stat().st_size
    max_size = settings.MAX_VIEWABLE_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        status_code = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)
        raise HTTPException(
            status_code=status_code,
            detail=f"This file is too large to preview ({round(file_size / (1024 * 1024), 2)}MB exceeds {settings.MAX_VIEWABLE_FILE_SIZE_MB}MB limit).",
        )

    # Safe text decoding
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(target_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(target_path, "r", encoding="latin-1") as f:
                    content = f.read()
            except Exception:
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file content for parsing.",
        )

    posix_path = clean_path.replace("\\", "/")
    return code_parser_service.parse_source_code(content, language, relative_path=posix_path)


def analyze_project(
    db: Session,
    project_id: int,
    user_id: int,
) -> ProjectAnalysisResponse:
    """
    Safely performs Day 8 project analysis (statistics, languages, extension counts,
    and folder hierarchy) on the extracted project directory.
    - Requires authenticated user to be the owner of the project.
    - Operates purely on filesystem metadata without loading large files into memory.
    - Never returns raw source code contents or absolute server paths.
    - Handles missing or empty extracted paths gracefully.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    if not project.extracted_path:
        return project_analyzer_service._build_empty_response(project.id, project.name)

    extracted_dir = Path(project.extracted_path).resolve()
    if not extracted_dir.exists() or not extracted_dir.is_dir():
        return project_analyzer_service._build_empty_response(project.id, project.name)

    return project_analyzer_service.analyze_directory(extracted_dir, project.id, project.name)


def analyze_project_dependencies(
    db: Session,
    project_id: int,
    user_id: int,
) -> DependencyAnalysisResponse:
    """
    Safely performs Day 9 dependency analysis (imports, manifests, local vs. external resolution,
    and graph relationships) on the extracted project directory.
    - Requires authenticated user to be the owner of the project.
    - Statically parses source files using Tree-sitter and manifests.
    - Never runs project code or executes external package managers.
    - Never leaks server absolute filesystem paths.
    - Handles missing or empty extracted paths gracefully.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    if not project.extracted_path:
        return dependency_analyzer_service._build_empty_response(project.id, project.name)

    extracted_dir = Path(project.extracted_path).resolve()
    if not extracted_dir.exists() or not extracted_dir.is_dir():
        return dependency_analyzer_service._build_empty_response(project.id, project.name)

    return dependency_analyzer_service.analyze_dependencies(extracted_dir, project.id, project.name)


def index_project_code(
    db: Session,
    project_id: int,
    user_id: int,
) -> ProjectIndexResponse:
    """
    Safely runs the Day 10 Code Indexing pipeline on an extracted project.
    - Strictly enforces JWT authentication and tenancy ownership.
    - Resolves project.extracted_path.
    - Generates structural AST and line-based code chunks with rich metadata.
    - Persists CodeChunk records in PostgreSQL with idempotent re-indexing.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    if not project.extracted_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extracted project directory is missing.",
        )

    extracted_dir = Path(project.extracted_path).resolve()
    if not extracted_dir.exists() or not extracted_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extracted project directory does not exist on disk.",
        )

    return code_indexer_service.index_project(db, project, extracted_dir)


def get_project_index_status(
    db: Session,
    project_id: int,
    user_id: int,
) -> ProjectIndexStatusResponse:
    """
    Retrieves the current indexing status and statistics for a project.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    chunks_stmt = select(CodeChunk).where(CodeChunk.project_id == project_id)
    chunks = list(db.scalars(chunks_stmt).all())

    total_chunks = len(chunks)
    indexed_files = len({c.file_path for c in chunks})
    languages_dict: Dict[str, int] = {}
    for c in chunks:
        languages_dict[c.language] = languages_dict.get(c.language, 0) + 1

    last_indexed = None
    if chunks:
        last_indexed = max(c.created_at for c in chunks)

    return ProjectIndexStatusResponse(
        project_id=project.id,
        status=project.status,
        total_chunks=total_chunks,
        indexed_files=indexed_files,
        languages=languages_dict,
        last_indexed_at=last_indexed,
    )


def get_project_chunks(
    db: Session,
    project_id: int,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[CodeChunkResponse]:
    """
    Retrieves stored code chunks for Day 11 embedding consumption.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    stmt = (
        select(CodeChunk)
        .where(CodeChunk.project_id == project_id)
        .order_by(CodeChunk.file_path, CodeChunk.chunk_index)
        .limit(limit)
        .offset(offset)
    )
    chunks = list(db.scalars(stmt).all())

    return [
        CodeChunkResponse(
            chunk_id=c.chunk_id,
            content=c.content,
            metadata=ChunkMetadata(
                project_id=c.project_id,
                project_name=project.name,
                file_path=c.file_path,
                file_name=c.file_name,
                file_extension=c.file_extension,
                language=c.language,
                chunk_id=c.chunk_id,
                chunk_index=c.chunk_index,
                start_line=c.start_line,
                end_line=c.end_line,
                symbol_name=c.symbol_name,
                symbol_type=c.symbol_type,
                parent_symbol=c.parent_symbol,
                content_hash=c.content_hash,
                source_type=c.source_type,
            ),
        )
        for c in chunks
    ]


def generate_project_embeddings(
    db: Session,
    project_id: int,
    user_id: int,
) -> ProjectEmbeddingResponse:
    """
    Safely generates Nomic Embed Text vector embeddings for project code chunks:
    - Enforces authentication & user tenancy.
    - Verifies code chunks have been indexed (Day 10 requirement).
    - Skips already-embedded unchanged chunks via content hash comparison.
    - Persists vectors to PostgreSQL and returns statistics.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    # Check if project has been indexed (Phase 20 & 21)
    chunks_count = db.scalar(
        select(CodeChunk.id).where(CodeChunk.project_id == project_id).limit(1)
    )

    if chunks_count is None:
        # If project has never been indexed or has no chunks
        if project.status not in ("indexed", "embeddings_generated"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no indexed code chunks. Run code indexing first.",
            )
        # If project was indexed but contains 0 chunks (empty project - Phase 21)
        return ProjectEmbeddingResponse(
            project_id=project.id,
            project_name=project.name,
            status="completed",
            total_chunks=0,
            embedded_chunks=0,
            skipped_chunks=0,
            failed_chunks=0,
            embedding_dimension=embedding_service.embedding_dimension,
            model=embedding_service.model_name,
            failed_details=[],
        )

    return embedding_service.embed_project_chunks(db, project)


def get_project_embedding_status(
    db: Session,
    project_id: int,
    user_id: int,
) -> ProjectEmbeddingStatusResponse:
    """
    Retrieves the embedding generation status and statistics for a project.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    return embedding_service.get_project_embedding_status(db, project)


def build_project_vector_index(
    db: Session,
    project_id: int,
    user_id: int,
) -> VectorIndexBuildResponse:
    """
    Builds or rebuilds the FAISS vector index for an authenticated user's project (Phase 11):
    - Strictly verifies user tenancy.
    - Requires project to have generated embeddings from Day 11.
    - Persists FAISS IndexFlatIP index and mapping file.
    - Returns index statistics.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    # Check total chunks vs embedded chunks (Phases 12 & 13)
    total_chunks = db.scalar(
        select(CodeChunk.id).where(CodeChunk.project_id == project_id).limit(1)
    )

    if total_chunks is None:
        if project.status not in ("indexed", "embeddings_generated"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no indexed code chunks. Run code indexing first.",
            )
        # Empty project handling (Phase 13)
        return faiss_service.build_project_index(db, project)

    # Check if embeddings have been generated for chunks
    embedded_chunk = db.scalar(
        select(CodeChunk.id)
        .where(
            CodeChunk.project_id == project_id,
            CodeChunk.embedding_status == "completed",
            CodeChunk.embedding.isnot(None),
        )
        .limit(1)
    )

    if embedded_chunk is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no generated embeddings. Generate embeddings before building the vector index.",
        )

    return faiss_service.build_project_index(db, project)


def get_project_vector_index_status(
    db: Session,
    project_id: int,
    user_id: int,
) -> VectorIndexStatusResponse:
    """
    Retrieves the FAISS vector index status and freshness for a project (Phase 35).
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    # Count current completed embedded chunks in DB
    completed_chunks_count = len(
        list(
            db.scalars(
                select(CodeChunk.id).where(
                    CodeChunk.project_id == project_id,
                    CodeChunk.embedding_status == "completed",
                    CodeChunk.embedding.isnot(None),
                )
            ).all()
        )
    )

    return faiss_service.get_project_index_status(project.id, completed_chunks_count)


def search_project_code(
    db: Session,
    project_id: int,
    user_id: int,
    query: str,
    top_k: int = 5,
) -> SearchResponse:
    """
    Safely executes semantic code retrieval using FAISS for an authenticated user's project (Phases 18–25):
    - Strictly verifies user tenancy.
    - Validates query presence and top_k bounds.
    - Verifies vector index existence.
    - Resolves results to CodeChunk records strictly belonging to the project.
    - Returns ranked chunks with cosine similarity scores.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    clean_query = (query or "").strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty.",
        )

    if top_k < 1 or top_k > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be an integer between 1 and 20.",
        )

    try:
        results = faiss_service.search(db, project, clean_query, top_k=top_k)
        return SearchResponse(
            project_id=project.id,
            query=clean_query,
            total_results=len(results),
            top_k=top_k,
            metric="cosine_similarity",
            results=results,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vector index not found. Build the project vector index before searching.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Semantic search failed. Please try again or rebuild the vector index.",
        )


def answer_project_question(
    db: Session,
    project_id: int,
    user_id: int,
    question: str,
    top_k: int = 5,
) -> RagResponse:
    """
    Safely executes RAG Q&A pipeline for an authenticated user's project (Phases 9, 17):
    - Strictly verifies user tenancy and ownership.
    - Reuses existing FAISS retrieval and LangChain pipeline via RagService.
    - Enforces grounded Gemma answers with real source citations.
    """
    project = get_project_by_id(db, project_id, user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )

    return rag_service.ask(db, project, question=question, top_k=top_k)

