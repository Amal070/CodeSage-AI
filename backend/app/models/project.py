from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    programming_language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    framework: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_count: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    lines_of_code: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storage_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    extracted_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded", server_default="uploaded", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    files: Mapped[List["UploadedFile"]] = relationship(
        "UploadedFile", back_populates="project", cascade="all, delete-orphan"
    )
    chats: Mapped[List["ChatHistory"]] = relationship(
        "ChatHistory", back_populates="project", cascade="all, delete-orphan"
    )
    code_chunks: Mapped[List["CodeChunk"]] = relationship(
        "CodeChunk", back_populates="project", cascade="all, delete-orphan"
    )
