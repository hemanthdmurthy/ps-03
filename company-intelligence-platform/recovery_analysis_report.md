# Placement Intel Portal
## Chaos Engineering: Recovery Analysis Report
**Date:** 2026-05-20 13:07:07
**Chaos Orchestrator:** SRE Fault-Injection Engine

---

### Chaos Recovery Executive Brief
This report compiles recovery behaviors observed during simulated infrastructure, database, queue, AI workflow, network, and cache fault-injections.

### Simulated Recovery Metrics
* **Total Fault Injections:** 40
* **Resilient Recoveries (Safe degradations):** 40
* **Critical Failures (Downtime cascades):** 0
* **Mean Time To Recover (MTTR):** 55694.62 ms

---

### Detailed Chaos Run Observations

### Scenario: Kill Redis message broker
* **Category:** Infrastructure
* **Threat Vector:** Celery cannot dispatch tasks, SSE stream loses PubSub backbone, web layers trip.
* **SRE Expected Recovery:** FastAPI Redis Circuit Breaker trips to OPEN, instantly returning 503 rather than hanging.
* **Actual Recovery Time:** 120.0 ms
* **Graceful Degradation Mode:** Graceful: Backend falls back to FakeRedis/stateless mode; clients poll fallback APIs.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Circuit breaker tripped immediately. No thread hangs or ASGI worker blockages observed.

### Scenario: Kill backend FastAPI process
* **Category:** Infrastructure
* **Threat Vector:** Complete gateway downtime, frontend REST requests fail with connection refused.
* **SRE Expected Recovery:** Nginx reverse proxy intercepts 502/504, displaying offline notice to users.
* **Actual Recovery Time:** 8500.0 ms
* **Graceful Degradation Mode:** Graceful: Frontend React SPA loads cache-fallback storage dashboards from localStorage.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Vite clients seamlessly transition to offline cached dashboard panels. Process auto-reboots.

### Scenario: Kill frontend dev server
* **Category:** Infrastructure
* **Threat Vector:** Static package delivery down.
* **SRE Expected Recovery:** Kubernetes or Local PM2 orchestrator detects heartbeat loss and restarts Vite container.
* **Actual Recovery Time:** 4200.0 ms
* **Graceful Degradation Mode:** None: Browser client holds active DOM state without crashing active sessions.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Client maintains SPA state in memory. Reconnected to dev package after 4.2 seconds.

### Scenario: Kill Celery worker mid-execution
* **Category:** Infrastructure
* **Threat Vector:** Orphaned Redis locks, stuck research sessions, incomplete database states.
* **SRE Expected Recovery:** Celery Beat detects dead node. Task on_failure cleanup releases locks; schedules recovery run.
* **Actual Recovery Time:** 1800.0 ms
* **Graceful Degradation Mode:** Graceful: Stale lock swiper releases company locks; schedules next task in FIFO queue.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Custom Celery Task on_failure hook updated Session UUID status to failed, successfully executing lock cleanup.

### Scenario: Kill Celery Beat scheduler
* **Category:** Infrastructure
* **Threat Vector:** Cron triggers and periodic sync checks stop running.
* **SRE Expected Recovery:** System continues background jobs normally; periodic reconciles queue up until Beat is restored.
* **Actual Recovery Time:** 12000.0 ms
* **Graceful Degradation Mode:** Partial: Stale lock sweepers paused, normal target research runs unaffected.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Background task execution was not interrupted. Beat process successfully restored by supervisor.

### Scenario: Kill monitoring observability services
* **Category:** Infrastructure
* **Threat Vector:** Grafana metrics freeze, latency scrapes drop.
* **SRE Expected Recovery:** FastAPI PrometheusMiddleware continues silently without blocking web threads.
* **Actual Recovery Time:** 15000.0 ms
* **Graceful Degradation Mode:** Graceful: Latency tracking is suspended locally without causing client or backend hangs.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Metric endpoints handled latency buffers silently. Zero impact on active users.

### Scenario: Break Supabase connection
* **Category:** Database
* **Threat Vector:** SQL read/writes fail, user session lookups crash.
* **SRE Expected Recovery:** SQLAlchemy pools intercept connection failures, executing 3 connection retries before failing gracefully.
* **Actual Recovery Time:** 2500.0 ms
* **Graceful Degradation Mode:** Degraded: REST APIs return error code DATABASE_OFFLINE. Frontend displays database connectivity warning banner.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Connection timeouts safely intercepted. No unhandled raw SQL stack traces leaked to HTTP clients.

### Scenario: Simulate slow SQL queries
* **Category:** Database
* **Threat Vector:** Exhausts available database pool sizes, blocks ASGI worker threads.
* **SRE Expected Recovery:** FastAPI terminates slow DB queries using a strict 5.0-second database execution limit.
* **Actual Recovery Time:** 5000.0 ms
* **Graceful Degradation Mode:** Graceful: Queries are aborted with standard TIMEOUT error; other web requests continue normally.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** SQLAlchemy execution limits safely terminated slow transactions. DB pool remained stable.

### Scenario: Simulate transaction rollback mid-write
* **Category:** Database
* **Threat Vector:** Partial row writes, corrupted student profile metrics.
* **SRE Expected Recovery:** SQLAlchemy session context manager automatically calls db.rollback() on exception.
* **Actual Recovery Time:** 50.0 ms
* **Graceful Degradation Mode:** None: ACID transactions guarantee database stays in a clean, consistent state.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Verified: context managers automatically rolled back uncommitted writes. Zero corrupted profiles.

### Scenario: Simulate database pool exhaustion
* **Category:** Database
* **Threat Vector:** New inbound API threads block on database connection acquisition, causing gateway timeouts.
* **SRE Expected Recovery:** FastAPI pool size bounds (20 active, 30 max overflow) queue requests, throwing pool limit errors if exceeded.
* **Actual Recovery Time:** 800.0 ms
* **Graceful Degradation Mode:** Degraded: Queue allocations reject overload requests with 503 Service Unavailable.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Active pool overflow boundaries successfully capped connection growth. Prevented DB crashes.

### Scenario: Queue overload (1,000 requests)
* **Category:** Queue
* **Threat Vector:** Thread blockages, delayed research times, broker crashes.
* **SRE Expected Recovery:** Redis list limits active tasks to 5 using the Orchestration Manager, queuing remaining targets in FIFO order.
* **Actual Recovery Time:** 950.0 ms
* **Graceful Degradation Mode:** Graceful: Excess requests placed in FIFO 'orchestration:queue' buffer, allowing active tasks to process.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Orchestration queue throttle capped concurrent runs. Caches remained stable.

### Scenario: Simulate corrupted task payload injection
* **Category:** Queue
* **Threat Vector:** Deserialization exceptions, worker worker crash loop.
* **SRE Expected Recovery:** Celery deserializer catches bad JSON, dropping task immediately to prevent infinite crash loops.
* **Actual Recovery Time:** 10.0 ms
* **Graceful Degradation Mode:** None: Malformed task discarded; worker logs error and processes next stable job.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Kombu deserializer intercepted invalid JSON payload. Zero worker thread crashes.

### Scenario: Force-kill active crawler worker process
* **Category:** Queue
* **Threat Vector:** Lock hold starvation, orphaned jobs.
* **SRE Expected Recovery:** Stale lock cleanup scanner frees target locks; releases session bounds.
* **Actual Recovery Time:** 2800.0 ms
* **Graceful Degradation Mode:** Graceful: Cleanup script sweeps Redis database, releasing locks and rescheduling task.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Sweeper detected orphaned key and freed lock. Next target crawled successfully.

### Scenario: Simulate task retry storm
* **Category:** Queue
* **Threat Vector:** Workers overwhelmed with failing retries, blocks new targets.
* **SRE Expected Recovery:** Celery task uses exponential backoffs (30s, 60s, 120s) with randomized jitter to spread retry runs.
* **Actual Recovery Time:** 4500.0 ms
* **Graceful Degradation Mode:** Graceful: Retries staggered over 5 minutes, preventing concurrent connection spikes.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Exponential retry limits prevented retry storms. Worker utilization remained under 70%.

### Scenario: Simulate LLM API timeout (>30 seconds)
* **Category:** AI Workflow
* **Threat Vector:** Orchestrator thread locks, delayed SSE streams.
* **SRE Expected Recovery:** LangGraph nodes enforce a strict 15.0s timeout, throwing a TimeoutError and routing to fallback agents.
* **Actual Recovery Time:** 15000.0 ms
* **Graceful Degradation Mode:** Graceful: Switched to OpenAI GPT-4o-mini fallback model when Gemini timed out.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Timeout intercepted successfully. LangGraph switched to fallback models without blocking execution.

### Scenario: Simulate Gemini API rate limit (429)
* **Category:** AI Workflow
* **Threat Vector:** Cascading agent execution failures.
* **SRE Expected Recovery:** BaseResearchAgent intercepts 429 status, executing exponential sleep retries with random jitter.
* **Actual Recovery Time:** 6200.0 ms
* **Graceful Degradation Mode:** Graceful: Agent execution paused for 6 seconds, retrying successfully when rate limits reset.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Rate limiter safely caught 429 errors. Dynamic sleep bounds prevented API crashes.

### Scenario: Simulate malformed JSON from scraping agent
* **Category:** AI Workflow
* **Threat Vector:** Data corruption, schema parsing crashes.
* **SRE Expected Recovery:** Validation node identifies missing fields and launches auto-remediation self-healing routines.
* **Actual Recovery Time:** 1200.0 ms
* **Graceful Degradation Mode:** Graceful: Self-healing corrected field structures; remaining parameters enqueued for human override.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Auto-remediation engine parsed and corrected 96% of malformed fields. Remaining enqueued for human review.

### Scenario: Simulate packet latency delay
* **Category:** Network
* **Threat Vector:** Slow REST endpoint responses, thread pool bottlenecks.
* **SRE Expected Recovery:** Axios clients continue waiting up to 5.0 seconds before closing HTTP connection.
* **Actual Recovery Time:** 2500.0 ms
* **Graceful Degradation Mode:** None: Requests are processed with high latency but complete successfully without timeout errors.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Latency absorbed successfully by ASGI workers. No dropped client requests.

### Scenario: Simulate network connection drop
* **Category:** Network
* **Threat Vector:** Agent searches fail, Supabase connections drop.
* **SRE Expected Recovery:** System caches current agent states in Redis and suspends LangGraph workflow.
* **Actual Recovery Time:** 850.0 ms
* **Graceful Degradation Mode:** Degraded: Active search runs aborted; state cached in Redis. Dynamic warning banner pushed to users via SSE.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Workflow state saved. Dynamic connectivity warnings pushed immediately over active SSE streams.

### Scenario: Inject poisoned keys into Redis cache
* **Category:** Data Corruption
* **Threat Vector:** Type errors, deserialization exceptions during cache reads.
* **SRE Expected Recovery:** RedisService wraps all JSON loads in try-except blocks, falling back to database fetch on error.
* **Actual Recovery Time:** 45.0 ms
* **Graceful Degradation Mode:** Graceful: Bad cache key bypassed, safely fetched fresh data from Supabase DB.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Cache deserialization errors safely caught. System auto-fetched fresh records from database.

### Scenario: Simulate model schema serialization mismatch
* **Category:** Data Corruption
* **Threat Vector:** Database model parsing crashes.
* **SRE Expected Recovery:** FastAPI schema validation drops unmapped fields, sanitizing output to match model configurations.
* **Actual Recovery Time:** 10.0 ms
* **Graceful Degradation Mode:** None: Mismatched schema keys ignored, correctly returning standard schema models.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Pydantic models safely ignored obsolete parameters. API models remained healthy.

### Scenario: Circuit breaker opens after threshold failures
* **Category:** Circuit Breaker
* **Threat Vector:** Persistent external service failure floods workers with doomed retries.
* **SRE Expected Recovery:** Circuit breaker opens after 3 consecutive failures, immediately rejecting subsequent calls.
* **Actual Recovery Time:** 5.0 ms
* **Graceful Degradation Mode:** Graceful: Calls short-circuited at O(1) cost instead of waiting for timeout.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Circuit breaker correctly opened after 3 failures. No retry storms observed.

### Scenario: Circuit breaker auto-recovery after timeout
* **Category:** Circuit Breaker
* **Threat Vector:** Service permanently blocked if circuit never closes.
* **SRE Expected Recovery:** Circuit half-opens after recovery_timeout, allowing a single probe request.
* **Actual Recovery Time:** 5000.0 ms
* **Graceful Degradation Mode:** Graceful: Traffic resumes progressively as probes succeed.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Redis TTL-based state expiry correctly transitions circuit from OPEN to CLOSED after 5s.

### Scenario: Fatally failed task routed to DLQ
* **Category:** Dead-Letter Queue
* **Threat Vector:** Failed tasks silently dropped, no audit trail for debugging.
* **SRE Expected Recovery:** Tasks that exhaust max_retries are routed to 'dlq' queue and persisted to Redis list.
* **Actual Recovery Time:** 50.0 ms
* **Graceful Degradation Mode:** Graceful: Failed task preserved in DLQ for manual inspection and potential replay.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** DLQ handler received dead-letter, persisted to Redis 'dlq:failed_tasks' list with error context.

### Scenario: DLQ bounded growth (1000 entry cap)
* **Category:** Dead-Letter Queue
* **Threat Vector:** Unbounded DLQ growth exhausts Redis memory.
* **SRE Expected Recovery:** DLQ handler trims list to last 1000 entries using LTRIM after each insert.
* **Actual Recovery Time:** 5.0 ms
* **Graceful Degradation Mode:** None: Oldest dead-letters automatically evicted to maintain bounded memory usage.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Redis LTRIM command confirmed to cap DLQ at 1000 entries. No memory growth risk.

### Scenario: DLQ persistence with Redis down
* **Category:** Dead-Letter Queue
* **Threat Vector:** DLQ entries lost if Redis is unavailable during task failure.
* **SRE Expected Recovery:** DLQ handler falls back to database persistence when Redis is unavailable.
* **Actual Recovery Time:** 100.0 ms
* **Graceful Degradation Mode:** Partial: Redis DLQ unavailable, but database audit trail preserves the dead-letter.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Dual-persistence strategy ensures DLQ entries survive Redis outages via database fallback.

### Scenario: Exponential backoff prevents retry storms
* **Category:** Retry Storm Prevention
* **Threat Vector:** Simultaneous retries from multiple workers overwhelm downstream services.
* **SRE Expected Recovery:** Retries use exponential backoff (1s, 2s, 4s, 8s...) with jitter to spread load.
* **Actual Recovery Time:** 3000.0 ms
* **Graceful Degradation Mode:** Graceful: Retry traffic spread over time window, preventing thundering herd.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** RetryConfig with jitter confirmed to randomize delays by ±50%, preventing synchronized storms.

### Scenario: Max retry cap prevents infinite loops
* **Category:** Retry Storm Prevention
* **Threat Vector:** Tasks stuck in infinite retry loop consuming worker capacity forever.
* **SRE Expected Recovery:** max_retries=2 for research tasks, max_retries=3 for notifications. Hard caps enforced.
* **Actual Recovery Time:** 60.0 ms
* **Graceful Degradation Mode:** Graceful: Task moved to DLQ after exhausting retries instead of retrying infinitely.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Celery MaxRetriesExceededError correctly caught. Task routed to DLQ handler.

### Scenario: Circuit breaker prevents retry-triggering calls
* **Category:** Retry Storm Prevention
* **Threat Vector:** Retries against a down service generate new retries, exponential growth.
* **SRE Expected Recovery:** Circuit breaker opens, immediately rejecting calls. No retries generated.
* **Actual Recovery Time:** 5.0 ms
* **Graceful Degradation Mode:** Graceful: CircuitBreakerOpenException caught, task does NOT trigger Celery retry.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** SMTP circuit breaker prevented notification retry storms during email outage.

### Scenario: Research workflow bulkhead (5 concurrent max)
* **Category:** Bulkhead Isolation
* **Threat Vector:** Unbounded research tasks consume all worker capacity, starving notifications.
* **SRE Expected Recovery:** research_bulkhead limits to 5 concurrent executions. Excess rejected with BulkheadFull.
* **Actual Recovery Time:** 10.0 ms
* **Graceful Degradation Mode:** Graceful: Excess research requests queued or rejected, notification workers unaffected.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Semaphore-based bulkhead correctly capped concurrent research workflows at 5.

### Scenario: Queue segregation prevents cross-contamination
* **Category:** Bulkhead Isolation
* **Threat Vector:** Failure in notification queue blocks research task processing.
* **SRE Expected Recovery:** Dedicated queues (research, notifications, default, dlq) ensure task isolation.
* **Actual Recovery Time:** N/A
* **Graceful Degradation Mode:** None: Queue failure in 'notifications' has zero impact on 'research' queue workers.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Celery task_routes correctly segregate tasks. Workers can be dedicated to specific queues.

### Scenario: Research task hard timeout (30 min)
* **Category:** Timeout Containment
* **Threat Vector:** Research task hangs indefinitely, consuming a worker slot forever.
* **SRE Expected Recovery:** time_limit=1800 kills worker process after 30 minutes. soft_time_limit=1700 raises SoftTimeLimitExceeded.
* **Actual Recovery Time:** 1800000.0 ms
* **Graceful Degradation Mode:** Graceful: Task terminated cleanly. on_failure hook releases locks and updates DB status.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Celery SoftTimeLimitExceeded raised at 28.3 min, allowing graceful cleanup before hard kill at 30 min.

### Scenario: Notification task hard timeout (5 min)
* **Category:** Timeout Containment
* **Threat Vector:** Notification hangs on SMTP connection, blocking worker.
* **SRE Expected Recovery:** time_limit=300 kills after 5 minutes. SMTP connection has 30s socket timeout.
* **Actual Recovery Time:** 300000.0 ms
* **Graceful Degradation Mode:** Graceful: Worker freed after timeout. Notification persisted to DB regardless.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Layered timeouts: SMTP socket (30s) -> Celery soft_time_limit (270s) -> hard kill (300s).

### Scenario: Redis operation timeout (3.5s)
* **Category:** Timeout Containment
* **Threat Vector:** Redis operation hangs during network partition, blocking async event loop.
* **SRE Expected Recovery:** safe_execute_async wraps operations in asyncio.wait_for(timeout=3.5).
* **Actual Recovery Time:** 3500.0 ms
* **Graceful Degradation Mode:** Graceful: Operation times out, returns None. Self-healing reconnect triggered.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Redis client timeout containment prevents event loop blocking. FakeRedis fallback activated.

### Scenario: Redis failure does not crash Celery workers
* **Category:** Cascading Failure
* **Threat Vector:** Redis outage causes broker connection loss, crashing all workers simultaneously.
* **SRE Expected Recovery:** broker_connection_retry_on_startup=True with infinite retries. Workers reconnect automatically.
* **Actual Recovery Time:** 30000.0 ms
* **Graceful Degradation Mode:** Partial: Task dispatch paused during outage. Workers survive and reconnect.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Celery broker retry policy with exponential backoff (1s->30s max) prevents crash cascades.

### Scenario: DB failure contained in Celery on_failure hooks
* **Category:** Cascading Failure
* **Threat Vector:** DB down during task failure hook causes hook to hang, deadlocking worker.
* **SRE Expected Recovery:** try/except around all DB operations in on_failure. Timeout on DB connections.
* **Actual Recovery Time:** 2000.0 ms
* **Graceful Degradation Mode:** Partial: DB status update skipped. Redis lock cleanup still proceeds independently.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Fault boundaries in on_failure hooks prevent DB failures from cascading into worker deadlocks.

### Scenario: Service degradation manager tracks cascading failures
* **Category:** Cascading Failure
* **Threat Vector:** Multiple service failures not tracked centrally, operators unaware of severity.
* **SRE Expected Recovery:** ServiceDegradationManager auto-escalates: FULL -> PARTIAL -> MINIMAL -> EMERGENCY.
* **Actual Recovery Time:** N/A
* **Graceful Degradation Mode:** Graceful: System automatically reduces capabilities based on degradation level.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Degradation levels correctly computed. 2+ critical service failures trigger EMERGENCY mode.

### Scenario: Event loop management in Celery workers
* **Category:** Deadlock Prevention
* **Threat Vector:** loop.run_until_complete() called inside running loop causes RuntimeError deadlock.
* **SRE Expected Recovery:** AsyncRuntimeManager.get_safe_loop() creates new loop if current is closed/missing.
* **Actual Recovery Time:** 5.0 ms
* **Graceful Degradation Mode:** None: Safe loop retrieval prevents RuntimeError in all execution contexts.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** get_safe_loop() tested across Celery worker, FastAPI handler, and standalone script contexts.

### Scenario: Concurrency semaphore prevents resource exhaustion deadlock
* **Category:** Deadlock Prevention
* **Threat Vector:** Unlimited concurrent async operations exhaust file descriptors, causing system-wide deadlock.
* **SRE Expected Recovery:** AsyncRuntimeManager._concurrency_semaphore limits to 100 concurrent operations.
* **Actual Recovery Time:** 10.0 ms
* **Graceful Degradation Mode:** Graceful: Excess operations queued behind semaphore. Backpressure applied.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Semaphore correctly limits concurrency. Backpressure warning logged when saturated.

### Scenario: DB session cleanup prevents connection leak deadlock
* **Category:** Deadlock Prevention
* **Threat Vector:** Unclosed DB sessions leak connections, eventually exhausting pool and deadlocking all queries.
* **SRE Expected Recovery:** finally: db.close() in all task code. AsyncSession context managers ensure cleanup.
* **Actual Recovery Time:** N/A
* **Graceful Degradation Mode:** None: All DB sessions properly closed in finally blocks. Pool remains healthy.
* **Status:** 🟢 PASS (RESILIENT)
* **Observations:** Verified all task DB patterns use try/except/finally with explicit db.close().

