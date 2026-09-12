from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class VectorIndexBuildResponse(BaseModel):
    """
    Response returned by POST /api/projects/{project_id}/vector-index (Phase 11).
    """
    project_id: int
    status: str = "completed"
    indexed_vectors: int
    embedding_dimension: int
    index_type: str = "IndexFlatIP"
    metric: str = "cosine_similarity"


class VectorIndexStatusResponse(BaseModel):
    """
    Response returned by GET /api/projects/{project_id}/vector-index/status (Phase 35).
    """
    project_id: int
    status: str  # "ready", "not_built", "stale", "empty"
    indexed_vectors: int = 0
    embedding_dimension: Optional[int] = None
    index_type: Optional[str] = None
    metric: Optional[str] = None
    last_indexed_at: Optional[datetime] = None


class SearchResultMetadata(BaseModel):
    """
    Structured metadata for a retrieved search result item (Phase 20).
    """
    file_path: str
    file_name: str
    file_extension: str
    language: str
    start_line: int
    end_line: int
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    source_type: str = "code"


class SearchResultItem(BaseModel):
    """
    Individual code chunk result from FAISS semantic search (Phase 20).
    """
    chunk_id: str
    score: float = Field(..., description="Cosine similarity score (higher is more similar)")
    content: str
    metadata: SearchResultMetadata


class SearchRequest(BaseModel):
    """
    Search request body for POST /api/projects/{project_id}/search.
    """
    query: str = Field(..., min_length=1, description="Natural-language search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top results to retrieve")


class SearchResponse(BaseModel):
    """
    Semantic code search response returned by search endpoints (Phases 18, 20).
    """
    project_id: int
    query: str
    total_results: int
    top_k: int
    metric: str = "cosine_similarity"
    results: List[SearchResultItem]
