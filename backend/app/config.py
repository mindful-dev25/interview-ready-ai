from functools import lru_cache
import json
from json import JSONDecodeError
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Interview Ready AI"
    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_chat_model: str = ""

    chroma_persist_dir: str = "./chroma_db"
    session_store_path: str = "./sessions"
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]

        value = value.strip()
        if not value:
            return []

        if value.startswith("["):
            try:
                decoded = json.loads(value)
            except JSONDecodeError:
                decoded = None
            if isinstance(decoded, list):
                return [str(origin).strip() for origin in decoded if str(origin).strip()]

        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
