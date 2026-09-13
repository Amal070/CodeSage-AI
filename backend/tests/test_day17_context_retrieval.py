"""
CodeSage AI — Day 17 Automated Test Suite: Context Retrieval

Tests:
1. File relevance scoring algorithm (best chunk dominance, supporting chunks bonus).
2. Score direction correctness (higher inner product/cosine similarity = higher score).
3. Duplicate chunk resistance (preventing repetitive chunks from dominating strong single matches).
4. Stable project-relative path grouping (backend/auth.py vs frontend/auth.py isolation).
5. Top-file limit and chunks-per-file truncation enforcement.
6. Noise & minimum similarity threshold filtering.
7. Metadata preservation (start_line, end_line, symbol_name, symbol_type, file_path, score).
8. API Endpoint authentication and tenancy isolation (User A vs User B, Project A vs Project B).
9. Context Retrieval API endpoint POST /api/projects/{project_id}/context/retrieve.
10. Clean error response for unindexed projects / missing FAISS indexes.
11. RAG pipeline integration with file-level retrieval.
"""

from datetime import datetime, timezone
import uuid
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.services.context_retriever import context_retriever, ContextRetrievalResult
from app.schemas.context_retrieval import (
    RetrievedChunkItem,
    RetrievedFileItem,
    ContextRetrievalResponse,
)
from app.schemas.semantic_search import SearchResultItem, SearchResultMetadata

client = TestClient(app)


# ==============================================================================
# TEST FIXTURES & HELPERS
# ==============================================================================

@pytest.fixture
def user_a():
    """Create User A."""
    unique_email = f"day17_user_a_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Day 17 User A",
            email=unique_email,
            password_hash=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id), "email": unique_email})
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers


@pytest.fixture
def user_b():
    """Create User B."""
    unique_email = f"day17_user_b_{uuid.uuid4().hex[:8]}@codesage.ai"
    db = next(get_db())
    try:
        user = User(
            name="Day 17 User B",
            email=unique_email,
            password_hash=hash_password("Password123!"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id
    finally:
        db.close()

    token = create_access_token(data={"sub": str(user_id), "email": unique_email})
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers


def create_project(user_id: int, name: str = "Day 17 Test Project") -> int:
    """Helper to insert a test project."""
    db = next(get_db())
    try:
        project = Project(
            name=name,
            original_filename=f"{name}.zip",
            storage_path=f"storage/projects/mock_{uuid.uuid4().hex[:6]}",
            extracted_path=f"storage/projects/mock_{uuid.uuid4().hex[:6]}/extracted",
            file_count=3,
            lines_of_code=150,
            status="completed",
            user_id=user_id,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project.id
    finally:
        db.close()


def make_search_result(
    chunk_id: int,
    file_path: str,
    score: float,
    start_line: int = 1,
    end_line: int = 20,
    content: str = "test code",
    symbol_name: str = None,
    symbol_type: str = None,
    language: str = "python",
    file_extension: str = None,
) -> SearchResultItem:
    """Helper to create a SearchResultItem with complete metadata."""
    ext = file_extension or ("." + file_path.rsplit(".", 1)[-1] if "." in file_path else ".py")
    return SearchResultItem(
        chunk_id=str(chunk_id),
        score=score,
        content=content,
        metadata=SearchResultMetadata(
            file_path=file_path,
            file_name=file_path.split("/")[-1],
            file_extension=ext,
            language=language,
            start_line=start_line,
            end_line=end_line,
            symbol_name=symbol_name,
            symbol_type=symbol_type,
            source_type="code",
        ),
    )


# ==============================================================================
# 1. FILE RELEVANCE SCORING & SCORE DIRECTION TESTS
# ==============================================================================

def test_file_relevance_scoring_direction():
    """Verify that higher similarity scores produce higher file relevance scores."""
    high_score = context_retriever.calculate_file_relevance_score([0.95, 0.90, 0.85])
    medium_score = context_retriever.calculate_file_relevance_score([0.70, 0.65, 0.60])
    low_score = context_retriever.calculate_file_relevance_score([0.35, 0.30])

    assert high_score > medium_score > low_score
    assert 0.0 <= low_score <= 1.0
    assert 0.0 <= high_score <= 1.0


def test_duplicate_chunk_resistance():
    """
    Step 9: A file containing many repetitive/duplicate chunks must NOT dominate
    over a file that has a significantly stronger top match.
    File A: 10 repetitive chunks of score 0.70
    File B: 2 chunks of score 0.95 and 0.88
    """
    repetitive_file_scores = [0.70] * 10
    strong_match_scores = [0.95, 0.88]

    score_repetitive = context_retriever.calculate_file_relevance_score(repetitive_file_scores)
    score_strong = context_retriever.calculate_file_relevance_score(strong_match_scores)

    # Strong match file must score higher than the repetitive file
    assert score_strong > score_repetitive, (
        f"File with 0.95 peak score ({score_strong}) should rank higher than "
        f"repetitive 0.70 file ({score_repetitive})"
    )


def test_supporting_chunk_bonus():
    """Verify that multiple distinct strong chunks boost score over a single isolated chunk."""
    single_chunk = [0.90]
    multi_chunks = [0.90, 0.88, 0.85]

    score_single = context_retriever.calculate_file_relevance_score(single_chunk)
    score_multi = context_retriever.calculate_file_relevance_score(multi_chunks)

    assert score_multi > score_single
    assert score_multi <= 1.0


# ==============================================================================
# 2. GROUPING & PATH SEPARATION TESTS
# ==============================================================================

def test_group_chunks_by_relative_file_path(monkeypatch):
    """
    Step 7: Candidate chunks must be grouped by full project-relative path.
    backend/auth.py and frontend/auth.py must remain distinct files.
    """
    mock_candidates = [
        make_search_result(
            chunk_id=1,
            file_path="backend/auth.py",
            score=0.92,
            start_line=1,
            end_line=25,
            content="def authenticate(): pass",
            symbol_name="authenticate",
            symbol_type="function",
        ),
        make_search_result(
            chunk_id=2,
            file_path="frontend/auth.py",
            score=0.88,
            start_line=1,
            end_line=30,
            content="export function useAuth() {}",
            symbol_name="useAuth",
            symbol_type="function",
        ),
        make_search_result(
            chunk_id=3,
            file_path="backend/auth.py",
            score=0.95,
            start_line=30,
            end_line=60,
            content="def create_token(): pass",
            symbol_name="create_token",
            symbol_type="function",
        ),
    ]

    monkeypatch.setattr(
        "app.services.faiss_service.faiss_service.search",
        lambda db, project, query, top_k: mock_candidates,
    )

    db = next(get_db())
    try:
        results = context_retriever.retrieve_context(
            db=db,
            project=1,
            query="Explain authentication",
            top_files=5,
            chunks_per_file=3,
        )

        file_paths = [f.file_path for f in results.files]
        assert "backend/auth.py" in file_paths
        assert "frontend/auth.py" in file_paths
        assert len(results.files) == 2

        # backend/auth.py had highest score (0.95) so it should rank #1
        assert results.files[0].file_path == "backend/auth.py"
        assert len(results.files[0].chunks) == 2  # chunks 3 and 1
        assert results.files[1].file_path == "frontend/auth.py"
        assert len(results.files[1].chunks) == 1
    finally:
        db.close()


# ==============================================================================
# 3. TOP FILES AND CHUNKS LIMITS TESTS
# ==============================================================================

def test_top_files_and_chunks_per_file_limits(monkeypatch):
    """
    Step 5 & 10: System returns at most top_files, and at most chunks_per_file per file.
    """
    mock_candidates = []
    # Create 8 different files, each with 5 chunks
    for file_idx in range(8):
        file_path = f"app/services/module_{file_idx}.py"
        for chunk_idx in range(5):
            mock_candidates.append(
                make_search_result(
                    chunk_id=file_idx * 10 + chunk_idx,
                    file_path=file_path,
                    score=0.50 + (file_idx * 0.05) + (chunk_idx * 0.01),
                    start_line=chunk_idx * 20 + 1,
                    end_line=chunk_idx * 20 + 20,
                    content=f"print('module {file_idx} chunk {chunk_idx}')",
                    symbol_name=f"func_{chunk_idx}",
                    symbol_type="function",
                )
            )

    monkeypatch.setattr(
        "app.services.faiss_service.faiss_service.search",
        lambda db, project, query, top_k: mock_candidates,
    )

    db = next(get_db())
    try:
        # Request top 3 files, 2 chunks per file
        results = context_retriever.retrieve_context(
            db=db,
            project=1,
            query="test query",
            top_files=3,
            chunks_per_file=2,
        )

        assert len(results.files) == 3
        for f in results.files:
            assert len(f.chunks) <= 2
    finally:
        db.close()


# ==============================================================================
# 4. NOISE & SIMILARITY THRESHOLD FILTERING
# ==============================================================================

def test_low_similarity_threshold_filtering(monkeypatch):
    """
    Step 19: If candidate results are all poor similarity (< threshold),
    they should be discarded cleanly.
    """
    mock_candidates = [
        make_search_result(
            chunk_id=101,
            file_path="random_unrelated.py",
            score=0.12,  # Below default 0.20 threshold
            content="# some noise",
        )
    ]

    monkeypatch.setattr(
        "app.services.faiss_service.faiss_service.search",
        lambda db, project, query, top_k: mock_candidates,
    )

    db = next(get_db())
    try:
        results = context_retriever.retrieve_context(
            db=db,
            project=1,
            query="unrelated query",
            min_similarity=0.20,
        )

        assert len(results.files) == 0
        assert results.total_matching_files == 0
        assert results.total_candidate_chunks == 1
    finally:
        db.close()


# ==============================================================================
# 5. METADATA PRESERVATION
# ==============================================================================

def test_metadata_preservation(monkeypatch):
    """
    Step 12: Ensure all metadata fields (file_path, start_line, end_line,
    symbol_name, symbol_type, score, content) are strictly preserved.
    """
    mock_candidate = make_search_result(
        chunk_id=42,
        file_path="app/core/security.py",
        score=0.945,
        start_line=15,
        end_line=35,
        symbol_name="create_access_token",
        symbol_type="function",
        content="def create_access_token(): pass",
    )

    monkeypatch.setattr(
        "app.services.faiss_service.faiss_service.search",
        lambda db, project, query, top_k: [mock_candidate],
    )

    db = next(get_db())
    try:
        results = context_retriever.retrieve_context(
            db=db,
            project=1,
            query="create_access_token",
        )

        assert len(results.files) == 1
        top_file = results.files[0]
        assert top_file.file_path == "app/core/security.py"
        assert len(top_file.chunks) == 1

        chunk = top_file.chunks[0]
        assert str(chunk.chunk_id) == "42"
        assert chunk.start_line == 15
        assert chunk.end_line == 35
        assert chunk.symbol_name == "create_access_token"
        assert chunk.symbol_type == "function"
        assert chunk.score == 0.945
        assert chunk.content == "def create_access_token(): pass"
    finally:
        db.close()


# ==============================================================================
# 6. RETRIEVAL API ENDPOINT & TENANCY TESTS
# ==============================================================================

def test_context_retrieval_unauthorized():
    """POST /api/projects/{id}/context/retrieve without JWT token must return 401."""
    response = client.post("/api/projects/1/context/retrieve", json={"query": "auth"})
    assert response.status_code == 401


def test_context_retrieval_tenancy_isolation(user_a, user_b):
    """User B cannot retrieve context for User A's project (returns 404)."""
    user_a_id, _, _ = user_a
    _, _, headers_b = user_b

    project_a_id = create_project(user_a_id, "User A Secret Project")

    response = client.post(
        f"/api/projects/{project_a_id}/context/retrieve",
        headers=headers_b,
        json={"query": "Where is secret logic?"},
    )
    assert response.status_code == 404


def test_context_retrieval_success(user_a, monkeypatch):
    """Owner can retrieve structured file context via POST /api/projects/{id}/context/retrieve."""
    user_a_id, _, headers_a = user_a
    project_id = create_project(user_a_id, "Context Retrieval Project")

    mock_candidates = [
        make_search_result(
            chunk_id=1,
            file_path="app/core/security.py",
            score=0.91,
            start_line=10,
            end_line=30,
            content="def hash_password(): ...",
            symbol_name="hash_password",
            symbol_type="function",
        )
    ]

    from pathlib import Path
    monkeypatch.setattr(
        "app.services.faiss_service.faiss_service.get_index_file_paths",
        lambda pid: (Path(__file__), Path(__file__)),
    )
    monkeypatch.setattr(
        "app.services.faiss_service.faiss_service.search",
        lambda db, project, query, top_k: mock_candidates,
    )

    response = client.post(
        f"/api/projects/{project_id}/context/retrieve",
        headers=headers_a,
        json={"query": "password hashing", "top_files": 3, "chunks_per_file": 2},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "password hashing"
    assert data["total_matching_files"] == 1
    assert data["total_candidate_chunks"] == 1
    assert data["files"][0]["file_path"] == "app/core/security.py"
    assert data["files"][0]["chunks"][0]["symbol_name"] == "hash_password"


def test_missing_faiss_index_handling(user_a):
    """An unindexed project returns a clean 400 error indicating index needs to be built."""
    user_a_id, _, headers_a = user_a
    unindexed_project_id = create_project(user_a_id, "Empty Unindexed Project")

    response = client.post(
        f"/api/projects/{unindexed_project_id}/context/retrieve",
        headers=headers_a,
        json={"query": "any query"},
    )

    # Clean error response as specified in Step 29
    assert response.status_code == 400
    detail = response.json().get("detail", "").lower()
    assert "index" in detail or "build" in detail or "not found" in detail


# ==============================================================================
# 7. RAG SERVICE INTEGRATION TEST
# ==============================================================================

def test_rag_service_uses_file_context(monkeypatch):
    """Verify that rag_service.ask() calls context_retriever and structures context docs."""
    from app.services.rag_service import rag_service
    from app.schemas.ai import AiHealthResponse, AiHealthOllamaInfo, AiHealthModelInfo

    chunk_item = make_search_result(
        chunk_id=1,
        file_path="app/auth.py",
        score=0.92,
        start_line=1,
        end_line=20,
        content="def login(): return 'ok'",
        symbol_name="login",
        symbol_type="function",
    )

    mock_context_result = ContextRetrievalResult(
        project_id=1,
        query="auth query",
        total_candidate_chunks=1,
        total_matching_files=1,
        files=[
            RetrievedFileItem(
                file_path="app/auth.py",
                file_name="auth.py",
                file_score=0.92,
                chunk_count=1,
                chunks=[
                    RetrievedChunkItem(
                        chunk_id=1,
                        score=0.92,
                        start_line=1,
                        end_line=20,
                        symbol_name="login",
                        symbol_type="function",
                        language="python",
                        content="def login(): return 'ok'",
                    )
                ],
            )
        ],
        selected_chunks=[chunk_item],
    )

    monkeypatch.setattr(
        "app.services.context_retriever.context_retriever.retrieve_context",
        lambda db, project, query, top_files, candidate_chunks, chunks_per_file, min_similarity: mock_context_result,
    )

    # Bypass indexing check for this unit test
    monkeypatch.setattr(
        rag_service,
        "check_project_indexing_status",
        lambda db, project: None,
    )

    mock_health = AiHealthResponse(
        ollama=AiHealthOllamaInfo(available=True),
        model=AiHealthModelInfo(name="gemma:2b", available=True),
    )
    monkeypatch.setattr(
        "app.services.ollama_service.ollama_service.check_health",
        lambda: mock_health,
    )

    from langchain_core.runnables import RunnableLambda
    monkeypatch.setattr(
        rag_service,
        "get_llm",
        lambda: RunnableLambda(lambda p: "Login is implemented in app/auth.py."),
    )

    db = next(get_db())
    try:
        mock_proj = Project(
            id=1,
            name="Mock Proj",
            original_filename="mock.zip",
            storage_path="mock",
            extracted_path="mock",
            file_count=1,
            lines_of_code=20,
            status="completed",
            user_id=1,
        )
        res = rag_service.ask(
            db=db,
            project=mock_proj,
            question="Where is login?",
            top_k=5,
        )

        assert res.answer == "Login is implemented in app/auth.py."
        assert len(res.sources) == 1
        assert res.sources[0].file_path == "app/auth.py"
        assert res.sources[0].start_line == 1
        assert res.sources[0].end_line == 20
    finally:
        db.close()
