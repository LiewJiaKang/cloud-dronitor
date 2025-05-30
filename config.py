from pydantic_settings import BaseSettings
from typing import List
import secrets

class Settings(BaseSettings):
    # API Settings
    API_KEYS: str
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    
    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./dronitor.db"
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS Settings (if needed)
    ALLOW_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env" 