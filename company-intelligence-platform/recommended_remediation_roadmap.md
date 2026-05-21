# Placement Intel Portal
## Recommended Remediation Roadmap
**Date:** 2026-05-20 12:20:25

---

### Phase 1: Immediate Fixes (Next 24 Hours)
* **Auth Fix:** Perform a global find-and-replace for `settings.SECRET_KEY` to `settings.JWT_SECRET_KEY` in `app.utils.security` and authentication routers.
* **Pre-Boot Migrations:** Extract `reconcile_database_schema()` from the application base import files and execute it inside a standalone Shell entrypoint before starting Uvicorn.

### Phase 2: Short-Term Fixes (Next 3 Days)
* **Async Fallbacks:** Wrap `asyncio.run()` checks inside `try...except RuntimeError` blocks in `RedisService` and `database.py` helpers, explicitly instantiating `asyncio.new_event_loop()` upon exceptions.
* **Worker Pools:** Enforce the `--pool=solo` flag on all Windows Celery deployments.

### Phase 3: Mid-Term Stabilization (Next 2 Weeks)
* **Dynamic Lock Heartbeats:** Reduce Redis static TTLs from 30 minutes to 5 minutes. Implement a background thread in the Celery worker that executes an `EXPIRE` Lua script every 60 seconds to renew the lease.
* **OOM Limits:** Enforce strict Docker Compose memory limits (`mem_limit: 1g`) on worker containers to proactively manage memory ceilings.

### Phase 4: Long-Term Architectural Improvements (Next 3 Months)
* **Complete Async Transition:** Transition all background task frameworks away from standard synchronous Celery to an async-native background worker (like ARQ or SAQ) to unify the async event loop context across web gateways and background jobs.
* **Telemetry Streaming:** Upgrade Prometheus metrics to push metrics via OpenTelemetry standard forwarders to prevent observability drops on container death.
