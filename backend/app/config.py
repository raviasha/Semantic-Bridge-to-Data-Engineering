import os
from pathlib import Path

from pydantic_settings import BaseSettings
from typing import Optional

# Find .env in the workspace root (parent of backend/)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    database_url: Optional[str] = None

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"


settings = Settings()
