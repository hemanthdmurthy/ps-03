# Failure Dependency Map
## Distributed Async Backend Infrastructure

### 1. Redis Dependency Risks
- **Path**: API <-> Celery Broker <-> Redis <-> Celery Result Backend <-> Pub/Sub
- **Risk**: Redis failure drops the Celery broker, halts new tasks, and breaks WebSocket real-time updates.
- **Cascading Impact**: If Redis fails without backpressure/retry caps, API calls to enqueue tasks will timeout and potentially crash API threads.

### 2. Database Dependency Risks
- **Path**: Tasks (e.g. `notification_tasks.py`, `research_tasks.py`) <-> PostgreSQL / SQLite
- **Risk**: Database connection pool exhaustion under high Celery worker concurrency.
- **Cascading Impact**: Long-running transactions or missing DB timeouts can deadlock worker processes, preventing further task execution.

### 3. Worker Crash Risks
- **Path**: Celery Worker -> Task execution
- **Risk**: Unhandled exceptions, OOM (Out Of Memory) issues in worker threads.
- **Cascading Impact**: Without graceful degradation, crashed workers can result in lost tasks if `acks_late` is disabled (though it's enabled here).

### 4. Retry Storm Vulnerabilities
- **Path**: `notification_tasks.py` (Email dispatch retry), `research_tasks.py` (workflow retry).
- **Risk**: Email sending failure triggers exponential backoff but lacks a circuit breaker if SMTP is permanently down.
- **Cascading Impact**: Queue fills up with retries, delaying critical tasks.

### 5. Queue Failure Propagation
- **Path**: Celery default queue.
- **Risk**: No isolation between critical (research) and non-critical (notification) queues.
- **Cascading Impact**: Failure in notifications can exhaust workers and block research tasks.

### 6. Deadlock Risks
- **Path**: DB Session Management in Celery Hooks.
- **Risk**: Synchronous DB operations inside `on_failure` hooks in `research_tasks.py`.
- **Cascading Impact**: If the DB is down, the hook hangs, deadlocking the worker process permanently.
