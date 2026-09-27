"""Settings shared by all services (read from environment / .env)"""
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholders that must never sign real tokens: anyone who knows them can log in as any user
PLACEHOLDER_SECRETS = {
    "", "dev-secret-key-change-in-production", "change-me-in-production", "your-secret-key-here-change-in-production",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # One database for every service. SQLite for local dev, PostgreSQL in docker/production.
    database_url: str = "sqlite:///./allegro_platform.db"

    # Auth
    secret_key: str = ""  # required: set SECRET_KEY in the environment or backend/.env
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 14

    # File storage. "local": the media_dir folder, served by the app under /media (development).
    # "s3": an S3-compatible bucket (Yandex Object Storage, Cloudflare R2...); media_url_prefix is then the
    # bucket's public address, e.g. https://storage.yandexcloud.net/<bucket> or https://pub-xxxx.r2.dev
    storage_backend: Literal["local", "s3"] = "local"
    media_dir: str = "media"
    media_url_prefix: str = "/media"
    max_upload_mb: int = 200
    s3_endpoint_url: str = ""  # Yandex: https://storage.yandexcloud.net; R2: https://<account id>.r2.cloudflarestorage.com
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = "auto"  # Yandex: ru-central1

    # First start of a fresh site: whoever knows this code may create the very first account at /setup.
    # Works only while the database has no users at all, so it closes itself after one use.
    setup_token: str = ""

    # Access. While the community is invite-only: no sign-ups, and only these usernames may log in
    # (comma-separated; empty = everyone with an account). Hidden ("shadowed") accounts can never log in.
    registration_open: bool = False  # closed unless explicitly opened: a forgotten setting must not let strangers in
    login_allowlist: str = ""

    # Comma-separated list of allowed browser origins
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    debug: bool = False

    @model_validator(mode="after")
    def _real_secret(self):
        if self.secret_key in PLACEHOLDER_SECRETS or len(self.secret_key) < 32:
            raise ValueError(
                "SECRET_KEY не задан или слишком короткий (нужно ≥ 32 символов). "
                "Сгенерируйте: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return self

    @model_validator(mode="after")
    def _complete_storage(self):
        if self.storage_backend == "s3":
            missing = [name.upper() for name in ("s3_endpoint_url", "s3_bucket", "s3_access_key_id", "s3_secret_access_key")
                       if not getattr(self, name)]
            if not self.media_url_prefix.startswith(("https://", "http://")):
                missing.append("MEDIA_URL_PREFIX (публичный адрес бакета, https://...)")
            if missing:
                raise ValueError(f"Для STORAGE_BACKEND=s3 не заданы: {', '.join(missing)}")
        return self

    @property
    def setup_enabled(self) -> bool:
        return len(self.setup_token) >= 16

    def login_allowed(self, username: str) -> bool:
        allowed = {u.strip().lower() for u in self.login_allowlist.split(",") if u.strip()}
        return not allowed or username.lower() in allowed


settings = Settings()
