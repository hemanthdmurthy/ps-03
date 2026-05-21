# Architecture Trace Map

## 1. Overview
This document serves as the foundational blueprint for injecting complete observability into the Placement Intelligence Platform. It outlines the architectural boundaries and interactions that must be instrumented to achieve full end-to-end distributed tracing.

## 2. Distributed Components and Boundaries
### FastAPI API Layer (Edge)
- **Framework**: FastAPI (asyncio)
- **Role**: Entry point for synchronous and asynchronous HTTP requests, WebSocket connections.
- **Trace Boundaries**:
  - Inbound HTTP Requests (REST APIs)
  - WebSocket Upgrade connections (Pub/Sub notifications)
  - LangServe integration endpoints (`/placement-agent`)
- **Key Middleware**: RequestTrackingMiddleware, RequestLoggingMiddleware, PrometheusMiddleware.

### Queue System (Celery Broker)
- **Framework**: Celery
- **Broker**: Redis
- **Role**: Dispatches and manages offline, long-running intelligence tasks (e.g., enrichment, scanning, notifications).
- **Trace Boundaries**:
  - Producer: Task enqueue events in FastAPI context.
  - Consumer: Task execution lifecycle in Celery worker context.
  - Retries & Dead-letter pathways.

### Redis Ecosystem (State & Cache)
- **Role**: Serves as the distributed cache, distributed lock manager (DLM), Pub/Sub message bus, and task broker.
- **Trace Boundaries**:
  - Redis Operations: GET/SET for caching.
  - Pub/Sub Channels: Broadcasting WebSocket events across nodes.
  - Lock Acquisition: Distributed locks for sync control.

### Database Layer (Persistence)
- **Framework**: SQLAlchemy (asyncpg) / PostgreSQL
- **Role**: Persistent data storage.
- **Trace Boundaries**:
  - Async DB Queries.
  - Connection pooling latency.

### Async Execution Runtimes (LangGraph)
- **Role**: Stateful multi-agent orchestrator.
- **Trace Boundaries**: LangGraph node transitions, model calls, and graph execution timelines.

## 3. Communication Flows and Trace Propagation
To achieve end-to-end visibility, trace context must be propagated across:
1. **HTTP -> DB**: FastAPI route -> SQLAlchemy session query.
2. **HTTP -> Cache/Lock**: FastAPI route -> Redis operation.
3. **HTTP -> Queue -> Worker**: FastAPI enqueues task -> Trace ID embedded in task payload -> Worker extracts and resumes trace.
4. **Worker -> DB/Cache**: Worker executes sub-tasks -> Traces database and cache interaction natively.

## 4. Identified Failure Points for Instrumentation
- Database connection timeouts and pool exhaustion.
- Celery worker crashes, `RuntimeError` due to conflicting async loops.
- Redis lock acquisition failures (wait timeouts).
- Unhandled API exceptions and 500s.
- Stale WebSocket connections and broadcast failures.
