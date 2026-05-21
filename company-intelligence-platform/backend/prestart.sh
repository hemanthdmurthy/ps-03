#!/bin/bash
set -e
python -c "from app.utils.db_reconciler import reconcile_database_schema; reconcile_database_schema()"
