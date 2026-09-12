from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """
    Structured metadata associated with an indexed code chunk (Phase 14).
    """
    project_id: int
    project_name: str
    file_path: str = Field(..., description="Project-relative POSIX file path")
    file_name: str
    file_extension: str
    language: str
    chunk_id: str
    chunk_index: int
    start_line: int
    end_line: int
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    parent_symbol: Optional[str] = None
    content_hash: str
    source_type: str = "code"


class CodeChunkResponse(BaseModel):
    """
    Indexed code chunk representation ready for Day 11 embedding consumption (Phase 19).
    """
    chunk_id: str
    content: str
    metadata: ChunkMetadata


class SkippedFileInfo(BaseModel):
    """
    Details of files skipped during indexing (Phase 27).
    """
    path: str
    status: str = "skipped"
    reason: str  # "binary_file", "file_too_large", "decode_error", etc.


class ProjectIndexResponse(BaseModel):
    """
    Result returned by POST /api/projects/{project_id}/index (Phases 23, 26).
    """
    project_id: int
    project_name: str
    status: str = "completed"  # "completed", "failed"
    total_files: int = 0
    indexed_files: int = 0
    skipped_files: int = 0
    total_chunks: int = 0
    languages: Dict[str, int] = Field(default_factory=dict)
    skipped_file_details: List[SkippedFileInfo] = Field(default_factory=list)


class ProjectIndexStatusResponse(BaseModel):
    """
    Read-only status response for GET /api/projects/{project_id}/index/status (Phase 22).
    """
    project_id: int
    status: str
    total_chunks: int = 0
    indexed_files: int = 0
    languages: Dict[str, int] = Field(default_factory=dict)
    last_indexed_at: Optional[datetime] = None
