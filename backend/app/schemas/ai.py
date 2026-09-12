from typing import Optional
from pydantic import BaseModel, Field


class AiHealthOllamaInfo(BaseModel):
    available: bool = Field(..., description="Whether the local Ollama daemon is reachable")


class AiHealthModelInfo(BaseModel):
    name: str = Field(..., description="Configured Gemma model name")
    available: bool = Field(..., description="Whether the configured Gemma model is installed in Ollama")


class AiHealthResponse(BaseModel):
    """
    Response schema for GET /api/ai/health (Phases 11 & 20).
    """
    ollama: AiHealthOllamaInfo
    model: AiHealthModelInfo


class AiTestRequest(BaseModel):
    """
    Request schema for POST /api/ai/test (Phases 12, 15, 16).
    """
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Prompt text to send to Gemma via Ollama"
    )
    system_prompt: Optional[str] = Field(
        None,
        max_length=5000,
        description="Optional system prompt for context/persona guidance"
    )


class AiTestResponse(BaseModel):
    """
    Response schema for POST /api/ai/test (Phase 17).
    """
    response: str = Field(..., description="Generated text response from Gemma")
    model: str = Field(..., description="Model name that generated the response")
