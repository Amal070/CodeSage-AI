from datetime import datetime
from typing import Optional, List
from sqlalchemy import ForeignKey, String, Text, Integer, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CodeChunk(Base):
    """
    Represents an indexed code chunk extracted from a project source file.
    Stores chunk content, structural metadata, symbol information, line ranges,
    deterministic hashes for semantic indexing, and Day 11 vector embeddings.
    """
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="code", server_default="code")
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    symbol_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parent_symbol: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Day 11 Embedding fields
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    embedding_status: Mapped[str] = mapped_column(
        String(50), default="pending", server_default="pending", nullable=False
    )
    embedding_dimension: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedded_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="code_chunks")
