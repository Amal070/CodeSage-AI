import os
from pydantic import BaseModel

class AppConfig(BaseModel):
    app_name: str = 'DataPipelineService'
    batch_size: int = 50
    environment: str = 'production'
    api_timeout_seconds: int = 10

def load_config() -> AppConfig:
    """Loads configuration settings from environment variables."""
    return AppConfig(
        batch_size=int(os.getenv('BATCH_SIZE', '50')),
        environment=os.getenv('PIPELINE_ENV', 'production'),
        api_timeout_seconds=int(os.getenv('TIMEOUT', '10')),
    )
