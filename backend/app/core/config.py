from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_EMAIL: str
    SMTP_PASSWORD: str
    OTP_SECRET: str
    OTP_HASH_SECRET: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    GOOGLE_CLIENT_ID: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Storage settings
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET_RESUMES: str = "resumes"
    SUPABASE_STORAGE_BUCKET_JOB_DOCS: str = "job-descriptions"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Internal ML team integration key
    INTERNAL_ML_API_KEY: str = "ml-internal-secret-token"

    # ML matching service URL (standalone FastAPI ML service)
    ML_SERVICE_URL: str = "http://localhost:8001"
    PROFESSIONAL_MATCH_THRESHOLD: float = 60.0

    app_name: str = "NexAbility API"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
