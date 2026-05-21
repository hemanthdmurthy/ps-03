# Tracing Architecture

## Distributed Trace Context
We rely on the standard W3C Trace Context (traceparent and tracestate headers) for context propagation.

## Components Instrumented
- **FastAPI**: `opentelemetry-instrumentation-fastapi`. Captures all HTTP inbound logic.
- **SQLAlchemy**: `opentelemetry-instrumentation-sqlalchemy`. Instruments engine queries directly.
- **Redis**: `opentelemetry-instrumentation-redis`. Tracks SET, GET, and cache hits/misses.
- **Celery**: `opentelemetry-instrumentation-celery`. Handles distributed context propagation via message headers.

## Exporters
- Traces are exported over gRPC to `localhost:4317` using `OTLPSpanExporter`.
- Tested and compatible with Jaeger, Datadog, Honeycomb, and New Relic.
