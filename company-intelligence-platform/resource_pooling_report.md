# Resource Pooling Report

## Database Pooling
- Base connections: 50
- Max overflow: 100
- Timeout: 60s
- Impact: Highly parallel workloads (e.g. bulk scraping results) will no longer crash due to `TimeoutError` when waiting for DB connections.

## Redis Pooling
- `aioredis` implicit pooling utilized.
- Enhanced with `pipeline()` capability to reduce pool checkout frequency for batch ops.
