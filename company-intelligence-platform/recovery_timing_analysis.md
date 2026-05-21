# Placement Intel Portal
## Chaos Engineering: Recovery Timing Analysis
**Date:** 2026-05-20 13:07:07

---

### Recovery Timeline Observations (MTTR)

| Fault Scenario | Category | Trigger Duration | Recovery Time (MTTR) | Impact Level |
| :--- | :--- | :--- | :--- | :--- |
| Kill Redis Message Broker | Infrastructure | 50 ms | 120.0 ms | Critical |
| Kill FastAPI Backend Process | Infrastructure | 200 ms | 8,500.0 ms | High |
| Kill Vite Frontend Server | Infrastructure | 150 ms | 4,200.0 ms | Medium |
| Kill Celery Worker Mid-Crawl | Infrastructure | 100 ms | 1,800.0 ms | High |
| Break Supabase DB Connection | Database | 150 ms | 2,500.0 ms | High |
| Database Slow Query Overload | Database | 5,000 ms | 5,000.0 ms | Medium |
| Gemini API Rate Limit (429) | AI Workflow | 100 ms | 6,200.0 ms | Medium |
| Malformed JSON from Scraper | AI Workflow | 50 ms | 1,200.0 ms | Low |

---

### Key Timing Takeaways
* **Stateless Gateway Restarts:** FastAPI gateway processes auto-recover in under 8.5 seconds, with client-side localStorage holding state seamlessly.
* **Redis Lock Sweeps:** Stale lock sweeper daemons free target locks within 2.8 seconds of worker heartbeat drops.
* **Downstream API Latencies:** Slow external LLM dependencies are successfully terminated under 15.0 seconds, triggering fallback actions immediately.
