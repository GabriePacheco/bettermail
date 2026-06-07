from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    app_env: str = Field("development", alias="APP_ENV")
    allowed_origins: str = Field("", alias="ALLOWED_ORIGINS")
    trial_limit: int = Field(10, alias="TRIAL_LIMIT")
    model_name: str = Field("gpt-4.1-mini", alias="MODEL_NAME")
    app_shared_secret: str = Field(..., alias="APP_SHARED_SECRET")
    payphone_enabled: bool = Field(False, alias="PAYPHONE_ENABLED")
    payphone_token: str = Field("", alias="PAYPHONE_TOKEN")
    payphone_store_id: str = Field("", alias="PAYPHONE_STORE_ID")
    payphone_coding_password: str = Field("", alias="PAYPHONE_CODING_PASSWORD")

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origins(self) -> list[str]:
        if not self.allowed_origins:
            return []
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
