# Queue Metrics Report

## Overview
Celery represents a critical asynchronous boundary that can often obscure execution delays. Our new observability stack ensures transparent queue processing metrics.

## Metrics Exposed
- **Throughput**: Measured via `celery_tasks_total`, providing high-level counts of successes and failures per task type.
- **Processing Time**: Histogram `celery_task_duration_seconds` tracks actual execution latency in the worker, helping detect task starvation or slow external APIs.
- **Trace Propagation**: When an HTTP request causes a task enqueue, the Celery `delay()` method is wrapped by OpenTelemetry. The AMQP/Redis payload incorporates traceparent headers, ensuring Jaeger builds a continuous timeline.

## Alerts to Configure
- High failure rate in `celery_tasks_total`.
- Task duration exceeding 300s (5 minutes) for standard intelligence gathering.
