# Retry Storm Prevention Report
## Distributed Async Backend Infrastructure
**Date:** 2026-05-20

---

### Executive Summary
Retry storms represent one of the most dangerous failure modes in distributed systems. A single failing downstream service can generate an exponential cascade of retry attempts that overwhelm the entire infrastructure. This report documents the comprehensive retry storm prevention mechanisms implemented.

---

### 1. Retry Caps (Hard Limits)

| Task | max_retries | Countdown Strategy | DLQ on Exhaustion |
| :--- | :--- | :--- | :--- |
| Research Workflow | 2 | Exponential (60s, 120s) | ✅ Yes |
| Notifications | 3 | Exponential (10s, 20s, 40s) | ✅ Yes |
| DLQ Handler | 0 | No retries | N/A |
| Stuck Task Sweeper | 0 | No retries | N/A |
| Heartbeat | 0 | No retries | N/A |

### 2. Exponential Backoff with Jitter

All retry mechanisms use the following formula:
```
delay = min(base_delay × 2^attempt, max_delay)
jitter = uniform(0.5 × delay, delay)
```

This ensures:
- **No synchronized retries**: Workers retry at different times
- **Bounded delays**: max_delay cap prevents unreasonable wait times
- **Progressive spacing**: Each retry waits longer than the last

### 3. Circuit Breaker Integration

The SMTP email dispatch is protected by a circuit breaker (`smtp_circuit_breaker`):
- **Threshold**: 5 consecutive failures → circuit OPENS
- **Recovery**: 120 seconds TTL in Redis → circuit auto-CLOSES
- **Effect**: When open, `CircuitBreakerOpenException` is caught WITHOUT triggering a Celery retry
- **Result**: Zero retry storms during sustained SMTP outages

### 4. Queue Isolation Prevents Cross-Domain Storms

```
research queue ─── Workers A ─── Research Tasks Only
notifications queue ─── Workers B ─── Notification Tasks Only
default queue ─── Workers C ─── Scheduled Tasks Only
dlq queue ─── Workers D ─── Dead Letter Processing Only
```

A retry storm in notifications cannot consume research worker capacity.

### 5. Redis Broker Retry Policy

```python
broker_transport_options = {
    "retry_policy": {
        "max_retries": None,      # Infinite (broker is critical)
        "interval_start": 1.0,    # Start at 1s
        "interval_step": 2.0,     # Double each attempt
        "interval_max": 30.0,     # Cap at 30s
    }
}
```

This prevents a broker reconnection thundering herd while ensuring eventual recovery.

### 6. Validation Results

| Test | Result |
| :--- | :--- |
| Exponential backoff jitter spread | ✅ PASS |
| Max retry cap enforcement | ✅ PASS |
| Circuit breaker prevents retry generation | ✅ PASS |
| DLQ routing after exhaustion | ✅ PASS |
| Queue isolation under storm | ✅ PASS |
