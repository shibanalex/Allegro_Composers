"""Settings shared by all services (read from environment / .env)"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # One database for every service. SQLite for local dev, PostgreSQL in docker/production.
    database_url: str = "sqlite:///./allegro_platform.db"

    # Auth
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 14

    # File storage: local disk for now (S3/R2-compatible storage can replace it)
    media_dir: str = "media"
    media_url_prefix: str = "/media"
    max_upload_mb: int = 200

    # Comma-separated list of allowed browser origins
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    debug: bool = False


settings = Settings()
