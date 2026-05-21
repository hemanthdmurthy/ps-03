# Queue Throughput Report

## Celery Broker
- Broker: Redis.
- Prefetch Multiplier: Updated from 1 to 4. This allows workers to pull small batches of tasks, reducing network RTT back to Redis.

## Saturation Prevention
- Memory limits ensure that queue floods do not bloat worker memory.
- Worker rotation (1000 tasks max) guarantees clean state during high-volume queue draining.
