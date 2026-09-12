import logging
import threading
from typing import List, Optional, Tuple
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.schemas.embedding import (
    ChunkEmbeddingFailure,
    ProjectEmbeddingResponse,
    ProjectEmbeddingStatusResponse,
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service responsible for Day 11 Embedding Generation:
    - Thread-safe lazy loading of Nomic Embed Text (nomic-ai/nomic-embed-text-v1.5).
    - CPU/GPU auto-detection and execution.
    - Safe formatting of code chunk embedding inputs with Nomic task prefixes.
    - Batch encoding with configurable batch size and L2 vector normalization.
    - Exact dimension detection (768) and validation.
    - Content-hash-based idempotency to skip unchanged chunks.
    - Persistent storage of vectors and statuses in PostgreSQL.
    """

    def __init__(self) -> None:
        self._model: Optional[SentenceTransformer] = None
        self._lock = threading.Lock()
        self._embedding_dimension: Optional[int] = None
        self._model_name: str = settings.EMBEDDING_MODEL
        self._batch_size: int = settings.EMBEDDING_BATCH_SIZE
        self._device: str = self._resolve_device()

    def _resolve_device(self) -> str:
        """
        Determines execution device (CPU or CUDA) based on hardware availability
        and settings (Phase 10).
        """
        config_device = getattr(settings, "EMBEDDING_DEVICE", "auto")
        if config_device and config_device.lower() != "auto":
            return config_device
        return "cuda" if torch.cuda.is_available() else "cpu"

    def get_model(self) -> SentenceTransformer:
        """
        Thread-safe lazy initialization of Nomic Embed Text model (Phase 6).
        Ensures the model is downloaded and loaded once at service-level,
        and re-used across all subsequent requests without redundant reloads.
        """
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is None:
                logger.info(
                    "Initializing Nomic Embed Text model '%s' on device '%s'...",
                    self._model_name,
                    self._device,
                )
                try:
                    model = SentenceTransformer(
                        self._model_name,
                        trust_remote_code=True,
                        device=self._device,
                    )
                    self._model = model

                    # Detect and cache actual embedding dimension (Phase 12)
                    try:
                        self._embedding_dimension = model.get_embedding_dimension()
                    except Exception:
                        try:
                            self._embedding_dimension = model.get_sentence_embedding_dimension()
                        except Exception:
                            # Fallback: run test embedding
                            test_emb = model.encode("test", normalize_embeddings=True)
                            self._embedding_dimension = len(test_emb)

                    logger.info(
                        "Nomic Embed Text model loaded successfully. Detected dimension: %s",
                        self._embedding_dimension,
                    )
                except Exception as e:
                    logger.error("Failed to load Nomic Embed Text model: %s", e, exc_info=True)
                    raise RuntimeError(f"Failed to initialize embedding model: {e}") from e

        return self._model

    @property
    def embedding_dimension(self) -> int:
        """
        Returns the detected embedding dimension for the active model.
        """
        if self._embedding_dimension is None:
            self.get_model()
        return self._embedding_dimension or 768

    @property
    def model_name(self) -> str:
        return self._model_name

    def format_chunk_input(self, chunk: CodeChunk) -> str:
        """
        Formats source code chunk content into Nomic Embed Text input (Phases 7 & 8).
        Adheres to Nomic's official prefix specification: 'search_document: <content>'.
        Includes safe project-relative file path and symbol name without leaking
        server filesystem paths, database credentials, or secret information.
        """
        # Relative file path and symbol (safe metadata only)
        header_parts = [f"File: {chunk.file_path}"]
        if chunk.symbol_name:
            sym_type = chunk.symbol_type or "symbol"
            header_parts.append(f"{sym_type.capitalize()}: {chunk.symbol_name}")

        header = " | ".join(header_parts)
        # Nomic task prefix for documents
        return f"search_document: {header}\n\n{chunk.content}"

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        """
        Generates L2-normalized vector embeddings for a batch of texts (Phases 9 & 11).
        Returns list of float vectors.
        """
        if not texts:
            return []

        model = self.get_model()
        bs = batch_size or self._batch_size

        try:
            vectors = model.encode(
                texts,
                batch_size=bs,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )

            # Convert numpy array to list of floats for JSON/PostgreSQL serialization
            if isinstance(vectors, np.ndarray):
                return vectors.tolist()
            return [list(map(float, v)) for v in vectors]

        except Exception as e:
            logger.error("Error during batch embedding generation: %s", e, exc_info=True)
            raise

    def format_query_input(self, query: str) -> str:
        """
        Formats user search query with Nomic task prefix: 'search_query: <text>' (Phase 16).
        """
        clean_query = (query or "").strip()
        return f"search_query: {clean_query}"

    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generates normalized vector embedding for a search query using the SAME
        Nomic Embed Text model used in Day 11 (Phases 5 & 16).
        """
        formatted = self.format_query_input(query)
        embeddings = self.generate_embeddings_batch([formatted], batch_size=1)
        return embeddings[0]

    def embed_project_chunks(
        self,
        db: Session,
        project: Project,
    ) -> ProjectEmbeddingResponse:
        """
        Executes Day 11 embedding generation pipeline for all chunks of a project:
        1. Retrieves indexed CodeChunks for project.
        2. Inspects content hashes: skips already-embedded unchanged chunks (Phases 17 & 18).
        3. Identifies chunks requiring embeddings.
        4. Generates embeddings in configurable batches (Phases 9 & 32).
        5. Validates dimension (Phase 12).
        6. Persists embeddings, hashes, dimensions, and status to PostgreSQL (Phases 13 & 16).
        7. Handles partial failures gracefully without losing successful chunks (Phase 22).
        """
        chunks_stmt = (
            select(CodeChunk)
            .where(CodeChunk.project_id == project.id)
            .order_by(CodeChunk.file_path, CodeChunk.chunk_index)
        )
        chunks = list(db.scalars(chunks_stmt).all())
        total_chunks = len(chunks)

        # Empty project handling (Phase 21)
        if total_chunks == 0:
            return ProjectEmbeddingResponse(
                project_id=project.id,
                project_name=project.name,
                status="completed",
                total_chunks=0,
                embedded_chunks=0,
                skipped_chunks=0,
                failed_chunks=0,
                embedding_dimension=self.embedding_dimension,
                model=self._model_name,
                failed_details=[],
            )

        # Separate chunks into those needing embeddings vs unchanged/skipped
        chunks_to_embed: List[CodeChunk] = []
        skipped_count = 0

        for chunk in chunks:
            # Idempotency check: embedding exists and hash has not changed (Phase 17 & 18)
            if (
                chunk.embedding is not None
                and chunk.embedded_hash == chunk.content_hash
                and chunk.embedding_status == "completed"
            ):
                skipped_count += 1
            else:
                chunks_to_embed.append(chunk)

        # If all chunks are already up-to-date
        if not chunks_to_embed:
            return ProjectEmbeddingResponse(
                project_id=project.id,
                project_name=project.name,
                status="completed",
                total_chunks=total_chunks,
                embedded_chunks=total_chunks - skipped_count,
                skipped_chunks=skipped_count,
                failed_chunks=0,
                embedding_dimension=self.embedding_dimension,
                model=self._model_name,
                failed_details=[],
            )

        # Ensure model is ready
        model = self.get_model()
        expected_dim = self.embedding_dimension

        failed_details: List[ChunkEmbeddingFailure] = []
        successfully_embedded_count = 0

        # Process chunks_to_embed in batches (Phases 9 & 32)
        batch_size = self._batch_size
        for i in range(0, len(chunks_to_embed), batch_size):
            batch = chunks_to_embed[i : i + batch_size]
            formatted_texts = [self.format_chunk_input(c) for c in batch]

            try:
                # Generate embeddings for batch
                embeddings = self.generate_embeddings_batch(formatted_texts, batch_size=batch_size)

                for chunk, vector in zip(batch, embeddings):
                    # Validate dimension (Phase 12)
                    if len(vector) != expected_dim:
                        chunk.embedding_status = "failed"
                        failed_details.append(
                            ChunkEmbeddingFailure(
                                chunk_id=chunk.chunk_id,
                                reason=f"Dimension mismatch: expected {expected_dim}, got {len(vector)}",
                            )
                        )
                        continue

                    # Persist embedding vector & update status (Phases 13, 14, 16, 17)
                    chunk.embedding = vector
                    chunk.embedding_status = "completed"
                    chunk.embedding_dimension = expected_dim
                    chunk.embedded_hash = chunk.content_hash
                    successfully_embedded_count += 1

                db.commit()

            except Exception as batch_err:
                logger.warning(
                    "Batch embedding failed for project %s (chunks %s..%s): %s. Falling back to individual processing.",
                    project.id,
                    i,
                    i + len(batch),
                    batch_err,
                )
                db.rollback()

                # Granular individual chunk retry for partial failure tolerance (Phase 22)
                for chunk, text in zip(batch, formatted_texts):
                    try:
                        single_emb = self.generate_embeddings_batch([text], batch_size=1)[0]
                        if len(single_emb) != expected_dim:
                            chunk.embedding_status = "failed"
                            failed_details.append(
                                ChunkEmbeddingFailure(
                                    chunk_id=chunk.chunk_id,
                                    reason=f"Dimension mismatch: expected {expected_dim}, got {len(single_emb)}",
                                )
                            )
                        else:
                            chunk.embedding = single_emb
                            chunk.embedding_status = "completed"
                            chunk.embedding_dimension = expected_dim
                            chunk.embedded_hash = chunk.content_hash
                            successfully_embedded_count += 1
                        db.commit()
                    except Exception as single_err:
                        db.rollback()
                        chunk.embedding_status = "failed"
                        failed_details.append(
                            ChunkEmbeddingFailure(
                                chunk_id=chunk.chunk_id,
                                reason=f"Embedding generation failed: {str(single_err)}",
                            )
                        )
                        try:
                            db.commit()
                        except Exception:
                            db.rollback()

        # Determine overall project embedding status
        if len(failed_details) == 0:
            final_status = "completed"
        elif successfully_embedded_count > 0 or skipped_count > 0:
            final_status = "partial_failure"
        else:
            final_status = "failed"

        return ProjectEmbeddingResponse(
            project_id=project.id,
            project_name=project.name,
            status=final_status,
            total_chunks=total_chunks,
            embedded_chunks=successfully_embedded_count,
            skipped_chunks=skipped_count,
            failed_chunks=len(failed_details),
            embedding_dimension=expected_dim,
            model=self._model_name,
            failed_details=failed_details,
        )

    def get_project_embedding_status(
        self,
        db: Session,
        project: Project,
    ) -> ProjectEmbeddingStatusResponse:
        """
        Retrieves embedding statistics and readiness status for a project (Phase 16).
        """
        chunks_stmt = select(CodeChunk).where(CodeChunk.project_id == project.id)
        chunks = list(db.scalars(chunks_stmt).all())
        total_chunks = len(chunks)

        if total_chunks == 0:
            return ProjectEmbeddingStatusResponse(
                project_id=project.id,
                status="not_generated",
                total_chunks=0,
                embedded_chunks=0,
                skipped_chunks=0,
                failed_chunks=0,
                embedding_dimension=self.embedding_dimension,
                model=self._model_name,
                last_embedded_at=None,
            )

        completed_count = sum(1 for c in chunks if c.embedding_status == "completed")
        failed_count = sum(1 for c in chunks if c.embedding_status == "failed")
        pending_count = total_chunks - completed_count - failed_count

        if completed_count == total_chunks:
            status_str = "ready"
        elif completed_count > 0:
            status_str = "partial_ready"
        elif failed_count > 0:
            status_str = "failed"
        else:
            status_str = "not_generated"

        last_updated = None
        if completed_count > 0:
            last_updated = max(c.updated_at for c in chunks if c.embedding_status == "completed")

        return ProjectEmbeddingStatusResponse(
            project_id=project.id,
            status=status_str,
            total_chunks=total_chunks,
            embedded_chunks=completed_count,
            skipped_chunks=pending_count,
            failed_chunks=failed_count,
            embedding_dimension=self.embedding_dimension,
            model=self._model_name,
            last_embedded_at=last_updated,
        )


# Global singleton instance
embedding_service = EmbeddingService()
