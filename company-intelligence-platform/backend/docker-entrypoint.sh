#!/bin/bash
set -e
echo "Running pre-start schema reconciliation..."
python -c "from app.utils.db_reconciler import reconcile_database_schema; reconcile_database_schema()"
exec "$@"
