import logging
from typing import List, Tuple, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.services.faiss_service import faiss_service
from app.services.ollama_service import ollama_service
from app.services.context_retriever import context_retriever
from app.services.prompts import (
    CODESAGE_CHAT_PROMPT_TEMPLATE,
    SYSTEM_INSTRUCTIONS,
    RESPONSE_REQUIREMENTS,
    format_conversation_history,
)
from app.schemas.rag import RagRequest, RagResponse, RagSourceItem
from app.schemas.semantic_search import SearchResultItem

logger = logging.getLogger(__name__)


class RagService:
    """
    Service responsible for Day 14 LangChain + RAG Pipeline & Day 16 Grounded Responses:
    - Coordinates query validation, semantic retrieval, and context construction.
    - Reuses Day 12 FAISS semantic search and Day 11 Nomic Embed Text query embeddings.
    - Converts retrieved CodeChunks into LangChain Document objects with full metadata preservation.
    - Enforces context size limits and safe chunk truncation.
    - Reusable LangChain LCEL chain with ChatOllama and Gemma 2B.
    - Enforces strict project isolation, preventing cross-project context leaks.
    - Production-grade error handling for offline Ollama, missing models, and unindexed projects.
    - Centralized Day 16 structured prompt with prompt injection defenses and conversation history.
    """

    def __init__(self) -> None:
        self.prompt_template = PromptTemplate.from_template(CODESAGE_CHAT_PROMPT_TEMPLATE)
        self.output_parser = StrOutputParser()

    def get_llm(self) -> ChatOllama:
        """
        Initializes LangChain ChatOllama wrapper using centralized configuration (Phases 19, 20).
        """
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.1,  # Low temperature for deterministic, grounded answers
        )

    def validate_request(self, question: str, top_k: int) -> Tuple[str, int]:
        """
        Validates question content and top_k bounds (Phase 18).
        """
        clean_question = (question or "").strip()
        if not clean_question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty or whitespace only.",
            )

        max_len = getattr(settings, "MAX_RAG_QUESTION_LENGTH", 5000)
        if len(clean_question) > max_len:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question exceeds maximum allowed length of {max_len} characters.",
            )

        min_k = 1
        max_k = getattr(settings, "MAX_RAG_TOP_K", 10)
        if top_k < min_k or top_k > max_k:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"top_k must be an integer between {min_k} and {max_k}.",
            )

        return clean_question, top_k

    def check_project_indexing_status(self, db: Session, project: Project) -> None:
        """
        Verifies project indexing readiness (Phase 34, 36).
        Raises HTTPException if prerequisites are not met.
        """
        # Count indexed code chunks in DB
        total_chunks = db.scalar(
            select(func.count()).select_from(CodeChunk).where(CodeChunk.project_id == project.id)
        ) or 0

        if total_chunks == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No indexed project context is available. Please index code first.",
            )

        # Check FAISS index files existence
        index_path, mapping_path = faiss_service.get_index_file_paths(project.id)
        if not index_path.exists() or not mapping_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete code indexing, embedding generation, and vector indexing before using CodeSage AI.",
            )

    def convert_chunks_to_documents(
        self,
        project_id: int,
        search_results: List[SearchResultItem],
    ) -> List[Document]:
        """
        Converts retrieved CodeSage chunks into LangChain Document objects (Phase 10).
        Preserves original code and full metadata.
        """
        documents: List[Document] = []
        for item in search_results:
            doc = Document(
                page_content=item.content,
                metadata={
                    "project_id": project_id,
                    "chunk_id": item.chunk_id,
                    "file_path": item.metadata.file_path,
                    "file_name": item.metadata.file_name,
                    "language": item.metadata.language,
                    "start_line": item.metadata.start_line,
                    "end_line": item.metadata.end_line,
                    "symbol_name": item.metadata.symbol_name,
                    "symbol_type": item.metadata.symbol_type,
                    "score": float(item.score),
                },
            )
            documents.append(doc)
        return documents

    def build_context(
        self,
        documents: List[Document],
        max_characters: int = 12000,
    ) -> Tuple[str, List[Document]]:
        """
        Constructs clean context from retrieved code chunks with source headers (Phases 11, 12).
        Enforces maximum context character size and safe chunk boundaries.
        Returns (context_text, included_documents).
        """
        context_parts: List[str] = []
        included_docs: List[Document] = []
        current_len = 0

        for i, doc in enumerate(documents, start=1):
            meta = doc.metadata
            file_path = meta.get("file_path", "unknown")
            start_line = meta.get("start_line", 1)
            end_line = meta.get("end_line", 1)
            symbol_name = meta.get("symbol_name")
            symbol_type = meta.get("symbol_type")

            symbol_header = ""
            if symbol_name:
                type_str = f" ({symbol_type})" if symbol_type else ""
                symbol_header = f"Symbol: {symbol_name}{type_str}\n"

            header = f"[Source {i}]\nFile: {file_path}\nLines: {start_line}-{end_line}\n{symbol_header}"
            code_content = doc.page_content.strip()

            # Bounded per-chunk size: max 3000 chars per chunk to prevent a single huge chunk dominating
            if len(code_content) > 3000:
                code_content = code_content[:3000] + "\n... [content truncated for context size]"

            block = f"{header}\n{code_content}\n"
            block_len = len(block)

            # Check total context budget
            if current_len + block_len > max_characters:
                # If we have at least one document, stop adding lower-priority documents
                if included_docs:
                    logger.info("Context size limit reached at %d characters. Truncating remaining chunks.", current_len)
                    break
                else:
                    # If even the first document exceeds budget, truncate it safely
                    allowed = max(500, max_characters - len(header) - 100)
                    truncated_code = code_content[:allowed] + "\n... [truncated]"
                    block = f"{header}\n{truncated_code}\n"
                    context_parts.append(block)
                    included_docs.append(doc)
                    break

            context_parts.append(block)
            included_docs.append(doc)
            current_len += block_len

        separator = "\n" + "=" * 50 + "\n\n"
        full_context = separator.join(context_parts)
        return full_context, included_docs

    def ask(
        self,
        db: Session,
        project: Project,
        question: str,
        top_k: int = 5,
        conversation_history: Optional[List[dict]] = None,
        retrieval_query: Optional[str] = None,
    ) -> RagResponse:
        """
        Main Day 14 & Day 16 RAG Pipeline execution:
        1. Validate request and parameters.
        2. Check project indexing readiness.
        3. Check Ollama and Gemma availability.
        4. Retrieve relevant chunks via Day 12 FAISS semantic search using (retrieval_query or question).
        5. Convert chunks to LangChain Documents.
        6. Construct context with size control.
        7. Format conversation history under controlled budget.
        8. Execute LangChain prompt template and ChatOllama chain with Day 16 structured sections.
        9. Return grounded answer with verified source citations.
        """
        # 1. Validate request
        clean_question, valid_k = self.validate_request(question, top_k)

        # 2. Check indexing status
        self.check_project_indexing_status(db, project)

        # 3. Check Ollama / Gemma health (Phase 35)
        health = ollama_service.check_health()
        if not health.ollama.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemma is currently unavailable. Please ensure Ollama is running.",
            )
        if not health.model.available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Configured model '{settings.OLLAMA_MODEL}' is not installed in Ollama. "
                    f"Please run 'ollama pull {settings.OLLAMA_MODEL}' and try again."
                ),
            )

        # 4. Day 17 File-Level Context Retrieval (reusing Day 12 FAISS semantic search)
        # Use retrieval_query if provided (e.g. enriched contextual follow-up query), else clean_question
        search_query = (retrieval_query or clean_question).strip()
        try:
            retrieval_result = context_retriever.retrieve_context(
                db=db,
                project=project,
                query=search_query,
                top_files=valid_k if valid_k != 5 else getattr(settings, "RETRIEVAL_TOP_FILES", 5),
                candidate_chunks=getattr(settings, "RETRIEVAL_CANDIDATE_CHUNKS", 30),
                chunks_per_file=getattr(settings, "RETRIEVAL_CHUNKS_PER_FILE", 3),
                min_similarity=getattr(settings, "RETRIEVAL_MIN_SIMILARITY_THRESHOLD", 0.20),
            )
            search_results = retrieval_result.selected_chunks
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete code indexing, embedding generation, and vector indexing before using CodeSage AI.",
            )
        except Exception as e:
            logger.error("Error during Context Retrieval for project %d: %s", project.id, e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Semantic retrieval failed during RAG processing.",
            )

        # Handle no results condition (Phase 37)
        if not search_results:
            return RagResponse(
                project_id=project.id,
                question=clean_question,
                answer="The available project context is insufficient to answer this question.",
                sources=[],
                model=settings.OLLAMA_MODEL,
            )

        # 5. Convert chunks to LangChain documents (Phase 10)
        documents = self.convert_chunks_to_documents(project.id, search_results)

        # 6. Context construction & size control (Phases 11, 12)
        max_context = getattr(settings, "CHAT_MAX_CONTEXT_LENGTH", getattr(settings, "MAX_CONTEXT_CHARACTERS", 12000))
        context_text, included_docs = self.build_context(documents, max_characters=max_context)

        # 7. Format conversation history (Day 16)
        max_history = getattr(settings, "CHAT_MAX_HISTORY_LENGTH", 4000)
        formatted_history = format_conversation_history(
            messages=conversation_history or [],
            max_history_chars=max_history,
        )

        # 8. LangChain RAG Chain Execution (Day 14 & 16)
        try:
            llm = self.get_llm()
            chain = self.prompt_template | llm | self.output_parser
            answer = chain.invoke(
                {
                    "system_instructions": SYSTEM_INSTRUCTIONS,
                    "project_context": context_text,
                    "conversation_history": formatted_history,
                    "question": clean_question,
                    "response_requirements": RESPONSE_REQUIREMENTS,
                }
            )
            clean_answer = (answer or "").strip()
        except Exception as e:
            logger.error("LangChain RAG chain invocation error: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to communicate with local Ollama/Gemma service. Please ensure Ollama is running.",
            )

        # 8. Source Citations (Phases 15, 16, 30)
        sources: List[RagSourceItem] = []
        for doc in included_docs:
            meta = doc.metadata
            sources.append(
                RagSourceItem(
                    chunk_id=meta["chunk_id"],
                    file_path=meta["file_path"],
                    file_name=meta["file_name"],
                    language=meta["language"],
                    start_line=meta["start_line"],
                    end_line=meta["end_line"],
                    symbol_name=meta.get("symbol_name"),
                    symbol_type=meta.get("symbol_type"),
                    score=round(float(meta["score"]), 4),
                )
            )

        return RagResponse(
            project_id=project.id,
            question=clean_question,
            answer=clean_answer,
            sources=sources,
            model=settings.OLLAMA_MODEL,
        )


# Global singleton instance
rag_service = RagService()
