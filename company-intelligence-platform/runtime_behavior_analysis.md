# Placement Intel Platform
## Runtime Behavior Analysis — Autonomous Recovery Systems Engineering
**Date:** 2026-05-20
**Engineer:** Principal Autonomous Recovery Systems Engineer

---

## 1. Runtime Lifecycle Architecture

### 1.1 Process Topology
The platform runs as a distributed async system comprising:

| Process           | Technology        | Runtime Model           | Lifecycle Owner       |
| :---              | :---              | :---                    | :---                  |
| Web Gateway       | FastAPI + Uvicorn | ASGI async event loop   | Uvicorn process       |
| Celery Workers    | Celery 5.x        | Solo/prefork pool       | Celery worker daemon  |
| Celery Beat       | Celery 5.x        | Single-process scheduler| Celery beat daemon    |
| Redis Broker      | Redis 7 Alpine    | Single-threaded I/O     | Docker container      |
| PostgreSQL        | PostgreSQL 15     | Multi-process backend   | Docker container      |
| Prometheus        | Prometheus v2.45  | Scraper pull model      | Docker container      |
| Grafana           | Grafana 10.0      | Dashboard renderer      | Docker container      |

### 1.2 Async Execution Flow
```
[Client HTTP] → FastAPI ASGI → Middleware Chain → Route Handler
                                                      ↓
                                              [Celery .delay()]
                                                      ↓
                                          Redis Broker Queue (research/notifications/default/dlq)
                                                      ↓
                                          Celery Worker picks task
                                                      ↓
                                    AsyncRuntimeManager.get_safe_loop()
                                                      ↓
                                    loop.run_until_complete(workflow)
                                                      ↓
                                    LangGraph Multi-Agent Pipeline
                                                      ↓
                                    Redis State + DB Persistence
```

### 1.3 Event Loop Lifecycle Behavior
- **FastAPI context**: Running event loop managed by Uvicorn. All async code executes natively.
- **Celery worker context**: No running event loop in worker thread. `AsyncRuntimeManager.get_safe_loop()` creates new loop.
- **Celery Beat context**: Pure synchronous scheduler. No async execution.
- **Testing context**: May or may not have running loop depending on test runner.

---

## 2. Worker Instability Patterns Detected

### 2.1 OOM Worker Kills (SIGKILL)
- **Trigger**: Heavy AI crawling tasks exceeding `worker_max_memory_per_child=256MB`
- **Behavior**: OS kills worker process with SIGKILL; Python `try/finally` blocks do NOT execute
- **Consequence**: Redis mutex locks remain held for 30 minutes (full TTL)
- **Current mitigation**: `task_acks_late=True` allows redelivery, but lock starvation persists

### 2.2 Event Loop Thread Collisions
- **Trigger**: Calling `asyncio.get_event_loop()` inside synchronous Celery worker threads
- **Behavior**: `RuntimeError: There is no current event loop in thread`
- **Current mitigation**: `AsyncRuntimeManager.get_safe_loop()` provides fallback — **PARTIALLY ADDRESSED**
- **Gap**: Not all code paths route through `AsyncRuntimeManager`

### 2.3 Worker Prefetch Starvation
- **Trigger**: `worker_prefetch_multiplier=4` with `worker_concurrency=1` (solo pool)
- **Behavior**: Worker prefetches 4 tasks but can only process 1 at a time
- **Consequence**: Prefetched tasks block behind long-running research workflows (up to 30 min each)
- **Impact**: Task start latency increases dramatically under load

---

## 3. Queue Congestion Risks Detected

### 3.1 Research Queue Saturation
- **Orchestration limit**: 5 concurrent research workflows (`concurrency_limit=5`)
- **Overflow behavior**: Excess jobs enqueue to `orchestration:queue` Redis list
- **Gap**: No bounded queue size — unlimited growth risk under sustained load
- **Gap**: No queue age monitoring — stale queued jobs may never execute

### 3.2 DLQ Unbounded Growth
- **Current cap**: 1000 entries via `LTRIM` — **ADDRESSED**
- **Gap**: No alerting when DLQ approaches capacity
- **Gap**: No automatic DLQ replay or triage mechanism

### 3.3 Cross-Queue Interference
- **Queues**: `default`, `research`, `notifications`, `dlq`
- **Current isolation**: Task routing via `task_routes` — **ADDRESSED**
- **Gap**: All queues share the same Redis broker instance; Redis saturation affects all queues

---

## 4. Memory Growth Anomaly Patterns

### 4.1 Worker Memory Leaks
- **Guard**: `worker_max_memory_per_child=256000` triggers worker restart after 256MB
- **Guard**: `worker_max_tasks_per_child=1000` triggers restart after 1000 tasks
- **Gap**: No runtime memory monitoring between task executions
- **Gap**: No memory growth rate detection (slow leaks under threshold)

### 4.2 Redis Memory Growth
- **Risk**: Large JSON payloads stored as orchestration status/progress keys
- **Guard**: TTL of 3600s on status keys
- **Gap**: No monitoring of total Redis memory utilization
- **Gap**: No eviction policy enforcement for non-TTL keys

---

## 5. Hung Coroutine Patterns Detected

### 5.1 LangGraph Workflow Hangs
- **Timeout**: `task_time_limit=1800` (30 min hard) / `task_soft_time_limit=1700` (28.3 min soft)
- **Behavior**: `SoftTimeLimitExceeded` raised at 28.3 min for graceful cleanup
- **Gap**: No intermediate heartbeat or progress check during workflow execution
- **Gap**: No coroutine-level timeout enforcement within LangGraph node execution

### 5.2 Redis Operation Hangs
- **Guard**: `asyncio.wait_for(timeout=3.5)` in `safe_execute_async`
- **Gap**: Synchronous Redis operations (`safe_execute_sync`) have no timeout enforcement
- **Gap**: Reconnect attempts during hang can compound delays

---

## 6. Orphan Task Accumulation Detected

### 6.1 Post-Crash Orphan Tasks
- **Trigger**: Worker crash during task execution with `task_acks_late=True`
- **Behavior**: Task is redelivered to another worker, but original state artifacts remain
- **Gap**: No cleanup of intermediate state (Redis keys, partial DB writes) from crashed run
- **Gap**: No deduplication check — redelivered task may create duplicate results

### 6.2 Stuck Task Sweeper Gaps
- **Current**: `stuck_task_sweeper` runs every 300s, checks task runtime vs 90% of `time_limit`
- **Gap**: Only logs warnings — does not revoke or terminate stuck tasks
- **Gap**: Does not clean up Redis locks for identified stuck tasks
- **Gap**: Does not integrate with `TaskQuarantine` system

---

## 7. Runtime Recovery Gaps Summary

| Gap ID  | Description                                              | Severity |
| :---    | :---                                                     | :---     |
| RG-001  | No worker auto-resurrection after crash                  | HIGH     |
| RG-002  | No runtime health scoring system                         | HIGH     |
| RG-003  | Stuck task sweeper is passive (log-only)                 | HIGH     |
| RG-004  | No orphan coroutine detection and cleanup                | MEDIUM   |
| RG-005  | No predictive failure detection (memory/CPU trending)    | MEDIUM   |
| RG-006  | No adaptive queue rebalancing under load                 | MEDIUM   |
| RG-007  | No autonomous stabilization feedback loop                | HIGH     |
| RG-008  | No runtime watchdog supervisor process                   | HIGH     |
| RG-009  | No heartbeat-based lock renewal during task execution    | HIGH     |
| RG-010  | No recovery circuit breaker (infinite recovery loops)    | CRITICAL |
