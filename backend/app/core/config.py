from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
import os


class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    # Project
    PROJECT_NAME: str = "SigmaLite"
    VERSION: str = "0.2.0-beta.1"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: str = ""
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_BACKEND: str = "auto"  # auto, redis, memory
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS - can be comma-separated string or list
    ALLOWED_ORIGINS: Union[List[str], str] = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    UPLOAD_DIR: str = "./uploads"
    
    # Environment
    ENVIRONMENT: str
    DEBUG: bool = False
    ENABLE_OTEL: bool = False
    EXPOSE_API_DOCS: bool = False
    EXPOSE_PUBLIC_METRICS: bool = False
    METRICS_TOKEN: str = ""
    TRUST_PROXY_CLIENT_IP_HEADER: str = ""
    
    # Authentication
    DISABLE_AUTH: bool = False  # Set to True to disable authentication

    # Public-beta safety caps
    MAX_EXPORT_ROWS: int = 100000
    MAX_FORMULA_LENGTH: int = 512
    MAX_FORMULA_EVAL_ROWS: int = 100000
    WS_TICKET_TTL_SECONDS: int = 60

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create upload directory if it doesn't exist
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        
        # Convert ALLOWED_ORIGINS string to list if needed
        if isinstance(self.ALLOWED_ORIGINS, str):
            self.ALLOWED_ORIGINS = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]

        self._validate_environment_settings()

    def _validate_environment_settings(self) -> None:
        """Reject unknown or unsafe settings before serving public traffic."""
        environment = self.ENVIRONMENT.lower()
        allowed_environments = {
            "development",
            "test",
            "testing",
            "staging",
            "selfhosted",
            "production",
        }
        if environment not in allowed_environments:
            raise ValueError(
                "ENVIRONMENT must be one of development, test, staging, selfhosted, production"
            )

        unsafe_secret_values = {
            "change-me",
            "changeme",
            "secret",
            "dev-secret",
            "test-secret-key-not-for-production",
            "your-secret-key-change-this-in-production",
            "replace-with-a-long-random-secret",
        }
        if self.is_public_environment():
            if self.SECRET_KEY.strip().lower() in unsafe_secret_values or len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be a strong public-environment secret")

            if self.DISABLE_AUTH:
                raise ValueError("DISABLE_AUTH cannot be true in public environments")

            if "*" in self.ALLOWED_ORIGINS:
                raise ValueError("Wildcard ALLOWED_ORIGINS is not allowed in public environments")

            if self.RATE_LIMIT_BACKEND != "redis":
                raise ValueError("RATE_LIMIT_BACKEND must be redis in public environments")

    def is_public_environment(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "staging", "selfhosted"}

    def api_docs_enabled(self) -> bool:
        return not self.is_public_environment() or self.EXPOSE_API_DOCS

    def public_metrics_enabled(self) -> bool:
        return not self.is_public_environment() or self.EXPOSE_PUBLIC_METRICS


settings = Settings()
