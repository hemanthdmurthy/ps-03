# Metrics Inventory

## 1. HTTP Metrics (FastAPI)
- `http_requests_total` (Counter) - Total request count. Labels: method, endpoint, status_code.
- `http_request_duration_seconds` (Histogram) - Endpoint latency.

## 2. Database Metrics (SQLAlchemy)
- `db_query_duration_seconds` (Histogram) - Query latency. Labels: query_type.
- `db_connections_active` (Gauge) - Active connections in pool.

## 3. Cache Metrics (Redis)
- `redis_cache_operations_total` (Counter) - Ops count. Labels: operation, status.
- `redis_op_duration_seconds` (Histogram) - Ops latency.

## 4. Queue Metrics (Celery)
- `celery_tasks_total` (Counter) - Task runs. Labels: task_name, status.
- `celery_task_duration_seconds` (Histogram) - Queue execution latency.

## 5. Network Metrics
- `websocket_connections_active` (Gauge) - Open connections.
- `websocket_events_total` (Counter) - Pub/Sub event traffic.
