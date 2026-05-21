import logging
import os
import functools
import time
import traceback
from typing import Dict, Any, List, Optional, Callable
from langsmith import Client, traceable
import langsmith as ls
from app.core.config import settings

# Setup logger for observability module
logger = logging.getLogger("company_intel.observability")

# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL LANGSMITH INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════

_client_instance = None

def initialize_langsmith():
    """
    Initializes the LangSmith client globally with environment validation and graceful fallback.
    """
    global _client_instance

    if _client_instance is not None:
        return _client_instance

    try:
        # 1. Environment Variable Validation
        required_vars = ["LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2", "LANGCHAIN_PROJECT"]
        missing_vars = [v for v in required_vars if not getattr(settings, v, None)]

        tracing_enabled = str(settings.LANGCHAIN_TRACING_V2).lower() == "true"

        if not tracing_enabled:
            logger.info("LangSmith tracing is disabled via LANGCHAIN_TRACING_V2.")
            return None

        if missing_vars:
            logger.warning(f"LangSmith initialization skipped. Missing variables: {', '.join(missing_vars)}")
            return None

        # 2. Initialization
        logger.info(f"Initializing Production LangSmith Client (Project: {settings.LANGCHAIN_PROJECT})")
        _client_instance = Client()

        logger.info("LangSmith initialized successfully.")
        return _client_instance

    except Exception as e:
        logger.error(f"FAIL-SAFE: LangSmith initialization failed: {e}")
        logger.debug(traceback.format_exc())
        _client_instance = None
        return None

# Initialize global client
client = initialize_langsmith()

# ═══════════════════════════════════════════════════════════════════════════
# TRACING UTILITIES & HELPERS
# ═══════════════════════════════════════════════════════════════════════════

class TracingHelper:
    """
    Production-grade utilities for LangSmith observability.
    Provides standardized metadata, tagging, and error logging.
    """

    @staticmethod
    def set_standard_metadata(
        company: Optional[str] = None,
        session_id: Optional[str] = None,
        stage: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Injects a standardized set of production metadata into the current trace."""
        metadata = {
            "environment": settings.ENVIRONMENT,
            "timestamp": time.time(),
            "version": "1.0.0"
        }
        if company: metadata["company"] = company
        if session_id: metadata["session_id"] = session_id
        if stage: metadata["execution_stage"] = stage
        if model: metadata["model_name"] = model
        if provider: metadata["provider"] = provider

        if extra:
            metadata.update(extra)

        try:
            ls.set_run_metadata(**metadata)
        except Exception as e:
            logger.debug(f"Failed to set metadata: {e}")

    @staticmethod
    def add_tags(tags: List[str]):
        """Adds a list of tags to the current trace."""
        try:
            if hasattr(ls, "set_tags"):
                ls.set_tags(tags)
            else:
                ls.set_run_metadata(tags=tags)
        except Exception:
            pass

    @staticmethod
    def log_error(e: Exception, context: Optional[str] = None):
        """Logs an exception with stack trace to LangSmith."""
        error_info = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "stack_trace": traceback.format_exc()
        }
        if context:
            error_info["context"] = context

        try:
            ls.set_run_metadata(error=error_info)
            TracingHelper.add_tags(["error"])
        except Exception:
            pass

def trace_with_retry(name: str, tags: Optional[List[str]] = None):
    """
    Decorator for wrapping functions with traceable + error handling.
    """
    def decorator(func):
        @traceable(name=name, tags=tags or [])
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                TracingHelper.log_error(e, context=f"Execution of {name}")
                raise

        @traceable(name=name, tags=tags or [])
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                TracingHelper.log_error(e, context=f"Execution of {name}")
                raise

        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def get_langsmith_client():
    return client
