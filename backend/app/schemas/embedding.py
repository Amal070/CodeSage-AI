from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChunkEmbeddingFailure(BaseModel):
    """
    Records information about a chunk that failed embedding generation.
    """
    chunk_id: str
    reason: str


class ProjectEmbeddingResponse(BaseModel):
    """
    Response returned by POST /api/projects/{project_id}/embeddings.
    """
    project_id: int
    project_name: str
    status: str = "completed"  # "completed", "failed", "partial_failure"
    total_chunks: int = 0
    embedded_chunks: int = 0
    skipped_chunks: int = 0
    failed_chunks: int = 0
    embedding_dimension: int = 768
    model: str
    failed_details: List[ChunkEmbeddingFailure] = Field(default_factory=list)


class ProjectEmbeddingStatusResponse(BaseModel):
    """
    Status response returned by GET /api/projects/{project_id}/embeddings/status.
    """
    project_id: int
    status: str  # "ready", "not_generated", "generating", "partial_failure"
    total_chunks: int = 0
    embedded_chunks: int = 0
    skipped_chunks: int = 0
    failed_chunks: int = 0
    embedding_dimension: Optional[int] = None
    model: Optional[str] = None
    last_embedded_at: Optional[datetime] = None
