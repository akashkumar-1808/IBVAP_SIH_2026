import os
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application settings
    ENVIRONMENT: str = Field(default="development", description="Environment mode: development, staging, production, test")
    APP_NAME: str = Field(default="IBVAP-Backend", description="Backend service application name")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    API_V1_STR: str = Field(default="/api/v1", description="API v1 prefix")
    HOST: str = Field(default="0.0.0.0", description="Backend host binding")
    PORT: int = Field(default=8000, description="Backend port binding")

    # Deployment, Camera & Storage settings
    STORAGE_ROOT: str = Field(default="storage", description="Root path for runtime evidence and output storage")
    DEMO_VIDEO_PATH: str = Field(default="storage/samples/test_video.mp4", description="Path to production demo MP4 video")
    DEFAULT_CAMERA_ID: str = Field(default="DEMO-CAM-01", description="Default camera ID for single-camera deployment")
    DEFAULT_DEVICE: str = Field(default="cpu", description="Compute device: cpu or cuda")
    YOLO_MODEL_PATH: str = Field(default="models/detector/yolov8n.pt", description="Path to YOLO weights file")
    AUTO_START_DEMO_PIPELINE: bool = Field(default=False, description="Auto-start live demo pipeline on server startup")

    # Supabase credentials & endpoints (Sensitive)
    SUPABASE_URL: Optional[str] = Field(default=None, description="Supabase project URL endpoint")
    SUPABASE_ANON_KEY: Optional[SecretStr] = Field(default=None, description="Supabase public anon key")
    SUPABASE_SERVICE_ROLE_KEY: Optional[SecretStr] = Field(default=None, description="Supabase privileged service-role key")

    # Direct PostgreSQL database URL (Optional)
    DATABASE_URL: Optional[SecretStr] = Field(default=None, description="Direct or pooled PostgreSQL connection string")

    # Supabase Storage settings
    EVIDENCE_STORAGE_BUCKET: str = Field(default="evidence", description="Storage bucket name for evidence files")
    MAX_UPLOAD_SIZE_MB: int = Field(default=50, description="Maximum allowed evidence upload size in MB")

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def is_supabase_configured(self) -> bool:
        """Returns True if minimum required Supabase URL and either service-role or anon key are set."""
        has_url = bool(self.SUPABASE_URL and self.SUPABASE_URL.strip() and not self.SUPABASE_URL.startswith("https://your-project-ref"))
        has_key = bool(
            (self.SUPABASE_SERVICE_ROLE_KEY and self.SUPABASE_SERVICE_ROLE_KEY.get_secret_value().strip() and not self.SUPABASE_SERVICE_ROLE_KEY.get_secret_value().startswith("your-"))
            or (self.SUPABASE_ANON_KEY and self.SUPABASE_ANON_KEY.get_secret_value().strip() and not self.SUPABASE_ANON_KEY.get_secret_value().startswith("your-"))
        )
        return has_url and has_key

    def get_service_key_value(self) -> Optional[str]:
        """Safely extracts service role key string without exposing in repr."""
        if self.SUPABASE_SERVICE_ROLE_KEY:
            val = self.SUPABASE_SERVICE_ROLE_KEY.get_secret_value()
            if val and not val.startswith("your-"):
                return val
        return None

    def get_anon_key_value(self) -> Optional[str]:
        """Safely extracts anon key string without exposing in repr."""
        if self.SUPABASE_ANON_KEY:
            val = self.SUPABASE_ANON_KEY.get_secret_value()
            if val and not val.startswith("your-"):
                return val
        return None

    @property
    def repo_root(self):
        from pathlib import Path
        return Path(__file__).resolve().parent.parent.parent.parent

    @property
    def storage_path(self):
        from pathlib import Path
        p = Path(self.STORAGE_ROOT)
        if not p.is_absolute():
            p = self.repo_root / p
        return p.resolve()

    @property
    def evidence_path(self):
        return self.storage_path / "evidence"

    @property
    def samples_path(self):
        return self.storage_path / "samples"

    @property
    def runs_path(self):
        return self.storage_path / "runs"

    def ensure_storage_directories(self) -> None:
        """Ensures that all runtime storage directories exist on disk."""
        self.evidence_path.mkdir(parents=True, exist_ok=True)
        self.samples_path.mkdir(parents=True, exist_ok=True)
        self.runs_path.mkdir(parents=True, exist_ok=True)


# Global settings singleton
settings = Settings()
