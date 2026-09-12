import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.services.embedding_service import embedding_service
from app.schemas.semantic_search import (
    SearchResultItem,
    SearchResultMetadata,
    VectorIndexBuildResponse,
    VectorIndexStatusResponse,
)

logger = logging.getLogger(__name__)


class FaissService:
    """
    Service responsible for Day 12 FAISS Semantic Code Retrieval:
    - Building and persisting project-isolated FAISS vector indexes (IndexFlatIP).
    - Mapping FAISS vector IDs to deterministic CodeChunk IDs.
    - Validating index consistency, file existence, and vector dimensions.
    - Executing top-k semantic code search using Nomic Embed Text query embeddings.
    - Preserving strict project boundary tenancy and security.
    """

    def __init__(self, indexes_base_dir: Optional[str] = None) -> None:
        self.indexes_base_dir = Path(indexes_base_dir or settings.INDEXES_DIR)
        self.indexes_base_dir.mkdir(parents=True, exist_ok=True)

    def get_project_index_dir(self, project_id: int) -> Path:
        """
        Returns the isolated filesystem directory for a project's FAISS index (Phases 8 & 9).
        Never exposes absolute filesystem paths to the API or frontend.
        """
        proj_dir = self.indexes_base_dir / f"project_{project_id}"
        proj_dir.mkdir(parents=True, exist_ok=True)
        return proj_dir

    def get_index_file_paths(self, project_id: int) -> Tuple[Path, Path]:
        """
        Returns (index_path, mapping_path) for a project.
        """
        proj_dir = self.get_project_index_dir(project_id)
        return proj_dir / "index.faiss", proj_dir / "mapping.json"

    def build_project_index(
        self,
        db: Session,
        project: Project,
    ) -> VectorIndexBuildResponse:
        """
        Constructs and persists a FAISS IndexFlatIP vector index from Day 11 code chunk embeddings (Phases 5, 6, 7, 10).
        1. Retrieves valid embedded CodeChunks from PostgreSQL.
        2. Validates vector dimensions against model configuration.
        3. Initializes an exact faiss.IndexFlatIP index (inner product = cosine similarity on normalized vectors).
        4. Adds embedding vectors in batch.
        5. Persists FAISS binary index and JSON ID-to-chunk mapping file.
        """
        # Retrieve chunks for this project only (Phase 23)
        stmt = (
            select(CodeChunk)
            .where(
                CodeChunk.project_id == project.id,
                CodeChunk.embedding_status == "completed",
            )
            .order_by(CodeChunk.file_path, CodeChunk.chunk_index)
        )
        chunks = list(db.scalars(stmt).all())

        # Filter chunks that actually have non-null embedding vectors
        embedded_chunks = [c for c in chunks if c.embedding is not None and len(c.embedding) > 0]
        total_vectors = len(embedded_chunks)

        index_path, mapping_path = self.get_index_file_paths(project.id)

        # Empty project handling (Phase 13)
        if total_vectors == 0:
            # If previous index exists, clean it up
            if index_path.exists():
                index_path.unlink(missing_ok=True)
            if mapping_path.exists():
                mapping_path.unlink(missing_ok=True)

            return VectorIndexBuildResponse(
                project_id=project.id,
                status="empty",
                indexed_vectors=0,
                embedding_dimension=embedding_service.embedding_dimension,
                index_type="IndexFlatIP",
                metric="cosine_similarity",
            )

        # Determine and validate expected dimension (Phase 6)
        expected_dim = embedding_service.embedding_dimension

        # Build numpy array of vectors
        vectors_list: List[List[float]] = []
        id_to_chunk: Dict[str, str] = {}

        for idx, chunk in enumerate(embedded_chunks):
            vec = chunk.embedding
            if len(vec) != expected_dim:
                raise ValueError(
                    f"Chunk {chunk.chunk_id} has invalid embedding dimension {len(vec)}; expected {expected_dim}."
                )
            vectors_list.append(vec)
            id_to_chunk[str(idx)] = chunk.chunk_id

        vectors_np = np.array(vectors_list, dtype=np.float32)

        # Build exact inner-product index (Phase 5)
        # Cosine similarity is mathematically exact because Day 11 vectors are L2-normalized
        index = faiss.IndexFlatIP(expected_dim)
        index.add(vectors_np)

        # Persist index binary (Phase 9)
        faiss.write_index(index, str(index_path))

        # Persist mapping metadata (Phase 7)
        mapping_data = {
            "project_id": project.id,
            "vector_count": total_vectors,
            "dimension": expected_dim,
            "index_type": "IndexFlatIP",
            "metric": "cosine_similarity",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "id_to_chunk": id_to_chunk,
        }
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(mapping_data, f, indent=2)

        logger.info(
            "Built FAISS vector index for project %s: %s vectors, dim=%s",
            project.id,
            total_vectors,
            expected_dim,
        )

        return VectorIndexBuildResponse(
            project_id=project.id,
            status="completed",
            indexed_vectors=total_vectors,
            embedding_dimension=expected_dim,
            index_type="IndexFlatIP",
            metric="cosine_similarity",
        )

    def load_project_index(
        self,
        project_id: int,
    ) -> Tuple[faiss.Index, Dict[str, str]]:
        """
        Loads a project's persisted FAISS index and mapping metadata (Phase 15).
        Validates index existence, dimension, and vector count consistency.
        """
        index_path, mapping_path = self.get_index_file_paths(project_id)

        if not index_path.exists() or not mapping_path.exists():
            raise FileNotFoundError(
                "Vector index not found. Build the project vector index before searching."
            )

        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping_data = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to read vector index mapping: {e}") from e

        try:
            index = faiss.read_index(str(index_path))
        except Exception as e:
            raise ValueError(f"Failed to load FAISS binary index: {e}") from e

        id_to_chunk = mapping_data.get("id_to_chunk", {})

        # Consistency verification (Phase 15)
        if index.ntotal != len(id_to_chunk):
            raise ValueError(
                f"Index corruption detected: FAISS vectors ({index.ntotal}) does not match mapping count ({len(id_to_chunk)}). Please rebuild the vector index."
            )

        return index, id_to_chunk

    def get_project_index_status(
        self,
        project_id: int,
        total_embedded_chunks: int,
    ) -> VectorIndexStatusResponse:
        """
        Retrieves index status, vector count, and freshness for a project (Phase 35).
        """
        index_path, mapping_path = self.get_index_file_paths(project_id)

        if not index_path.exists() or not mapping_path.exists():
            return VectorIndexStatusResponse(
                project_id=project_id,
                status="not_built",
                indexed_vectors=0,
                embedding_dimension=None,
                index_type=None,
                metric=None,
                last_indexed_at=None,
            )

        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping_data = json.load(f)

            vector_count = mapping_data.get("vector_count", 0)
            dimension = mapping_data.get("dimension", 768)
            index_type = mapping_data.get("index_type", "IndexFlatIP")
            metric = mapping_data.get("metric", "cosine_similarity")
            created_at_str = mapping_data.get("created_at")
            created_at = datetime.fromisoformat(created_at_str) if created_at_str else None

            # Check if index has fewer vectors than current embedded chunks in DB
            status_str = "ready"
            if total_embedded_chunks > vector_count:
                status_str = "stale"
            elif vector_count == 0:
                status_str = "empty"

            return VectorIndexStatusResponse(
                project_id=project_id,
                status=status_str,
                indexed_vectors=vector_count,
                embedding_dimension=dimension,
                index_type=index_type,
                metric=metric,
                last_indexed_at=created_at,
            )
        except Exception:
            return VectorIndexStatusResponse(
                project_id=project_id,
                status="corrupted",
                indexed_vectors=0,
                embedding_dimension=None,
                index_type=None,
                metric=None,
                last_indexed_at=None,
            )

    def search(
        self,
        db: Session,
        project: Project,
        query: str,
        top_k: int = 5,
    ) -> List[SearchResultItem]:
        """
        Executes semantic code search for a natural-language query (Phases 16, 17, 19, 20):
        1. Validates query and top_k bounds.
        2. Generates normalized query embedding vector via Nomic Embed Text (search_query: prefix).
        3. Loads project's FAISS index and resolves top-k matching vector IDs.
        4. Retrieves corresponding CodeChunk records from PostgreSQL, strictly scoped to project.id.
        5. Formats results with file metadata, symbols, line numbers, and cosine similarity scores.
        """
        clean_query = (query or "").strip()
        if not clean_query:
            raise ValueError("Search query cannot be empty.")

        k = max(1, min(top_k, getattr(settings, "MAX_SEARCH_TOP_K", 20)))

        # Load project index (verifies index existence and consistency)
        index, id_to_chunk = self.load_project_index(project.id)

        if index.ntotal == 0 or len(id_to_chunk) == 0:
            return []

        # 1. Generate query embedding using the SAME Nomic Embed Text model (Phase 16)
        query_vector = embedding_service.generate_query_embedding(clean_query)
        query_np = np.array([query_vector], dtype=np.float32)

        # 2. Search FAISS index (Phase 19)
        search_k = min(k, index.ntotal)
        scores, indices = index.search(query_np, search_k)

        matched_scores = scores[0]
        matched_indices = indices[0]

        # 3. Resolve matched vector IDs to chunk_ids
        target_chunk_ids: List[str] = []
        score_map: Dict[str, float] = {}

        for faiss_idx, score in zip(matched_indices, matched_scores):
            if faiss_idx < 0:
                continue
            chunk_id = id_to_chunk.get(str(faiss_idx))
            if chunk_id:
                target_chunk_ids.append(chunk_id)
                score_map[chunk_id] = float(score)

        if not target_chunk_ids:
            return []

        # 4. Fetch CodeChunk records strictly scoped to project.id (Phases 23 & 24)
        chunks_stmt = select(CodeChunk).where(
            CodeChunk.project_id == project.id,
            CodeChunk.chunk_id.in_(target_chunk_ids),
        )
        chunk_records = {c.chunk_id: c for c in db.scalars(chunks_stmt).all()}

        # 5. Format results in descending order of similarity score
        results: List[SearchResultItem] = []
        for chunk_id in target_chunk_ids:
            chunk = chunk_records.get(chunk_id)
            if not chunk:
                continue

            score = score_map.get(chunk_id, 0.0)
            # Bound cosine similarity score between 0.0 and 1.0 for readability
            bounded_score = round(max(0.0, min(1.0, score)), 4)

            results.append(
                SearchResultItem(
                    chunk_id=chunk.chunk_id,
                    score=bounded_score,
                    content=chunk.content,
                    metadata=SearchResultMetadata(
                        file_path=chunk.file_path,
                        file_name=chunk.file_name,
                        file_extension=chunk.file_extension,
                        language=chunk.language,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        symbol_name=chunk.symbol_name,
                        symbol_type=chunk.symbol_type,
                        source_type=chunk.source_type,
                    ),
                )
            )

        return results


# Global singleton instance
faiss_service = FaissService()
