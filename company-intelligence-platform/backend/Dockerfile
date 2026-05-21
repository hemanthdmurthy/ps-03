# Multi-stage Dockerfile for FastAPI Backend, Celery Worker, and Beat Scheduler
# ==========================================
# Stage 1: Build Dependencies
# ==========================================
FROM python:3.11-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered output logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /code

# Install build dependencies for Postgres client / compilation if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for sandboxed, relocatable packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file first to take advantage of Docker layer caching
COPY requirements.txt .

# Install dependencies using pip cache mounting to speed up repeated builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# ==========================================
# Stage 2: Final Minimal Runtime
# ==========================================
FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /code

# Install PostgreSQL client tools (for pg_isready healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy codebase
COPY . .

# Setup entrypoint script
RUN chmod +x entrypoint.sh

# Expose FastAPI backend default port
EXPOSE 8000

# Leverage entrypoint to manage DB synchronization and app boot
ENTRYPOINT ["/code/entrypoint.sh"]

# Default command starts FastAPI with Uvicorn (overridden for Celery worker & beat)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
