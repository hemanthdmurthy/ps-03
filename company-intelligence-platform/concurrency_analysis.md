# Concurrency Analysis

## Worker Concurrency
- `solo` pool on Windows.
- `prefork` pool on Linux with `worker_concurrency=8` dynamically tuned.
- Hard limits on memory usage per child to avoid OOM killer terminations.

## Async Event Loop
- Bounded to `max_concurrency=100` via Semaphore.
- Prevents resource exhaustion attacks.
- Tasks beyond the limit will block at the semaphore, gracefully queuing or timing out depending on implementation.
