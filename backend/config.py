from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ORCHESTRATOR_MODEL: str = "anthropic/claude-haiku-4-5"
    SCOUT_MODEL: str = "anthropic/claude-haiku-4-5"
    APPLICATOR_MODEL: str = "anthropic/claude-haiku-4-5"
    OUTREACH_MODEL: str = "anthropic/claude-haiku-4-5"

    SERP_API_KEY: str = ""
    JOB_MATCH_THRESHOLD: float = 0.6
    WEBHOOK_BYPASS_THRESHOLD: bool = False

    EMAIL_PROVIDER: str = "gmail"
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    OUTLOOK_CLIENT_ID: str = ""
    OUTLOOK_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/auth/email/callback"

    WEBHOOK_SECRET: str = ""

    DATABASE_URL: str = "sqlite:///./jobapplier.db"
    UPLOAD_DIR: str = "uploads"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
