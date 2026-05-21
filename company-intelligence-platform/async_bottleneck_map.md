# Async Bottleneck Map

## 1. Database Operations
- **Current State**: Connection pool was undersized (20/30).
- **Bottleneck**: High concurrency queries would exhaust the connection pool, leading to queueing.
- **Optimization**: Increased pool size to 50 and max_overflow to 100 to support high burst workloads.

## 2. Redis Operations
- **Current State**: Single commands per operation.
- **Bottleneck**: Round-trip time (RTT) overhead for bulk operations.
- **Optimization**: Implemented Pipeline support in `ResilientRedisClient` to allow batched executions.

## 3. Celery Task Execution
- **Current State**: `worker_prefetch_multiplier` was 1.
- **Bottleneck**: Underutilization of worker bandwidth for fast-executing tasks.
- **Optimization**: Increased `worker_prefetch_multiplier` to 4, enabled memory limits (256MB), and tuned concurrency to 8 for pre-fork pool.

## 4. Async Execution Flow
- **Current State**: Unbounded coroutine execution.
- **Bottleneck**: Risk of memory exhaustion and event loop saturation.
- **Optimization**: Implemented a global concurrency semaphore (default 100) and adaptive timeouts to enforce backpressure.
