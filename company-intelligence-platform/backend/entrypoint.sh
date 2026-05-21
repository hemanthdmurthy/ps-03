#!/bin/bash
set -e

# Function to wait for PostgreSQL to be ready
wait_for_db() {
  if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == postgresql* ]]; then
    echo "Waiting for database to be ready at: $DATABASE_URL"
    until pg_isready -d "$DATABASE_URL" -t 2 >/dev/null 2>&1; do
      echo "Database is unavailable - sleeping 1s..."
      sleep 1
    done
    echo "Database is ready!"
  else
    echo "Using non-PostgreSQL database. Skipping database readiness check."
  fi
}

# Wait for DB connectivity if PostgreSQL is active
wait_for_db

# If the command passed is to run the FastAPI web server, run migrations first
if [[ "$*" == *"uvicorn"* ]]; then
  echo "Detected FastAPI application startup."
  echo "Running Alembic database migrations (upgrade head)..."
  alembic upgrade head
  echo "Database migrations applied successfully!"
fi

# Execute the passed container command (FastAPI, Celery worker, or Celery beat)
echo "Executing container command: $*"
exec "$@"
