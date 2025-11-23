"""Application configuration using Pydantic settings."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Database
    postgres_user: str = "maestro"
    postgres_password: str = "change_me"
    postgres_db: str = "maestro"
    database_url: str = "postgresql://maestro:change_me@postgres:5432/maestro"
    
    # Ollama
    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "llama3:8b"
    ollama_gpu_enabled: bool = False
    
    # Google Cloud
    google_cloud_project: Optional[str] = None
    google_application_credentials: Optional[str] = None
    google_drive_folder_id: Optional[str] = None
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    
    # Google Gemini
    google_gemini_api_key: Optional[str] = None
    
    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    log_level: str = "INFO"
    
    # Security
    allowed_origins: str = "http://localhost:3000,http://localhost:8000,http://localhost:5173"
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Paths (container paths)
    obsidian_vault_path: str = "/app/data/vault"
    gdrive_sync_path: str = "/app/data/gdrive-sync"

    # Local host path (for setup scripts and volume mounting)
    local_obsidian_path: Optional[str] = None
    
    # Feature Flags
    enable_proactive_suggestions: bool = True
    enable_hitl_confirmations: bool = True
    enable_user_behavior_modeling: bool = False
    
    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins string to list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()
