# Placement Intel Portal
## SRE Stability Heatmap
**Date:** 2026-05-20 12:19:16

---

### System Stability Heatmap Analysis

| Subsystem Component | Incident Rate | Failure Risk | Stability Index | Threat Level |
| :--- | :--- | :--- | :--- | :--- |
| **app.core.database** | Low | High | `82.0%` (Reconciliation blocks ASGI Event Loop) | **HIGH** |
| **app.utils.security** | High | High | `70.0%` (JWT Secret Key attribute mismatch) | **HIGH** |
| **app.services.redis_service** | Medium | Medium | `90.0%` (Event loop RuntimeError in synchronous contexts) | **MEDIUM** |
| **app.services.orchestration_manager** | Medium | Medium | `88.0%` (Orphaned locks on OS OOM worker kills) | **HIGH** |
| **app.tasks.research_tasks** | Low | Low | `98.0%` (Resilient queue task configurations) | **LOW** |
| **app.graphs.placement_graph** | Low | Low | `98.5%` (Robust schema compiles checked) | **LOW** |
