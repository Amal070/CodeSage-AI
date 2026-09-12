import logging
import threading
from typing import Optional

import ollama
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.ai import (
    AiHealthModelInfo,
    AiHealthOllamaInfo,
    AiHealthResponse,
)

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Service responsible for Day 13 Ollama + Gemma LLM Integration:
    - Reusable connection to local Ollama daemon (Phases 9 & 10).
    - Model availability and daemon health verification (Phase 11).
    - Single-turn text generation with prompt validation and optional system prompt (Phases 15 & 16).
    - Production-grade error handling preventing stack trace / path leakage (Phase 19).
    - Foundation for future RAG generation without premature Day 14+ coupling.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OLLAMA_MODEL
        self._client: Optional[ollama.Client] = None
        self._lock = threading.Lock()

    @property
    def client(self) -> ollama.Client:
        """
        Thread-safe singleton client getter to reuse connections across requests (Phase 10).
        """
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = ollama.Client(host=self.base_url)
        return self._client

    def is_model_installed(self, target_model: str, installed_models: list) -> bool:
        """
        Matches target model name against installed models list (e.g. 'gemma:2b' vs 'gemma:2b' or 'gemma:latest').
        """
        target = target_model.strip().lower()
        for m in installed_models:
            m_name = getattr(m, "model", str(m)).strip().lower()
            if m_name == target:
                return True
            # Match repository prefix if tag omitted (e.g., 'gemma' matching 'gemma:2b')
            if ":" not in target and m_name.startswith(f"{target}:"):
                return True
            if ":" not in m_name and target.startswith(f"{m_name}:"):
                return True
        return False

    def check_health(self) -> AiHealthResponse:
        """
        Checks connectivity to Ollama daemon and availability of configured Gemma model (Phases 11 & 20).
        Never throws unhandled exceptions.
        """
        try:
            models_response = self.client.list()
            installed_models = getattr(models_response, "models", [])
            model_found = self.is_model_installed(self.model_name, installed_models)

            return AiHealthResponse(
                ollama=AiHealthOllamaInfo(available=True),
                model=AiHealthModelInfo(
                    name=self.model_name,
                    available=model_found,
                ),
            )
        except Exception as e:
            logger.warning(
                "Ollama daemon unreachable at %s: %s",
                self.base_url,
                e,
            )
            return AiHealthResponse(
                ollama=AiHealthOllamaInfo(available=False),
                model=AiHealthModelInfo(
                    name=self.model_name,
                    available=False,
                ),
            )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Sends prompt to Gemma via Ollama and returns the generated text response (Phases 12–17).
        - Validates prompt content and bounded size (Phase 15).
        - Supports optional system prompt (Phase 16).
        - Catches daemon downtime, missing models, and request timeouts (Phase 19).
        """
        clean_prompt = (prompt or "").strip()
        if not clean_prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt cannot be empty.",
            )

        max_len = getattr(settings, "MAX_PROMPT_LENGTH", 10000)
        if len(clean_prompt) > max_len:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt exceeds maximum allowed length of {max_len} characters.",
            )

        clean_system = system_prompt.strip() if system_prompt and system_prompt.strip() else None

        # Verify daemon and model reachability
        health = self.check_health()
        if not health.ollama.available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ollama service is not running. Please start Ollama and try again.",
            )

        if not health.model.available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Configured model '{self.model_name}' is not installed in Ollama. "
                    f"Please run 'ollama pull {self.model_name}' and try again."
                ),
            )

        try:
            kwargs = {
                "model": self.model_name,
                "prompt": clean_prompt,
                "stream": False,
            }
            if clean_system:
                kwargs["system"] = clean_system

            response = self.client.generate(**kwargs)

            # Response object handling
            generated_text = getattr(response, "response", "") or ""
            if not generated_text and isinstance(response, dict):
                generated_text = response.get("response", "")

            return generated_text.strip()

        except ollama.ResponseError as e:
            logger.error("Ollama ResponseError: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ollama generation error: {e.error if hasattr(e, 'error') else str(e)}",
            )
        except Exception as e:
            logger.error("Unexpected error connecting to Ollama: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to communicate with local Ollama service. Please check daemon status.",
            )


# Global singleton instance
ollama_service = OllamaService()
