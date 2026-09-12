import logging
from fastapi import APIRouter, Depends, status

from app.api.auth import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AiHealthResponse,
    AiTestRequest,
    AiTestResponse,
)
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI & LLM"])


@router.get(
    "/health",
    response_model=AiHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check local Ollama daemon and Gemma model status",
)
def check_ai_health(
    current_user: User = Depends(get_current_user),
) -> AiHealthResponse:
    """
    Day 13 AI Health Check Endpoint:
    - Authenticated via JWT.
    - Verifies local Ollama daemon reachability on port 11434.
    - Verifies presence of the configured Gemma model.
    - Never throws unhandled exceptions or crashes FastAPI.
    """
    return ollama_service.check_health()


@router.post(
    "/test",
    response_model=AiTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test prompt execution with Gemma via Ollama",
)
def test_ai_prompt(
    request: AiTestRequest,
    current_user: User = Depends(get_current_user),
) -> AiTestResponse:
    """
    Day 13 Protected Gemma Connection Test Endpoint:
    - Authenticated via JWT.
    - Validates prompt content and max length bounds.
    - Sends prompt directly to local Ollama/Gemma service.
    - Returns clean generated response without leaking internal structures.
    """
    generated = ollama_service.generate(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
    )
    return AiTestResponse(
        response=generated,
        model=ollama_service.model_name,
    )
