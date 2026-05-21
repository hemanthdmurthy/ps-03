# Logging Standardization Report

## Context
All platform services now use Loguru to emit structured, normalized logging data.

## Configuration
- `logging_util.py` intercepts standard logging events (including Uvicorn, Celery, SQLAlchemy) and routes them into Loguru.
- In `PRODUCTION` environments, all logs are serialized to JSON with `format_production_json`.
- Sensitive data (e.g., passwords, keys, tokens) are explicitly scrubbed and masked using a dictionary traverser and regex filter.

## Categories & Sinks
Separate physical log files are maintained for:
- `app.log`: Aggregated system events.
- `error.log`: Aggregated errors (>= ERROR).
- `access.log`: HTTP access tracking.
- `tasks.log`: Celery background processing.
- `auth.log`: Security boundaries.
