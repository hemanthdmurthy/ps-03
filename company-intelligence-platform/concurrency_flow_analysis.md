# Concurrency Flow Analysis

## Flow 1: FastAPI Async Request Cycle
- **Path**: Client -> FastAPI Route -> AsyncService -> Redis/DB.
- **Concurrency Risks**: Database connection pool exhaustion and memory spikes on unbounded traffic.
- **Mitigation**: Async concurrency semaphore in `AsyncRuntimeManager` ensures the loop sheds load before crashing. DB pool size increased.

## Flow 2: Celery Background Processing
- **Path**: Redis Broker -> Celery Worker -> Synchronous/Async execution.
- **Concurrency Risks**: Memory leaks from long-running workers, starvation from blocked tasks.
- **Mitigation**: Added `worker_max_tasks_per_child=1000` and `worker_max_memory_per_child=256000`. Prefetch multiplier increased to 4 to reduce idle time.

## Flow 3: Redis Distributed Locks
- **Path**: Worker -> RedisService -> Redis Lock.
- **Concurrency Risks**: Deadlocks, lock contention.
- **Mitigation**: Retained Lua script atomic releases, and exposed pipelines to allow batch acquisition if needed in the future.
