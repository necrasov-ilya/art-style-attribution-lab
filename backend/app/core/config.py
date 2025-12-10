"""Application configuration with environment variables."""
import os
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Art Style Attribution Lab"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/art_style_db"
    
    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Upload settings
    UPLOAD_DIR: Path = Path(__file__).parent.parent.parent / "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # ML model path
    ML_DIR: Path = Path(__file__).parent.parent.parent / "ml"
    
    # ML Prediction settings
    ML_INCLUDE_UNKNOWN_ARTIST: bool = False  # Include "Unknown Artist" in predictions
    ML_TOP_K: int = 3  # Number of top predictions (use 4 if including Unknown)
    
    # LLM Configuration
    LLM_PROVIDER: Literal["openai", "openrouter", "ollama", "none"] = "none"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # OpenRouter
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "anthropic/claude-3-haiku"
    OPENROUTER_VISION_MODEL: str = "openrouter/bert-nebulon-alpha"
    
    # Vision LLM for scene analysis
    VISION_LLM_ENABLED: bool = False
    VISION_LLM_PROVIDER: Literal["openai", "openrouter", "ollama", "none"] = "none"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    
    # LLM Generation settings
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT: int = 180  # Increased from 120 for complex analyses  
    
    # ComfyUI Configuration
    COMFYUI_BASE_URL: str = "http://127.0.0.1:8188"
    COMFYUI_ENABLED: bool = True
    COMFYUI_TIMEOUT: int = 120  
    COMFYUI_CHECKPOINT: str = ""  
    
    # Workflows path
    WORKFLOWS_DIR: Path = Path(__file__).parent.parent / "workflows"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Create upload directory if it doesn't exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
