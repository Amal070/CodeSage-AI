from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.project import (
    ProjectResponse,
    ProjectUploadResponse,
    ProjectFileTreeResponse,
    FileContentResponse,
)
from app.schemas.code_parser import CodeParseResponse
from app.schemas.project_analysis import ProjectAnalysisResponse
from app.schemas.dependency_analysis import DependencyAnalysisResponse
from app.schemas.code_index import (
    CodeChunkResponse,
    ProjectIndexResponse,
    ProjectIndexStatusResponse,
)
from app.schemas.embedding import (
    ProjectEmbeddingResponse,
    ProjectEmbeddingStatusResponse,
)
from app.schemas.semantic_search import (
    VectorIndexBuildResponse,
    VectorIndexStatusResponse,
    SearchRequest,
    SearchResponse,
)
from app.schemas.rag import RagRequest, RagResponse
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryItem
from app.services.chat_service import chat_service
from app.services.project_service import (
    process_project_upload,
    get_user_projects,
    get_project_by_id,
    get_project_file_tree,
    get_project_file_content,
    parse_project_source_file,
    analyze_project,
    analyze_project_dependencies,
    index_project_code,
    get_project_index_status,
    get_project_chunks,
    generate_project_embeddings,
    get_project_embedding_status,
    build_project_vector_index,
    get_project_vector_index_status,
    search_project_code,
    answer_project_question,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "/upload",
    response_model=ProjectUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and unpack project ZIP archive",
)
async def upload_project(
    file: UploadFile = File(..., description="Project source code ZIP archive (.zip)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Authenticated project upload endpoint:
    - Accepts multipart/form-data ZIP file
    - Validates file extension, magic bytes, and integrity
    - Enforces maximum upload file size (MAX_UPLOAD_SIZE_MB)
    - Performs safe extraction with Zip Slip defense
    - Stores project records and file metadata in PostgreSQL
    - Assigns project ownership directly to the authenticated user (derived from JWT)
    """
    project = await process_project_upload(db, file, current_user.id)
    return ProjectUploadResponse(
        message="Project uploaded successfully",
        project=ProjectResponse.model_validate(project),
    )


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List all projects for the authenticated user",
)
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves all projects belonging to the authenticated user.
    """
    projects = get_user_projects(db, current_user.id)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details by ID",
)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves project details by ID, ensuring the project belongs to the authenticated user.
    """
    project = get_project_by_id(db, project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you do not have permission to access it.",
        )
    return ProjectResponse.model_validate(project)


@router.get(
    "/{project_id}/files",
    response_model=ProjectFileTreeResponse,
    summary="Get recursive file and folder tree of project",
)
def get_project_files(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the recursive folder and file tree for an extracted project.
    - Strictly verifies user ownership of the project.
    - Returns hierarchical tree relative to the extracted project root.
    - Never exposes server absolute filesystem paths.
    """
    tree_data = get_project_file_tree(db, project_id, current_user.id)
    return tree_data


@router.get(
    "/{project_id}/file",
    response_model=FileContentResponse,
    summary="Get source code or text content of a file",
)
def get_project_file(
    project_id: int,
    path: str = Query(..., description="Relative file path within the project (e.g. src/main.py)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safely retrieves the content of a file within an extracted project.
    - Requires authentication and verifies project ownership.
    - Prevents directory traversal attacks (../, absolute paths).
    - Protects against reading excessively large files (MAX_VIEWABLE_FILE_SIZE_MB).
    - Identifies binary files safely without crashing or corrupting memory.
    - Detects language for frontend syntax display.
    """
    file_data = get_project_file_content(db, project_id, current_user.id, path)
    return file_data


@router.get(
    "/{project_id}/parse",
    response_model=CodeParseResponse,
    summary="Parse source code structure using Tree-sitter",
)
def parse_project_file(
    project_id: int,
    path: str = Query(..., description="Relative file path within the project (e.g. src/main.py)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safely parses functions, classes, and imports of a supported source file (.py, .java, .js)
    using Tree-sitter:
    - Requires authentication and verifies project ownership.
    - Prevents directory traversal attacks (../, absolute paths).
    - Protects against reading excessively large files (MAX_VIEWABLE_FILE_SIZE_MB).
    - Rejects unsupported extensions with 400 Bad Request.
    - Handles syntax errors gracefully without crashing.
    """
    parsed_data = parse_project_source_file(db, project_id, current_user.id, path)
    return parsed_data


@router.get(
    "/{project_id}/analysis",
    response_model=ProjectAnalysisResponse,
    summary="Analyze project statistics, language breakdown, and folder hierarchy",
)
def get_project_analysis(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safely analyzes project statistics, programming language distributions,
    file extension counts, and folder hierarchy for an authenticated user's project.
    - Requires authentication and verifies project ownership.
    - Never returns raw source code contents or exposes absolute server paths.
    - Handles empty projects gracefully.
    """
    analysis_data = analyze_project(db, project_id, current_user.id)
    return analysis_data


@router.get(
    "/{project_id}/dependencies",
    response_model=DependencyAnalysisResponse,
    summary="Analyze project dependencies, imports, and relationships",
)
def get_project_dependencies(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safely analyzes imports, external packages, local file relationships, and
    dependency graph structure for an authenticated user's project.
    - Requires authentication and verifies project ownership.
    - Statically parses source files using Tree-sitter and manifests.
    - Never executes project code or installs dependencies.
    - Never exposes absolute server filesystem paths.
    - Handles empty projects gracefully.
    """
    dependency_data = analyze_project_dependencies(db, project_id, current_user.id)
    return dependency_data


@router.post(
    "/{project_id}/index",
    response_model=ProjectIndexResponse,
    summary="Index project source code into structured code chunks",
)
def index_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safely indexes source code from the extracted project archive:
    - Verifies user ownership of project.
    - Applies structural AST parsing (Tree-sitter) for Python, JS/JSX, Java.
    - Applies line-based fallback chunking with overlap for other text files.
    - Generates metadata (symbols, line numbers, hashes, languages, source_type).
    - Persists CodeChunk records in PostgreSQL with idempotent re-indexing.
    - Returns indexing statistics and skipped file details.
    """
    index_result = index_project_code(db, project_id, current_user.id)
    return index_result


@router.get(
    "/{project_id}/index/status",
    response_model=ProjectIndexStatusResponse,
    summary="Get project code indexing status and chunk count",
)
def get_indexing_status(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns current indexing status, total chunk count, and indexed files count.
    """
    status_data = get_project_index_status(db, project_id, current_user.id)
    return status_data


@router.get(
    "/{project_id}/chunks",
    response_model=List[CodeChunkResponse],
    summary="Get stored code chunks and metadata (ready for Day 11)",
)
def get_chunks(
    project_id: int,
    limit: int = Query(50, ge=1, le=500, description="Max chunks to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns stored code chunks and metadata prepared for Day 11 embedding generation.
    """
    chunks = get_project_chunks(db, project_id, current_user.id, limit=limit, offset=offset)
    return chunks


@router.post(
    "/{project_id}/embeddings",
    response_model=ProjectEmbeddingResponse,
    summary="Generate vector embeddings for project code chunks using Nomic Embed Text",
)
def generate_embeddings(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Day 11 Embedding Generation Endpoint:
    - Strictly verifies JWT authentication and project tenancy.
    - Requires project to have indexed code chunks from Day 10.
    - Formats code content with Nomic task prefix 'search_document: '.
    - Generates 768-dimensional normalized embeddings using Nomic Embed Text.
    - Persists vectors to PostgreSQL.
    - Skips already-embedded unchanged chunks via content hash comparison.
    - Returns comprehensive generation statistics.
    """
    return generate_project_embeddings(db, project_id, current_user.id)


@router.get(
    "/{project_id}/embeddings/status",
    response_model=ProjectEmbeddingStatusResponse,
    summary="Get project embedding generation status and statistics",
)
def get_embedding_status(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the current status, chunk counts, model information, and dimension
    for project code embeddings.
    """
    return get_project_embedding_status(db, project_id, current_user.id)


@router.post(
    "/{project_id}/vector-index",
    response_model=VectorIndexBuildResponse,
    summary="Build or rebuild FAISS vector index for project code chunks",
)
def build_vector_index(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Day 12 FAISS Index Construction Endpoint:
    - Strictly verifies JWT authentication and project tenancy.
    - Requires project to have generated embeddings from Day 11.
    - Constructs an exact faiss.IndexFlatIP index (cosine similarity).
    - Persists index and mapping file in isolated project storage.
    - Returns vector count and index metadata.
    """
    return build_project_vector_index(db, project_id, current_user.id)


@router.get(
    "/{project_id}/vector-index/status",
    response_model=VectorIndexStatusResponse,
    summary="Get project FAISS vector index status and freshness",
)
def get_vector_index_status(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the vector index status (ready, not_built, stale, empty),
    vector count, dimension, and metric.
    """
    return get_project_vector_index_status(db, project_id, current_user.id)


@router.get(
    "/{project_id}/search",
    response_model=SearchResponse,
    summary="Semantic code search using FAISS and Nomic Embed Text query embeddings",
)
def search_project_get(
    project_id: int,
    query: str = Query(..., min_length=1, description="Natural-language code search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of top results to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Day 12 Semantic Retrieval Endpoint (GET):
    - Strictly verifies JWT authentication and project tenancy.
    - Generates query embedding using the same Nomic Embed Text model (search_query: prefix).
    - Searches project's FAISS index for top-k semantically similar code chunks.
    - Returns code chunks, file metadata, lines, symbols, and cosine similarity scores.
    """
    return search_project_code(db, project_id, current_user.id, query=query, top_k=top_k)


@router.post(
    "/{project_id}/search",
    response_model=SearchResponse,
    summary="Semantic code search (POST body)",
)
def search_project_post(
    project_id: int,
    search_req: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Day 12 Semantic Retrieval Endpoint (POST):
    - Supports JSON body search requests for longer queries.
    """
    return search_project_code(
        db,
        project_id,
        current_user.id,
        query=search_req.query,
        top_k=search_req.top_k,
    )


@router.post(
    "/{project_id}/rag",
    response_model=RagResponse,
    summary="CodeSage AI Retrieval-Augmented Generation (RAG) Code Q&A",
)
def rag_project_question(
    project_id: int,
    rag_req: RagRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Day 14 LangChain + RAG Pipeline Endpoint:
    - Strictly verifies JWT authentication and project tenancy.
    - Retrieves top-k semantically relevant code chunks via FAISS (Nomic Embed Text).
    - Converts chunks into LangChain Documents with full metadata.
    - Constructs context with safety limits and truncation controls.
    - Invokes Gemma 2B via LangChain ChatOllama using grounded PromptTemplate.
    - Returns grounded answer with verified source citations.
    """
    return answer_project_question(
        db,
        project_id,
        current_user.id,
        question=rag_req.question,
        top_k=rag_req.top_k,
    )


@router.post(
    "/{project_id}/ask",
    response_model=RagResponse,
    summary="CodeSage AI RAG Code Q&A (alias for /rag)",
)
def ask_project_question(
    project_id: int,
    rag_req: RagRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Convenience alias endpoint matching POST /api/projects/{project_id}/ask.
    """
    return answer_project_question(
        db,
        project_id,
        current_user.id,
        question=rag_req.question,
        top_k=rag_req.top_k,
    )


# ============================================================
# Day 15 — AI Chat Endpoints
# ============================================================

@router.post(
    "/{project_id}/chat",
    response_model=ChatResponse,
    summary="CodeSage AI Chat with Project Codebase",
)
def chat_with_project(
    project_id: int,
    chat_req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Day 15 AI Chat Endpoint:
    - Requires valid JWT authentication.
    - Strictly verifies project ownership / tenancy.
    - Validates question and optional top_k retrieval parameters.
    - Reuses Day 14 RAG pipeline (Nomic Embed Text + FAISS retrieval + Gemma 2B via LangChain).
    - Persists conversation exchange in the PostgreSQL chat_history table.
    - Returns grounded answer, source chunk citations with file paths and line numbers, and chat record ID.
    """
    return chat_service.send_message(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        question=chat_req.question,
        top_k=chat_req.top_k,
    )


@router.get(
    "/{project_id}/chat",
    response_model=List[ChatHistoryItem],
    summary="Retrieve Stored Chat History for Project",
)
def get_project_chat_history(
    project_id: int,
    limit: int = Query(default=50, ge=1, le=100, description="Max history items to retrieve"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves stored conversation history for the authenticated user and project.
    """
    return chat_service.get_project_chat_history(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        limit=limit,
    )


@router.delete(
    "/{project_id}/chat",
    summary="Clear Stored Chat History for Project",
)
def clear_project_chat_history(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Deletes all conversation history for the authenticated user and project.
    """
    return chat_service.clear_project_chat_history(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
    )


