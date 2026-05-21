# Placement Intel Portal
## Chaos Engineering: Failure Propagation Report
**Date:** 2026-05-20 13:07:07

---

### Systemic Failure Cascade Vectors

```mermaid
graph TD
    classDef trigger fill:#fee2e2,stroke:#ef4444,stroke-width:2px;
    classDef cascade fill:#ffedd5,stroke:#ea580c,stroke-width:2px;
    classDef barrier fill:#dcfce7,stroke:#22c55e,stroke-width:2px;

    T_RED[Redis Outage]:::trigger --> P_CEL[Celery connection drops]:::cascade
    T_RED --> P_SSE[SSE Pub/Sub halts]:::cascade
    P_CEL --> B_FAIL[Celery Task on_failure triggers]:::barrier
    B_FAIL --> S_LOCK[Self-Healing lock release completes]:::barrier

    T_DB[Supabase DB Drop]:::trigger --> P_SQL[SQL query timeouts]:::cascade
    P_SQL --> B_POOL[SQLAlchemy Pool overflow limits]:::barrier
    B_POOL --> S_ERR[FastAPI central exception filters return 503]:::barrier
```

### Critical Propagation Nodes
1. **The Redis Mutex Core**: Redis is both our message broker and state lock holder. If Redis fails, a lock cleanup cascade is automatically triggered to prevent task starvation once connection is restored.
2. **PostgreSQL Database Pool**: High latency queries cascade into SQLAlchemy connection exhaustions. Pool overflows act as a protective barrier, rejecting excess requests to prevent database crashes.
3. **LLM Rate-Limit Threshold**: Inbound agent surges cascade into Gemini/OpenAI rate-limiting 429s. BaseResearchAgent wrappers successfully absorb these spikes using exponential retry jitter backoffs.
