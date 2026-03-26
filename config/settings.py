from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    ideahunter_api_key: str = ""
    ideahunter_sqlite_path: str = "data/ideahunter.db"
    output_dir: str = "output"
    schedule_enabled: bool = False
    schedule_cron: str = "0 9 * * *"
    schedule_sources: list[str] = ["v2ex"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
