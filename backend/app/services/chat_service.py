import logging
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.models.chat_history import ChatHistory
from app.schemas.chat import ChatResponse, ChatHistoryItem
from app.services.project_service import get_project_by_id
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)


class ChatService:
    """
    Day 15 AI Chat Service:
    - Coordinates conversation requests between authenticated users and their project codebases.
    - Reuses the existing Day 14 LangChain + RAG pipeline (rag_service.ask).
    - Enforces strict tenant isolation and project ownership checks.
    - Persists conversation exchanges in the ChatHistory database table.
    - Manages retrieval and clearing of project chat history.
    """

    def send_message(
        self,
        db: Session,
        project_id: int,
        user_id: int,
        question: str,
        top_k: int = 5,
    ) -> ChatResponse:
        """
        Processes a chat question against the project codebase:
        1. Verifies that the requested project exists and belongs to the authenticated user.
        2. Executes the existing Day 14 RAG pipeline (FAISS retrieval + Gemma via LangChain).
        3. Persists the user question and AI answer in PostgreSQL chat_history.
        4. Returns structured ChatResponse with sources and history ID.
        """
        # Verify project ownership and tenant isolation
        project = get_project_by_id(db, project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )

        # Execute existing Day 14 RAG pipeline
        rag_response = rag_service.ask(
            db=db,
            project=project,
            question=question,
            top_k=top_k,
        )

        # Persist conversation in ChatHistory table
        chat_entry = ChatHistory(
            user_id=user_id,
            project_id=project.id,
            message=rag_response.question,
            response=rag_response.answer,
        )
        try:
            db.add(chat_entry)
            db.commit()
            db.refresh(chat_entry)
        except Exception as e:
            db.rollback()
            logger.error("Failed to save chat history record for project %d: %s", project_id, e)
            # We don't fail the response if saving to chat history encounters an error,
            # but we log it and continue with chat_id as None.
            return ChatResponse(
                project_id=project.id,
                question=rag_response.question,
                answer=rag_response.answer,
                sources=rag_response.sources,
                chat_id=None,
                created_at=None,
                model=rag_response.model,
            )

        return ChatResponse(
            project_id=project.id,
            question=rag_response.question,
            answer=rag_response.answer,
            sources=rag_response.sources,
            chat_id=chat_entry.id,
            created_at=chat_entry.created_at,
            model=rag_response.model,
        )

    def get_project_chat_history(
        self,
        db: Session,
        project_id: int,
        user_id: int,
        limit: int = 100,
    ) -> List[ChatHistoryItem]:
        """
        Retrieves stored chat history items for a specific project and authenticated user.
        Items are returned chronologically (oldest first).
        """
        project = get_project_by_id(db, project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )

        query = (
            select(ChatHistory)
            .where(
                ChatHistory.project_id == project_id,
                ChatHistory.user_id == user_id,
            )
            .order_by(ChatHistory.created_at.asc())
            .limit(limit)
        )
        records = db.scalars(query).all()
        return [ChatHistoryItem.model_validate(r) for r in records]

    def clear_project_chat_history(
        self,
        db: Session,
        project_id: int,
        user_id: int,
    ) -> dict:
        """
        Clears all stored chat history for a specific project and user.
        """
        project = get_project_by_id(db, project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )

        stmt = delete(ChatHistory).where(
            ChatHistory.project_id == project_id,
            ChatHistory.user_id == user_id,
        )
        result = db.execute(stmt)
        db.commit()

        deleted_count = result.rowcount if hasattr(result, "rowcount") else 0
        return {
            "status": "cleared",
            "project_id": project_id,
            "deleted_count": deleted_count,
        }


# Global singleton instance
chat_service = ChatService()
