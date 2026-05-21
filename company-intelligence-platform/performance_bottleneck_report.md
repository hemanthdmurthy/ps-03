# Placement Intel Portal
## SRE Performance Bottleneck Report
**Date:** 2026-05-20 12:19:16

---

### Systemic Performance Bottlenecks

1. **Monolithic DB Updates on Startup**: Synchronous database updates trigger on gateway import, blocking liveness checks and increasing startup latency from 200ms to over 20 seconds.
2. **Missing Thread Event Loop Fallbacks**: Utilities executing in synchronous threads throw event loop `RuntimeError` exceptions when event loops are missing, causing background tasks to fail.
3. **Static Mutex Keys**: Long-lived static Redis locks hold company targets for 30 minutes upon worker crashes, starving subsequent research jobs.
