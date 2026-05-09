from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
import os


class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    # Project
    PROJECT_NAME: str = "SigmaLite"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS - can be comma-separated string or list
    ALLOWED_ORIGINS: Union[List[str], str] = "http://localhost:5173,http://localhost:3000"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "./uploads"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Authentication
    DISABLE_AUTH: bool = False  # Set to True to disable authentication

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create upload directory if it doesn't exist
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        
        # Convert ALLOWED_ORIGINS string to list if needed
        if isinstance(self.ALLOWED_ORIGINS, str):
            self.ALLOWED_ORIGINS = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]

        self._validate_production_settings()

    def _validate_production_settings(self) -> None:
        """Reject local/demo settings when the app is explicitly production."""
        if self.ENVIRONMENT.lower() not in {"prod", "production"}:
            return

        unsafe_secret_values = {
            "change-me",
            "changeme",
            "secret",
            "dev-secret",
            "test-secret-key-not-for-production",
        }
        if self.SECRET_KEY.strip().lower() in unsafe_secret_values or len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be a strong production secret")

        if self.DISABLE_AUTH:
            raise ValueError("DISABLE_AUTH cannot be true in production")

        if "*" in self.ALLOWED_ORIGINS:
            raise ValueError("Wildcard ALLOWED_ORIGINS is not allowed in production")


settings = Settings()
