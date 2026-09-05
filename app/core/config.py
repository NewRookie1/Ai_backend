from pydantic_settings import BaseSettings
from typing import List
import json

class Settings(BaseSettings):
    APP_NAME: str = "Artisan AI Backend"
    DEBUG: bool = True
    
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/artisan_ai"
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    AI_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
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
