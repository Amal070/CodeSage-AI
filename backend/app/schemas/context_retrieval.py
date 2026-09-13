from typing import List, Optional, Union
from pydantic import BaseModel, Field


class RetrievedChunkItem(BaseModel):
    """
    Individual code chunk retrieved from a matching project file (Day 17).
    """
    chunk_id: Union[str, int] = Field(..., description="Unique CodeSage chunk identifier")
    score: float = Field(..., description="Cosine similarity score (higher is more similar)")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    symbol_name: Optional[str] = Field(None, description="Function/class/method symbol name")
    symbol_type: Optional[str] = Field(None, description="Symbol type (function, class, etc.)")
    language: Optional[str] = Field(None, description="Programming language")
    content: str = Field(..., description="Raw code chunk content")


class RetrievedFileItem(BaseModel):
    """
    Ranked project file containing matching code chunks (Day 17).
    """
    file_path: str = Field(..., description="Project-relative file path")
    file_name: Optional[str] = Field(None, description="File basename")
    file_score: float = Field(..., description="Aggregated file relevance score (0.0 to 1.0)")
    chunk_count: int = Field(default=0, description="Number of matching candidate chunks from this file")
    chunks: List[RetrievedChunkItem] = Field(
        default_factory=list,
        description="Top matching chunks selected from this file",
    )


class ContextRetrievalRequest(BaseModel):
    """
    Request schema for Day 17 context retrieval endpoint (POST /api/projects/{project_id}/context/retrieve).
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural-language search query about the project codebase",
    )
    top_files: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of top matching files to retrieve (1 to 10)",
    )
    candidate_chunks: int = Field(
        default=30,
        ge=5,
        le=50,
        description="Number of initial candidate chunks to retrieve from FAISS before file ranking",
    )
    chunks_per_file: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum number of top chunks to extract per ranked file",
    )


class ContextRetrievalResponse(BaseModel):
    """
    Response schema for Day 17 context retrieval endpoint (POST /api/projects/{project_id}/context/retrieve).
    """
    project_id: int = Field(..., description="Project identifier")
    query: str = Field(..., description="Search query executed")
    total_candidate_chunks: int = Field(..., description="Total candidate chunks retrieved from FAISS")
    total_matching_files: int = Field(..., description="Total distinct files identified from candidates")
    files: List[RetrievedFileItem] = Field(
        default_factory=list,
        description="Top matching files ranked by relevance score",
    )
