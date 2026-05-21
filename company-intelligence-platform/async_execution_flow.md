# Async Execution Flow Analysis

## 1. Overview
This report maps the end-to-end asynchronous execution pathways within the Placement Intelligence Platform to ensure observability tools can accurately track the lifespan of coroutines, thread pools, and multi-process workers.

## 2. Core Execution Environments
- **Uvicorn/FastAPI Loop**: The primary event loop for handling inbound API requests, executing dependency injection (DB sessions), and managing async route handlers.
- **Celery Worker Pool**: Synchronous wrapper around asynchronous operations via `AsyncRuntimeManager`, isolating the execution to prevent `RuntimeError`.
- **WebSocket Manager Loop**: Maintains long-lived async connections and background tasks for heartbeat pruning.
- **Redis Pub/Sub Listener Loop**: Dedicated async task for intercepting and broadcasting distributed state changes.

## 3. Async Boundaries & Hand-offs
Tracing these hand-offs is critical to prevent broken traces (lost correlation IDs).
1. **API Request -> Background Task (FastAPI)**: Handled within the same memory space, but executing after the primary response is returned. The trace must span across `BackgroundTasks`.
2. **API Request -> Queue (Celery)**: 
   - A synchronous dispatch `delay()` or `apply_async()` over AMQP/Redis.
   - Trace context (OpenTelemetry Context/Correlation ID) must be injected into the Celery message headers.
3. **Celery Worker -> Async Task**:
   - The worker runs synchronously but invokes an `AsyncRuntimeManager.run_async(...)`.
   - The trace context must be extracted from the headers and used to start a new span or link to the parent span before entering the asyncio event loop.
4. **WebSockets -> Pub/Sub**:
   - Connection established -> Trace initialized.
   - Pub/Sub event broadcast -> Trace propagates across instances.

## 4. Risks & Challenges for Tracing
- **ContextVars Leakage**: Context propagation in Python depends heavily on `contextvars`. Transitioning from thread pools (Celery) to async loops (LangGraph) can lose context if not explicitly propagated.
- **Event Loop Blocking**: Any synchronous instrumentation (e.g., blocking HTTP exports of traces/metrics) inside the main event loop will degrade performance. OTLP exporter must use background threads or async batch processors.
- **Celery Heartbeats**: Background recovery tasks require dedicated spans that are not linked to a specific user request, but rather to the worker's operational lifecycle.

## 5. Instrumentation Strategy
- Use `opentelemetry-instrumentation-fastapi` for automatic API span generation.
- Use `opentelemetry-instrumentation-celery` to inject and extract context from message headers automatically.
- Use `opentelemetry-instrumentation-redis` for cache insights.
- Use `opentelemetry-instrumentation-sqlalchemy` to catch `asyncpg` queries via standard engine hooks.
