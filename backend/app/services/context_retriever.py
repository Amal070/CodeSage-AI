"""
CodeSage AI — Day 17 Context Retrieval Service

Implements file-level relevance scoring and aggregation over Day 12 FAISS semantic search:
1. Retrieves a broad pool of candidate code chunks via FAISS IndexFlatIP (cosine similarity).
2. Groups candidate chunks by project-relative file path.
3. Computes deterministic, explainable file relevance scores combining peak chunk similarity,
   top-N chunk average, and bounded supporting evidence bonus.
4. Restricts duplicate/near-duplicate chunk influence.
5. Selects top matching files and their strongest relevant code chunks for RAG.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project
from app.schemas.context_retrieval import (
    RetrievedChunkItem,
    RetrievedFileItem,
    ContextRetrievalResponse,
)
from app.schemas.semantic_search import SearchResultItem
from app.services.faiss_service import faiss_service

logger = logging.getLogger(__name__)


@dataclass
class ContextRetrievalResult:
    """
    Internal container holding both structured file items and flattened top chunks for RAG.
    """
    project_id: int
    query: str
    total_candidate_chunks: int
    total_matching_files: int
    files: List[RetrievedFileItem]
    selected_chunks: List[SearchResultItem]


class ContextRetriever:
    """
    Day 17 Context Retrieval Layer:
    - Coordinates file-level candidate retrieval and relevance ranking.
    - Reuses Day 12 FAISS semantic search and Day 11 Nomic Embed Text normalized embeddings.
    - Preserves strict project-scoped multi-tenant isolation.
    - Prevents single-file dominance from repeated similar chunks.
    """

    def calculate_file_relevance_score(
        self,
        chunk_scores: List[float],
        strong_threshold: float = 0.60,
    ) -> float:
        """
        Calculates an explainable, deterministic file relevance score (0.0 to 1.0).
        
        Formula:
            file_score = 0.65 * best_score + 0.25 * top_3_mean + supporting_bonus
            
        Components:
        1. Peak Match (0.65 weight): The highest chunk similarity indicates the file's peak relevance.
        2. Coherence / Breadth (0.25 weight): Mean similarity of top 3 chunks indicates broad topical relevance.
        3. Supporting Evidence Bonus (up to 0.10 max): Bounded bonus for distinct strong chunks (>= 0.60).
           Prevents a file with 10 duplicate/near-duplicate chunks from dominating a file with higher semantic peak.
        """
        if not chunk_scores:
            return 0.0

        sorted_scores = sorted(chunk_scores, reverse=True)
        best_score = sorted_scores[0]

        top_n = sorted_scores[:3]
        top_n_mean = sum(top_n) / len(top_n)

        # Supporting chunks bonus: +0.03 for each additional strong chunk beyond the first, capped at +0.10
        strong_count = sum(1 for s in sorted_scores if s >= strong_threshold)
        supporting_bonus = min(0.10, max(0.0, (strong_count - 1) * 0.03))

        raw_score = (0.65 * best_score) + (0.25 * top_n_mean) + supporting_bonus
        return round(max(0.0, min(1.0, raw_score)), 4)

    def retrieve_context(
        self,
        db: Session,
        project: Union[Project, int],
        query: str,
        top_files: Optional[int] = None,
        candidate_chunks: Optional[int] = None,
        chunks_per_file: Optional[int] = None,
        min_similarity: Optional[float] = None,
    ) -> ContextRetrievalResult:
        """
        Executes file-level context retrieval for a user question:
        1. Queries FAISS for candidate chunks (default 30).
        2. Filters noise below min_similarity threshold (default 0.20).
        3. Groups chunks by project-relative file_path.
        4. Calculates file relevance score and ranks files.
        5. Selects top matching files (default 5, max 10).
        6. Extracts top chunks per file (default 3) for RAG context.
        """
        if isinstance(project, int):
            proj_obj = db.query(Project).filter(Project.id == project).first()
            if not proj_obj:
                proj_obj = Project(id=project, name=f"Project-{project}")
            project = proj_obj

        clean_query = (query or "").strip()
        if not clean_query:
            return ContextRetrievalResult(
                project_id=project.id,
                query="",
                total_candidate_chunks=0,
                total_matching_files=0,
                files=[],
                selected_chunks=[],
            )

        # Resolve configuration boundaries
        c_chunks = candidate_chunks or getattr(settings, "RETRIEVAL_CANDIDATE_CHUNKS", 30)
        c_chunks = max(5, min(c_chunks, 50))

        t_files = top_files or getattr(settings, "RETRIEVAL_TOP_FILES", 5)
        max_files = getattr(settings, "RETRIEVAL_MAX_TOP_FILES", 10)
        t_files = max(1, min(t_files, max_files))

        cp_file = chunks_per_file or getattr(settings, "RETRIEVAL_CHUNKS_PER_FILE", 3)
        cp_file = max(1, min(cp_file, 5))

        threshold = min_similarity if min_similarity is not None else getattr(
            settings, "RETRIEVAL_MIN_SIMILARITY_THRESHOLD", 0.20
        )

        # 1. Retrieve broad candidate chunks from Day 12 FAISS index
        raw_candidates = faiss_service.search(
            db=db,
            project=project,
            query=clean_query,
            top_k=c_chunks,
        )

        if not raw_candidates:
            return ContextRetrievalResult(
                project_id=project.id,
                query=clean_query,
                total_candidate_chunks=0,
                total_matching_files=0,
                files=[],
                selected_chunks=[],
            )

        # 2. Filter noise below threshold
        candidates = [c for c in raw_candidates if c.score >= threshold]
        if not candidates:
            logger.info(
                "All %d candidate chunks for project %d fell below similarity threshold %.2f",
                len(raw_candidates),
                project.id,
                threshold,
            )
            return ContextRetrievalResult(
                project_id=project.id,
                query=clean_query,
                total_candidate_chunks=len(raw_candidates),
                total_matching_files=0,
                files=[],
                selected_chunks=[],
            )

        # 3. Group candidate chunks by project-relative file_path
        file_chunks_map: Dict[str, List[SearchResultItem]] = {}
        for chunk in candidates:
            f_path = chunk.metadata.file_path or "unknown"
            file_chunks_map.setdefault(f_path, []).append(chunk)

        # 4. Score and rank each file
        ranked_files_data = []
        for f_path, chunks in file_chunks_map.items():
            # Sort chunks within file in descending order of similarity
            chunks_sorted = sorted(chunks, key=lambda c: c.score, reverse=True)
            scores = [c.score for c in chunks_sorted]
            file_score = self.calculate_file_relevance_score(scores)

            f_name = chunks_sorted[0].metadata.file_name or f_path.split("/")[-1]
            ranked_files_data.append({
                "file_path": f_path,
                "file_name": f_name,
                "file_score": file_score,
                "chunks": chunks_sorted,
            })

        # Sort files descending by file_score, breaking ties by peak chunk score
        ranked_files_data.sort(
            key=lambda item: (item["file_score"], item["chunks"][0].score),
            reverse=True,
        )

        # 5. Select top files up to t_files
        top_ranked_files = ranked_files_data[:t_files]

        # 6. Extract top chunks per file and format schema items
        retrieved_file_items: List[RetrievedFileItem] = []
        selected_rag_chunks: List[SearchResultItem] = []

        for item in top_ranked_files:
            file_selected_chunks = item["chunks"][:cp_file]
            chunk_items: List[RetrievedChunkItem] = []

            for c in file_selected_chunks:
                meta = c.metadata
                chunk_items.append(
                    RetrievedChunkItem(
                        chunk_id=c.chunk_id,
                        score=c.score,
                        start_line=meta.start_line,
                        end_line=meta.end_line,
                        symbol_name=meta.symbol_name,
                        symbol_type=meta.symbol_type,
                        language=meta.language,
                        content=c.content,
                    )
                )
                selected_rag_chunks.append(c)

            retrieved_file_items.append(
                RetrievedFileItem(
                    file_path=item["file_path"],
                    file_name=item["file_name"],
                    file_score=item["file_score"],
                    chunk_count=len(item["chunks"]),
                    chunks=chunk_items,
                )
            )

        logger.info(
            "ContextRetriever: Project %d query '%s' -> %d candidates -> %d files -> top %d files selected (%d chunks)",
            project.id,
            clean_query[:50],
            len(raw_candidates),
            len(ranked_files_data),
            len(retrieved_file_items),
            len(selected_rag_chunks),
        )

        return ContextRetrievalResult(
            project_id=project.id,
            query=clean_query,
            total_candidate_chunks=len(raw_candidates),
            total_matching_files=len(ranked_files_data),
            files=retrieved_file_items,
            selected_chunks=selected_rag_chunks,
        )


# Global singleton instance
context_retriever = ContextRetriever()
