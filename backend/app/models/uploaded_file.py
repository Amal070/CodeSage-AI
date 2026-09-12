from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    size: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="files")
