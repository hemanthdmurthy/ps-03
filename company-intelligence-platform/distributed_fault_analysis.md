# Distributed Fault Analysis
## Enterprise-Grade Resilience Assessment

### 1. Circuit Breaker Deficiencies
- Currently, tasks interact with external services (SMTP, LLM APIs) without circuit breakers. A persistent failure will exhaust retry limits across all workers simultaneously.
- **Recommendation**: Implement a Redis-backed distributed circuit breaker pattern for external API calls and DB queries.

### 2. Dead-Letter Queues (DLQ)
- Failed tasks that exceed max retries are simply dropped and logged.
- **Recommendation**: Implement a DLQ routing mechanism to park permanently failed tasks for manual inspection and replay.

### 3. Graceful Degradation & Fallbacks
- `redis_client.py` has a FakeRedis fallback, which is good. But tasks like `send_notification_task` fail hard if DB is down.
- **Recommendation**: Provide fallback paths, e.g., storing to a file or Redis if DB is temporarily unavailable.

### 4. Bulkhead Isolation
- All tasks appear to run in a unified worker pool without queue segmentation.
- **Recommendation**: Introduce task routing to isolate heavy compute tasks (Research) from I/O tasks (Notifications).

### 5. Timeout Containment
- Celery `task_time_limit` is set globally to 3600s. Individual tasks need stricter, granular timeouts.
- **Recommendation**: Add strict `time_limit` and `soft_time_limit` decorators per task based on expected SLA.

### 6. Retry Isolation & Caps
- Need to ensure `max_retries` are capped system-wide to prevent queue clogging (Retry storms).

### Action Plan
1. Introduce a `CircuitBreaker` utility.
2. Implement DLQ in Celery configuration.
3. Enhance `ResearchWorkflowTask` and `send_notification_task` with isolation and strict timeouts.
4. Add global Retry limitations and Queue Isolation.
