import os
import sys
import logging
import re
import json
from loguru import logger
from app.core.config import settings

# Ensure the logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Sensitive keys patterns for masking (production safety)
SENSITIVE_KEYS = {
    "password", "token", "api_key", "secret", "authorization", 
    "access_token", "refresh_token", "hashed_password", 
    "client_secret", "supabase_anon_key", "jwt_secret_key"
}

SENSITIVE_PATTERN = re.compile(
    r"(" + "|".join(SENSITIVE_KEYS) + r")", 
    re.IGNORECASE
)

def mask_dict(d: dict) -> dict:
    """Recursively masks keys containing sensitive keywords in a dictionary."""
    if not isinstance(d, dict):
        return d
    
    masked = {}
    for k, v in d.items():
        if isinstance(v, dict):
            masked[k] = mask_dict(v)
        elif isinstance(v, list):
            masked[k] = [mask_dict(item) if isinstance(item, dict) else item for item in v]
        elif SENSITIVE_PATTERN.search(str(k)):
            masked[k] = "********"
        else:
            masked[k] = v
    return masked

def mask_string_secrets(text: str) -> str:
    """Masks authorization headers or keys inside log strings."""
    if not isinstance(text, str):
        return text
    text = re.sub(r"(bearer\s+)[a-zA-Z0-9_\-\.]+", r"\1********", text, flags=re.IGNORECASE)
    text = re.sub(r"(password|secret|token|api_key|key)(=|:\s*['\"]?)[a-zA-Z0-9_\-\.]+", r"\1\2********", text, flags=re.IGNORECASE)
    return text

class InterceptHandler(logging.Handler):
    """
    Default handler to intercept standard library logging messages
    and route them through Loguru.
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # Determine category based on logger name
        category = None
        name_lower = record.name.lower()
        if "access" in name_lower or "middleware.logging" in name_lower or "middleware.request_tracking" in name_lower:
            category = "access"
        elif "auth" in name_lower or "security" in name_lower:
            category = "auth"
        elif "celery" in name_lower or "tasks" in name_lower or "workflow" in name_lower or "redis" in name_lower:
            category = "tasks"

        log_bound = logger.bind(logger_name=record.name)
        if category:
            log_bound = log_bound.bind(category=category)

        # Mask secrets in string messages
        msg = mask_string_secrets(record.getMessage())
        
        log_bound.opt(depth=depth, exception=record.exc_info).log(level, msg)

def format_production_json(record):
    """Formats Loguru records into clean, production-safe JSON structures."""
    # Mask secrets in extra data
    extra_data = mask_dict(record["extra"])
    
    # Mask secrets in log message
    masked_message = mask_string_secrets(record["message"])

    exception_data = None
    if record["exception"]:
        exception_data = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback
        }

    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": masked_message,
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "category": extra_data.pop("category", "system"),
        "extra": extra_data,
        "exception": exception_data
    }
    
    # Escape curly braces for Loguru's formatting system
    serialized = json.dumps(log_entry) + "\n"
    return serialized.replace("{", "{{").replace("}", "}}")

def format_human_readable(record):
    """Beautiful human-readable formatting with custom color palettes."""
    extra_data = mask_dict(record["extra"])
    masked_message = mask_string_secrets(record["message"])
    
    # Pop specific categories to keep formatting clean
    category = extra_data.pop("category", None)
    logger_name = extra_data.pop("logger_name", record["name"])
    
    cat_str = f" [{category.upper()}]" if category else ""
    extra_str = f" | Context: {extra_data}" if extra_data else ""
    
    # Escape curly braces in dynamic content to prevent Loguru format_map KeyErrors
    masked_message = masked_message.replace("{", "{{").replace("}", "}}")
    extra_str = extra_str.replace("{", "{{").replace("}", "}}")
    
    # Escape angle brackets to prevent Loguru color tag parsing errors (e.g. <undefined>)
    masked_message = masked_message.replace("<", "\\<")
    extra_str = extra_str.replace("<", "\\<")
    
    # Return formatted string with Loguru markup tags
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
        f"{cat_str} - <level>{masked_message}</level>{extra_str}\n"
    )


def configure_logging(level=logging.INFO):
    """Centralized configuration of the Loguru framework for FastAPI backend."""
    # 1. Clear existing standard library logging handlers
    logging.getLogger().handlers = []
    
    # 2. Intercept logs of major libraries
    interceptable_loggers = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "sqlalchemy",
        "gunicorn",
        "gunicorn.access",
        "gunicorn.error",
        "celery",
        "celery.task",
        "celery.worker"
    ]
    
    for name in interceptable_loggers:
        logging_logger = logging.getLogger(name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
        logging_logger.setLevel(level)

    # Attach interceptor to standard root logger to catch everything
    logging.getLogger().handlers = [InterceptHandler()]
    logging.getLogger().setLevel(level)

    # 3. Configure Loguru Sinks
    logger.remove()  # Clear Loguru's default console handler

    is_prod = settings.ENVIRONMENT.lower() == "production"
    log_format = format_production_json if is_prod else format_human_readable

    # SINK 1: Console logging
    logger.add(
        sys.stderr,
        level=level,
        format=format_human_readable,  # Console is always beautiful for developer visibility
        colorize=True,
        enqueue=True
    )

    # SINK 2: General Application Logs
    logger.add(
        os.path.join(LOGS_DIR, "app.log"),
        level=level,
        format=log_format,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True
    )

    # SINK 3: Dedicated Error Logs (level >= ERROR)
    logger.add(
        os.path.join(LOGS_DIR, "error.log"),
        level=logging.ERROR,
        filter=lambda r: r["level"].no >= logging.ERROR,
        format=log_format,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True
    )

    # SINK 4: Access Log separation
    logger.add(
        os.path.join(LOGS_DIR, "access.log"),
        filter=lambda r: r["extra"].get("category") == "access",
        level=level,
        format=log_format,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True
    )

    # SINK 5: Authentication Log separation
    logger.add(
        os.path.join(LOGS_DIR, "auth.log"),
        filter=lambda r: r["extra"].get("category") == "auth",
        level=level,
        format=log_format,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True
    )

    # SINK 6: Background Tasks Log separation
    logger.add(
        os.path.join(LOGS_DIR, "tasks.log"),
        filter=lambda r: r["extra"].get("category") == "tasks",
        level=level,
        format=log_format,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True
    )

    logger.info("Enterprise-grade Loguru centralized logging configured successfully.")
