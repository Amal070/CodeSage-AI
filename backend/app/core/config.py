import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from app directory or backend directory
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings:
    PROJECT_NAME: str = "CodeSage AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:psql@localhost:5432/codesage_db"
    )

    # JWT Authentication
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "codesage-ai-super-secret-key-2026-production-grade-security-token"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )

    # Project Upload & Storage (Day 5)
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))
    STORAGE_DIR: str = os.getenv(
        "STORAGE_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "storage")
    )

    # File Explorer & Code Viewer (Day 6)
    MAX_VIEWABLE_FILE_SIZE_MB: int = int(os.getenv("MAX_VIEWABLE_FILE_SIZE_MB", "5"))

    # Embedding Generation (Day 11)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5")
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "auto")
    EMBEDDING_NORMALIZE: bool = os.getenv("EMBEDDING_NORMALIZE", "true").lower() in ("true", "1", "yes")

    # FAISS Semantic Retrieval (Day 12)
    INDEXES_DIR: str = os.getenv(
        "INDEXES_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "storage" / "indexes")
    )
    DEFAULT_SEARCH_TOP_K: int = int(os.getenv("DEFAULT_SEARCH_TOP_K", "5"))
    MAX_SEARCH_TOP_K: int = int(os.getenv("MAX_SEARCH_TOP_K", "20"))

    # Ollama & Gemma LLM (Day 13)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma:2b")
    MAX_PROMPT_LENGTH: int = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))

    # LangChain & RAG Pipeline (Day 14)
    DEFAULT_RAG_TOP_K: int = int(os.getenv("DEFAULT_RAG_TOP_K", "5"))
    MAX_RAG_TOP_K: int = int(os.getenv("MAX_RAG_TOP_K", "10"))
    MAX_RAG_QUESTION_LENGTH: int = int(os.getenv("MAX_RAG_QUESTION_LENGTH", "5000"))
    MAX_CONTEXT_CHARACTERS: int = int(os.getenv("MAX_CONTEXT_CHARACTERS", "12000"))

settings = Settings()
