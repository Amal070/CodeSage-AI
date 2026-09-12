import hashlib
import logging
import os
import posixpath
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.schemas.code_index import (
    ChunkMetadata,
    CodeChunkResponse,
    ProjectIndexResponse,
    ProjectIndexStatusResponse,
    SkippedFileInfo,
)
from app.services.code_parser import code_parser_service
from app.services.project_analyzer import (
    EXCLUDED_DIRECTORIES,
    EXTENSION_LANGUAGE_MAP,
)

logger = logging.getLogger(__name__)

# Configurable chunking settings (Phases 6 & 11)
DEFAULT_CHUNK_SIZE = 100      # Target max lines per chunk
DEFAULT_CHUNK_OVERLAP = 15    # Overlap lines between adjacent chunks
MAX_INDEXABLE_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB limit per file (Phase 6)

# Known binary extensions to skip immediately (Phase 4)
BINARY_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff", ".svgz",
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".dmg", ".msi",
    ".class", ".pyc", ".pyd", ".o", ".a", ".lib",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".db", ".sqlite", ".sqlite3"
}

# Source type classification by extension (Phase 17)
DOCUMENTATION_EXTENSIONS: Set[str] = {".md", ".markdown", ".txt", ".rst", ".adoc"}
CONFIG_EXTENSIONS: Set[str] = {".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".env"}


class CodeIndexerService:
    """
    Service responsible for Day 10 Code Indexing:
    - Recursively discovers project source code.
    - Applies structural and fallback line-based chunking.
    - Generates rich metadata, line numbers, deterministic chunk IDs, and SHA-256 hashes.
    - Persists CodeChunk records in PostgreSQL with idempotent re-indexing.
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        max_file_size: int = MAX_INDEXABLE_FILE_SIZE_BYTES,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_file_size = max_file_size

    def index_project(
        self,
        db: Session,
        project: Project,
        extracted_dir: Path,
    ) -> ProjectIndexResponse:
        """
        Executes the code indexing pipeline for an extracted project directory.
        Persists chunks in PostgreSQL and returns indexing statistics.
        """
        if not extracted_dir.exists() or not extracted_dir.is_dir():
            project.status = "failed"
            db.commit()
            return ProjectIndexResponse(
                project_id=project.id,
                project_name=project.name,
                status="failed",
                total_files=0,
                indexed_files=0,
                skipped_files=0,
                total_chunks=0,
                languages={},
                skipped_file_details=[],
            )

        # Update project status to indexing
        project.status = "indexing"
        db.commit()

        try:
            # 1. Discover all candidate files
            all_files = self._discover_files(extracted_dir)
            total_files = len(all_files)

            indexed_files_count = 0
            skipped_file_details: List[SkippedFileInfo] = []
            all_chunks: List[CodeChunk] = []
            languages_count: Dict[str, int] = {}

            # 2. Process each file
            for rel_path in all_files:
                full_path = extracted_dir / rel_path
                file_ext = Path(rel_path).suffix.lower()

                # A. Binary file check
                if file_ext in BINARY_EXTENSIONS:
                    skipped_file_details.append(
                        SkippedFileInfo(path=rel_path, status="skipped", reason="binary_file")
                    )
                    continue

                # B. File size check (Phase 6)
                try:
                    file_size = full_path.stat().st_size
                except OSError:
                    skipped_file_details.append(
                        SkippedFileInfo(path=rel_path, status="skipped", reason="stat_error")
                    )
                    continue

                if file_size > self.max_file_size:
                    skipped_file_details.append(
                        SkippedFileInfo(path=rel_path, status="skipped", reason="file_too_large")
                    )
                    continue

                # C. Safe text reading and decoding (Phase 7)
                content, decode_error = self._safe_read_file(full_path)
                if decode_error:
                    skipped_file_details.append(
                        SkippedFileInfo(path=rel_path, status="skipped", reason="decode_error")
                    )
                    continue

                # Empty file or binary null-byte check
                if "\x00" in content[:4096]:
                    skipped_file_details.append(
                        SkippedFileInfo(path=rel_path, status="skipped", reason="binary_file")
                    )
                    continue

                # D. Language & source_type detection (Phases 17 & 18)
                language = EXTENSION_LANGUAGE_MAP.get(file_ext, "Plain Text")
                source_type = self._detect_source_type(file_ext)

                # E. Chunk source code (Phases 8–13)
                file_chunks = self._chunk_file(
                    content=content,
                    rel_path=rel_path,
                    language=language,
                    file_ext=file_ext,
                    source_type=source_type,
                    project_id=project.id,
                    project_name=project.name,
                )

                if file_chunks:
                    indexed_files_count += 1
                    all_chunks.extend(file_chunks)
                    languages_count[language] = languages_count.get(language, 0) + len(file_chunks)

            # 3. Persistent storage & Idempotent replacement (Phases 20 & 24)
            # Delete existing chunks for this project in transaction to avoid duplicates
            db.execute(delete(CodeChunk).where(CodeChunk.project_id == project.id))

            # Bulk insert new chunks
            if all_chunks:
                db.add_all(all_chunks)

            # Update project status to indexed
            project.status = "indexed"
            db.commit()

            return ProjectIndexResponse(
                project_id=project.id,
                project_name=project.name,
                status="completed",
                total_files=total_files,
                indexed_files=indexed_files_count,
                skipped_files=len(skipped_file_details),
                total_chunks=len(all_chunks),
                languages=languages_count,
                skipped_file_details=skipped_file_details,
            )

        except Exception as e:
            logger.error("Failed to index project %s: %s", project.id, e, exc_info=True)
            db.rollback()
            try:
                project.status = "failed"
                db.commit()
            except Exception:
                db.rollback()

            return ProjectIndexResponse(
                project_id=project.id,
                project_name=project.name,
                status="failed",
                total_files=0,
                indexed_files=0,
                skipped_files=0,
                total_chunks=0,
                languages={},
                skipped_file_details=[],
            )

    # --------------------------------------------------------------------------
    # Discovery & Reading
    # --------------------------------------------------------------------------
    def _discover_files(self, extracted_dir: Path) -> List[str]:
        """
        Recursively discovers all candidate files in extracted directory.
        Prunes excluded directories (node_modules, .git, etc.).
        """
        discovered: List[str] = []
        for root, dirs, files in os.walk(extracted_dir):
            dirs[:] = [
                d for d in dirs
                if d not in EXCLUDED_DIRECTORIES and not d.startswith(".")
            ]
            for file_name in files:
                if file_name.startswith(".") and file_name not in {
                    ".env", ".env.example", ".gitignore"
                }:
                    continue
                full_path = Path(root) / file_name
                try:
                    rel = full_path.relative_to(extracted_dir).as_posix()
                    discovered.append(rel)
                except ValueError:
                    continue

        discovered.sort()
        return discovered

    def _safe_read_file(self, file_path: Path) -> Tuple[str, bool]:
        """
        Safely reads file with multiple encoding attempts.
        Returns (content, is_error).
        """
        encodings = ["utf-8", "utf-8-sig", "latin-1"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read(), False
            except UnicodeDecodeError:
                continue
            except Exception:
                return "", True
        return "", True

    def _detect_source_type(self, file_ext: str) -> str:
        """
        Classifies file content into code, config, or documentation (Phase 17).
        """
        if file_ext in DOCUMENTATION_EXTENSIONS:
            return "documentation"
        if file_ext in CONFIG_EXTENSIONS:
            return "config"
        return "code"

    # --------------------------------------------------------------------------
    # Code Chunking Engine (Phases 8–13)
    # --------------------------------------------------------------------------
    def _chunk_file(
        self,
        content: str,
        rel_path: str,
        language: str,
        file_ext: str,
        source_type: str,
        project_id: int,
        project_name: str,
    ) -> List[CodeChunk]:
        """
        Splits source code into chunks using Tree-sitter AST where supported,
        falling back to line-based chunking with overlap.
        """
        lines = content.splitlines(keepends=False)
        total_lines = len(lines)
        if total_lines == 0:
            return []

        chunks: List[CodeChunk] = []
        file_name = posixpath.basename(rel_path)

        # Check if language is supported by Day 7 Tree-sitter
        ts_lang = code_parser_service.detect_language(file_name)

        if ts_lang:
            chunks = self._structural_chunking(
                lines=lines,
                ts_lang=ts_lang,
                rel_path=rel_path,
                file_name=file_name,
                file_ext=file_ext,
                language=language,
                source_type=source_type,
                project_id=project_id,
            )

        # If structural chunking produced no chunks (or language unsupported), use fallback
        if not chunks:
            chunks = self._line_based_chunking(
                lines=lines,
                rel_path=rel_path,
                file_name=file_name,
                file_ext=file_ext,
                language=language,
                source_type=source_type,
                project_id=project_id,
            )

        return chunks

    def _structural_chunking(
        self,
        lines: List[str],
        ts_lang: str,
        rel_path: str,
        file_name: str,
        file_ext: str,
        language: str,
        source_type: str,
        project_id: int,
    ) -> List[CodeChunk]:
        """
        Uses Day 7 Tree-sitter parser to identify classes, methods, and functions,
        turning them into natural structural chunks (Phases 9 & 10).
        """
        content_str = "\n".join(lines)
        parse_result = code_parser_service.parse_source_code(
            source_code=content_str, language=ts_lang, relative_path=rel_path
        )

        total_lines = len(lines)
        chunks: List[CodeChunk] = []
        chunk_idx = 1

        # Collect symbols
        symbols = []
        for c in parse_result.classes:
            symbols.append({
                "name": c.name,
                "type": "class",
                "start": max(1, c.line_start),
                "end": min(total_lines, c.line_end),
                "parent": None,
            })
        for f in parse_result.functions:
            symbols.append({
                "name": f.name,
                "type": f.type,  # "function" or "method"
                "start": max(1, f.line_start),
                "end": min(total_lines, f.line_end),
                "parent": f.parent_class,
            })

        if not symbols:
            return []

        # Sort symbols by start line
        symbols.sort(key=lambda s: (s["start"], s["end"]))

        # Check top-level preamble before first symbol (e.g. imports / module setup)
        first_symbol_start = symbols[0]["start"]
        if first_symbol_start > 1:
            preamble_lines = lines[: first_symbol_start - 1]
            preamble_text = "\n".join(preamble_lines).strip()
            if preamble_text:
                end_l = first_symbol_start - 1
                for sub_start, sub_end in self._subdivide_range(1, end_l):
                    chunk = self._build_chunk_record(
                        lines=lines,
                        start_line=sub_start,
                        end_line=sub_end,
                        symbol_name=None,
                        symbol_type="module",
                        parent_symbol=None,
                        chunk_index=chunk_idx,
                        project_id=project_id,
                        rel_path=rel_path,
                        file_name=file_name,
                        file_ext=file_ext,
                        language=language,
                        source_type=source_type,
                    )
                    chunks.append(chunk)
                    chunk_idx += 1

        # Process each symbol
        for sym in symbols:
            start_l = sym["start"]
            end_l = sym["end"]
            if start_l > end_l or start_l > total_lines:
                continue

            # Subdivide large structures if they exceed chunk_size (Phase 11)
            sub_ranges = self._subdivide_range(start_l, end_l)
            for sub_start, sub_end in sub_ranges:
                chunk = self._build_chunk_record(
                    lines=lines,
                    start_line=sub_start,
                    end_line=sub_end,
                    symbol_name=sym["name"],
                    symbol_type=sym["type"],
                    parent_symbol=sym["parent"],
                    chunk_index=chunk_idx,
                    project_id=project_id,
                    rel_path=rel_path,
                    file_name=file_name,
                    file_ext=file_ext,
                    language=language,
                    source_type=source_type,
                )
                chunks.append(chunk)
                chunk_idx += 1

        return chunks

    def _line_based_chunking(
        self,
        lines: List[str],
        rel_path: str,
        file_name: str,
        file_ext: str,
        language: str,
        source_type: str,
        project_id: int,
    ) -> List[CodeChunk]:
        """
        Fallback line-based overlapping chunking (Phase 12).
        """
        total_lines = len(lines)
        if total_lines == 0:
            return []

        chunks: List[CodeChunk] = []
        chunk_idx = 1

        sub_ranges = self._subdivide_range(1, total_lines)
        for start_l, end_l in sub_ranges:
            chunk = self._build_chunk_record(
                lines=lines,
                start_line=start_l,
                end_line=end_l,
                symbol_name=None,
                symbol_type=None,
                parent_symbol=None,
                chunk_index=chunk_idx,
                project_id=project_id,
                rel_path=rel_path,
                file_name=file_name,
                file_ext=file_ext,
                language=language,
                source_type=source_type,
            )
            chunks.append(chunk)
            chunk_idx += 1

        return chunks

    def _subdivide_range(self, start_line: int, end_line: int) -> List[Tuple[int, int]]:
        """
        Splits a line range [start_line, end_line] into overlapping ranges
        based on chunk_size and chunk_overlap.
        """
        total = end_line - start_line + 1
        if total <= self.chunk_size:
            return [(start_line, end_line)]

        ranges: List[Tuple[int, int]] = []
        curr_start = start_line

        while curr_start <= end_line:
            curr_end = min(curr_start + self.chunk_size - 1, end_line)
            ranges.append((curr_start, curr_end))
            if curr_end == end_line:
                break
            step = self.chunk_size - self.chunk_overlap
            if step <= 0:
                step = 1
            curr_start = curr_start + step

        return ranges

    def _build_chunk_record(
        self,
        lines: List[str],
        start_line: int,
        end_line: int,
        symbol_name: Optional[str],
        symbol_type: Optional[str],
        parent_symbol: Optional[str],
        chunk_index: int,
        project_id: int,
        rel_path: str,
        file_name: str,
        file_ext: str,
        language: str,
        source_type: str,
    ) -> CodeChunk:
        """
        Builds a CodeChunk model instance with deterministic chunk_id,
        SHA-256 content_hash, and preserved source content (Phases 13–16).
        """
        chunk_slice = lines[start_line - 1 : end_line]
        content_text = "\n".join(chunk_slice)
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

        # Deterministic chunk ID (Phase 15)
        clean_rel = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", rel_path)
        chunk_id = f"p{project_id}_{clean_rel}_c{chunk_index:04d}_{content_hash[:8]}"

        return CodeChunk(
            project_id=project_id,
            chunk_id=chunk_id,
            file_path=rel_path,
            file_name=file_name,
            file_extension=file_ext,
            language=language,
            source_type=source_type,
            start_line=start_line,
            end_line=end_line,
            symbol_name=symbol_name,
            symbol_type=symbol_type,
            parent_symbol=parent_symbol,
            chunk_index=chunk_index,
            content_hash=content_hash,
            content=content_text,
        )


# Global singleton instance
code_indexer_service = CodeIndexerService()
