import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Resolve the root backend directory to load the correct .env file
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOTENV_PATH = os.path.join(BACKEND_DIR, ".env")

# Explicitly load environment variables from .env to ensure they are available globally
load_dotenv(DOTENV_PATH)

class Settings(BaseSettings):
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    NODE_ENV: str = "development"

    # CORS and Frontend Settings
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    FRONTEND_URL: str = "http://localhost:3000"

    # Supabase credentials (required)
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str

    # Database connection URL (supports PostgreSQL, MySQL, SQLite)
    DATABASE_URL: str = "sqlite:///./company_intel.db"

    # Redis & Celery configurations
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Caching configurations
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 300  # Default to 5 minutes (300s)

    # JWT authentication settings
    JWT_SECRET_KEY: str = "supersecretaccesskeyforcompanyintelligenceportal"
    JWT_REFRESH_SECRET_KEY: str = "supersecretrefreshkeyforcompanyintelligenceportal"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM keys (optional, but needed at runtime for agents)
    GEMINI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None

    # LLM Settings
    MODEL_PROVIDER: str = "google"
    MODEL_NAME: str = "gemini-2.0-flash"
    TEMPERATURE: float = 0.2

    # Search API (optional, fallback to simulation if empty)
    TAVILY_API_KEY: Optional[str] = None
    ENABLE_TAVILY: bool = True

    # LangSmith Observability
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "company-research-agent"

    # OpenTelemetry Configuration (OTel-spec standard variable names)
    OTEL_ENABLED: bool = True                            # Emergency kill switch
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""                # gRPC/HTTP endpoint (e.g. http://otel-collector:4317)
    OTEL_EXPORTER_OTLP_PROTOCOL: str = "grpc"            # "grpc" or "http/protobuf"
    OTEL_SERVICE_NAME: str = "placement-intel-backend"    # Service identity in traces
    OTEL_RESOURCE_ATTRIBUTES: str = ""                    # Comma-separated key=value pairs
    OTEL_EXPORT_CONSOLE: str = "false"                    # "true" for console span output
    OTEL_JAEGER_ENDPOINT: str = ""                        # Jaeger fallback (e.g. http://localhost:4317)
    OTEL_WATCHDOG_INTERVAL: int = 60                      # Seconds between collector health probes

    model_config = SettingsConfigDict(
        env_file=DOTENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate config
settings = Settings()
