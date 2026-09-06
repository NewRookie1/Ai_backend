from pydantic_settings import BaseSettings
from typing import List
import json

class Settings(BaseSettings):
    APP_NAME: str = "Artisan AI Backend"
    DEBUG: bool = True
    
    # Defaults to a local SQLite file so the service boots with zero
    # configuration (e.g. fresh Render deploy without DATABASE_URL set).
    # Set DATABASE_URL to a Postgres URL for shared/persistent storage.
    DATABASE_URL: str = "sqlite:///./artisan_ai.db"
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    AI_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    # Text/chat model for agent, pricing, translation.
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    # Vision-capable model for image analysis (auto-catalogue).
    GROQ_VISION_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    GROQ_STT_MODEL: str = "whisper-large-v3"
    GROQ_API_BASE: str = "https://api.groq.com/openai/v1"
    
    OPENAI_API_KEY: str = ""
    
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8080"]'
    
    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
