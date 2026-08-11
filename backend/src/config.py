from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Settings
    POSTGRES_USER: str = "rag_user"
    POSTGRES_PASSWORD: str = "change_me_in_production"
    POSTGRES_DB: str = "school_rag"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = ""

    # OpenRouter / LLM Settings
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    DEFAULT_LLM_MODEL: str = "google/gemini-2.5-flash"
    EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
    ADMIN_API_KEY: str = ""

    # Admin authentication (password-based)
    # Store a bcrypt hash here, never the plaintext password.
    ADMIN_PASSWORD_HASH: str = ""
    # JWT secret for admin session tokens
    SECRET_KEY: str = "change_this_secret_key_in_production_please"

    # CORS settings
    CORS_ORIGINS: str = "http://localhost:3000,https://arthurjarvisuniversity.edu.ng"

    def get_database_url(self) -> str:
        raw_url = (self.DATABASE_URL or "").strip().strip('"').strip("'")
        if raw_url:
            return raw_url
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
