# Placement Intel Platform
## Autonomous Recovery Gap Analysis
**Date:** 2026-05-20
**Engineer:** Principal Autonomous Recovery Systems Engineer

---

## Executive Summary

The platform demonstrates **strong foundational resilience** (97.6% reliability score) with circuit breakers, retry policies, bulkhead isolation, and DLQ routing already implemented. However, the system lacks **autonomous self-healing intelligence** — the ability to detect anomalies, predict failures, and automatically recover without human intervention.

This gap analysis identifies 10 critical recovery gaps and prescribes the autonomous systems required to close them.

---

## Gap Matrix

| Gap ID | Category                   | Current State                                    | Required State                                                | Priority |
| :---   | :---                       | :---                                             | :---                                                          | :---     |
| RG-001 | Worker Recovery            | Manual restart required after crash              | Auto-detection + resurrection within 30s                      | P0       |
| RG-002 | Health Scoring             | No health scoring system                         | Composite health score from 8+ signals                        | P0       |
| RG-003 | Stuck Task Recovery        | Passive logging only                             | Active revocation + lock cleanup + DLQ routing                | P0       |
| RG-004 | Orphan Coroutine Recovery  | Basic `cleanup_orphaned_tasks` exists             | Proactive detection + graceful cancellation + state cleanup   | P1       |
| RG-005 | Predictive Failure         | No trending analysis                             | Memory/CPU/queue depth trending with EWA anomaly detection    | P1       |
| RG-006 | Queue Rebalancing          | Static concurrency limits                        | Adaptive concurrency based on worker health and queue depth   | P1       |
| RG-007 | Stabilization Loop         | No feedback loop                                 | Continuous monitor → detect → act → verify cycle              | P0       |
| RG-008 | Watchdog Supervisor        | No supervisor process                            | Dedicated watchdog monitoring all runtime components          | P0       |
| RG-009 | Heartbeat Lock Renewal     | Static 30-min TTL locks                          | Dynamic heartbeat renewal every 60s with 5-min TTL            | P0       |
| RG-010 | Recovery Safeguards        | No recovery circuit breaker                      | Max recovery attempts + cooldown + escalation policies        | P0       |

---

## Detailed Gap Analysis

### RG-001: Worker Auto-Recovery
**Current**: Workers crash and rely on Docker `restart: always` or manual intervention.
**Gap**: No application-level detection of worker death. No intelligent restart with state cleanup.
**Impact**: 8.5s average recovery time for backend; Celery workers may leave orphaned state.
**Required**: Heartbeat monitoring system that detects worker death within 10s and triggers:
  1. Redis lock cleanup for the dead worker's active tasks
  2. Task requeue or DLQ routing
  3. Worker restart signal
  4. Health score update

### RG-002: Runtime Health Scoring
**Current**: No composite health score. Individual metrics exist but are not aggregated.
**Gap**: Cannot make autonomous decisions without a unified health signal.
**Required**: Health scoring engine computing weighted composite from:
  - Worker availability (weight: 0.20)
  - Redis connectivity (weight: 0.15)
  - Database connectivity (weight: 0.15)
  - Queue depth/throughput ratio (weight: 0.15)
  - Memory utilization trend (weight: 0.10)
  - Task success rate (weight: 0.10)
  - Active error rate (weight: 0.10)
  - Response latency P95 (weight: 0.05)

### RG-003: Stuck Task Recovery (Active)
**Current**: `stuck_task_sweeper` identifies stuck tasks but only logs warnings.
**Gap**: No remediation action taken. Stuck tasks consume worker slots indefinitely.
**Required**: Active recovery pipeline:
  1. Detect task running > 90% of `time_limit`
  2. Send `SoftTimeLimitExceeded` signal
  3. If still running after grace period → revoke task
  4. Clean up Redis locks for affected company
  5. Route task metadata to DLQ
  6. Update database session status to `failed`
  7. Record in `TaskQuarantine`

### RG-004: Orphan Coroutine Recovery
**Current**: `AsyncRuntimeManager.cleanup_orphaned_tasks()` exists but is never called automatically.
**Gap**: Orphan coroutines accumulate during event loop errors or ungraceful shutdowns.
**Required**: Periodic orphan coroutine scanner that:
  1. Enumerates all tasks in active event loops
  2. Identifies tasks without parent references or exceeding max lifetime
  3. Gracefully cancels with `CancelledError`
  4. Logs cancellation metadata for debugging

### RG-005: Predictive Failure Detection
**Current**: No trending or anomaly detection.
**Gap**: Failures are only detected after they occur.
**Required**: Exponentially Weighted Average (EWA) anomaly detector tracking:
  - Memory utilization rate of change
  - Queue depth growth velocity
  - Error rate acceleration
  - Task duration drift
  Triggers preemptive alerts when metrics exceed 2σ from rolling baseline.

### RG-006: Adaptive Queue Rebalancing
**Current**: Static `concurrency_limit=5` for research workflows.
**Gap**: No adaptation to runtime conditions (healthy workers, queue pressure).
**Required**: Adaptive concurrency controller that:
  - Increases concurrency when health score > 0.85 and queue depth > threshold
  - Decreases concurrency when health score < 0.60 or error rate spikes
  - Enforces hard floor (1) and ceiling (10) bounds

### RG-007: Autonomous Stabilization Loop
**Current**: No continuous feedback loop.
**Gap**: Recovery actions are one-shot; no verification that recovery succeeded.
**Required**: Continuous stabilization cycle:
  ```
  MONITOR → DETECT → DIAGNOSE → ACT → VERIFY → MONITOR
  ```
  With state machine transitions and audit logging.

### RG-008: Watchdog Supervisor
**Current**: No dedicated supervisor process.
**Gap**: No single authority coordinating all recovery systems.
**Required**: Watchdog supervisor that:
  - Runs as a periodic Celery Beat task (every 30s)
  - Aggregates health signals from all subsystems
  - Triggers appropriate recovery actions based on health score thresholds
  - Enforces recovery rate limiting (max 3 recoveries per 5 minutes)
  - Escalates to emergency degradation mode when recovery fails

### RG-009: Heartbeat Lock Renewal
**Current**: Locks acquired with static 1800s (30 min) TTL.
**Gap**: If worker dies, lock blocks for full TTL duration.
**Required**: Dynamic heartbeat system:
  - Acquire lock with 300s (5 min) TTL
  - Worker sends heartbeat every 60s extending TTL by 300s
  - If worker dies, lock auto-expires in ≤5 min instead of 30 min
  - Background thread in worker handles heartbeat renewal

### RG-010: Recovery Circuit Breaker
**Current**: No safeguard against infinite recovery loops.
**Gap**: A flapping service could trigger unlimited recovery attempts.
**Required**: Recovery policy with:
  - Max 3 recovery attempts per component per 5-minute window
  - Exponential cooldown between recovery attempts (30s, 60s, 120s)
  - Escalation to degradation mode after max attempts exhausted
  - Manual override capability for operators

---

## Implementation Priority Order

1. **P0 (Immediate)**: RG-010 → RG-002 → RG-008 → RG-009 → RG-003 → RG-001 → RG-007
2. **P1 (Short-term)**: RG-004 → RG-005 → RG-006

> [!IMPORTANT]
> Recovery safeguards (RG-010) must be implemented FIRST to prevent the recovery systems themselves from causing instability.
