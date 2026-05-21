# Bottleneck Detection Report

## Detected Bottlenecks & Fixes

1. **DB Connection Limits**
   - *Issue*: `pool_size=20` insufficient for high throughput.
   - *Fix*: Increased to 50/100 overflow.

2. **Celery Worker Idleness**
   - *Issue*: `prefetch_multiplier=1` caused network wait states.
   - *Fix*: Increased to 4.

3. **Memory Bloat**
   - *Issue*: Unbounded Celery child processes.
   - *Fix*: Memory guards implemented.

4. **Async Saturation**
   - *Issue*: Unbounded `asyncio.create_task`.
   - *Fix*: Semaphore backpressure.
