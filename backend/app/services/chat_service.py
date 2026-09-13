import logging
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func

from app.core.config import settings
from app.models.chat_history import ChatHistory
from app.schemas.chat import ChatResponse, ChatHistoryItem
from app.services.project_service import get_project_by_id
from app.services.rag_service import rag_service
from app.services.prompts import build_contextual_retrieval_query

logger = logging.getLogger(__name__)


class ChatService:
    """
    Day 15 & Day 16 AI Chat Service:
    - Coordinates conversation requests between authenticated users and their project codebases.
    - Reuses the existing Day 14 LangChain + RAG pipeline (rag_service.ask).
    - Enforces strict tenant isolation, project ownership, and conversation isolation.
    - Manages structured, project-aware conversation sessions with conversation_id.
    - Contextually enriches retrieval queries for follow-up questions.
    - Passes bounded conversation history into the structured prompt.
    - Persists conversation exchanges in the ChatHistory database table.
    """

    def send_message(
        self,
        db: Session,
        project_id: int,
        user_id: int,
        question: str,
        top_k: int = 5,
        conversation_id: Optional[int] = None,
    ) -> ChatResponse:
        """
        Processes a chat question against the project codebase:
        1. Verifies that the requested project exists and belongs to the authenticated user.
        2. Validates and resolves the conversation session (conversation_id), ensuring strict isolation.
        3. Retrieves bounded recent conversation history for this conversation.
        4. Detects referential follow-ups and enriches FAISS semantic retrieval query if needed.
        5. Executes Day 14/16 RAG pipeline with structured prompt and conversation context.
        6. Persists the user question and AI answer in PostgreSQL chat_history with conversation_id.
        7. Returns structured ChatResponse with sources, conversation_id, and history ID.
        """
        # 1. Verify project ownership and tenant isolation
        project = get_project_by_id(db, project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )

        # 2. Resolve & validate conversation_id
        resolved_conv_id: int
        if conversation_id is not None:
            # Check for cross-user or cross-project conversation leakage
            foreign_conv = db.scalar(
                select(ChatHistory.id).where(
                    ChatHistory.conversation_id == conversation_id,
                    (ChatHistory.user_id != user_id) | (ChatHistory.project_id != project_id),
                ).limit(1)
            )
            if foreign_conv is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Conversation belongs to another user or project.",
                )
            resolved_conv_id = conversation_id
        else:
            # Generate new unique conversation session ID across sessions to prevent collisions
            max_conv = db.scalar(
                select(func.max(ChatHistory.conversation_id))
            ) or 0
            resolved_conv_id = max_conv + 1

        # 3. Retrieve bounded conversation history for this conversation
        history_limit = getattr(settings, "CHAT_HISTORY_LIMIT", 10)
        recent_records = db.scalars(
            select(ChatHistory)
            .where(
                ChatHistory.project_id == project_id,
                ChatHistory.user_id == user_id,
                ChatHistory.conversation_id == resolved_conv_id,
            )
            .order_by(ChatHistory.created_at.desc())
            .limit(history_limit)
        ).all()

        # Reverse to chronological order (oldest first)
        recent_records = list(reversed(recent_records))

        # Build list of turn dicts for prompt formatting and contextual query enrichment
        conv_messages: List[dict] = []
        for rec in recent_records:
            conv_messages.append({"role": "user", "content": rec.message})
            conv_messages.append({"role": "assistant", "content": rec.response})

        # 4. Contextual retrieval query enrichment for follow-up questions
        enriched_query = build_contextual_retrieval_query(
            question=question,
            conversation_history=conv_messages,
        )

        # 5. Execute Day 14/16 RAG pipeline (FAISS retrieval + Gemma via LangChain)
        rag_response = rag_service.ask(
            db=db,
            project=project,
            question=question,
            top_k=top_k,
            conversation_history=conv_messages,
            retrieval_query=enriched_query,
        )

        # 6. Persist conversation in ChatHistory table
        chat_entry = ChatHistory(
            user_id=user_id,
            project_id=project.id,
            conversation_id=resolved_conv_id,
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
            return ChatResponse(
                project_id=project.id,
                conversation_id=resolved_conv_id,
                question=rag_response.question,
                answer=rag_response.answer,
                sources=rag_response.sources,
                chat_id=None,
                created_at=None,
                model=rag_response.model,
            )

        # 7. Return structured ChatResponse
        return ChatResponse(
            project_id=project.id,
            conversation_id=resolved_conv_id,
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
        conversation_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[ChatHistoryItem]:
        """
        Retrieves stored chat history items for a specific project and authenticated user.
        Optionally filtered by conversation_id. Items are returned chronologically.
        """
        project = get_project_by_id(db, project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )

        query = select(ChatHistory).where(
            ChatHistory.project_id == project_id,
            ChatHistory.user_id == user_id,
        )

        if conversation_id is not None:
            query = query.where(ChatHistory.conversation_id == conversation_id)

        query = query.order_by(ChatHistory.created_at.asc()).limit(limit)
        records = db.scalars(query).all()
        return [ChatHistoryItem.model_validate(r) for r in records]

    def clear_project_chat_history(
        self,
        db: Session,
        project_id: int,
        user_id: int,
        conversation_id: Optional[int] = None,
    ) -> dict:
        """
        Clears stored chat history for a specific project and user.
        Optionally scoped to a specific conversation_id.
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

        if conversation_id is not None:
            stmt = stmt.where(ChatHistory.conversation_id == conversation_id)

        result = db.execute(stmt)
        db.commit()

        deleted_count = result.rowcount if hasattr(result, "rowcount") else 0
        return {
            "status": "cleared",
            "project_id": project_id,
            "conversation_id": conversation_id,
            "deleted_count": deleted_count,
        }


# Global singleton instance
chat_service = ChatService()
