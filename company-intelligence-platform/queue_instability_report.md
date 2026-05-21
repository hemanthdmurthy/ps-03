# Placement Intel Portal
## SRE Queue Instability Report
**Date:** 2026-05-20 12:19:16

---

### Queue Instability Analysis

* **OOM worker terminations**: Forced process terminations by SRE kills or OS memory OOM sweeps bypass try/finally code blocks and Celery cleanups, leaving active Redis mutex keys locked in the registry.
* **Retry Storm Vectors**: Task failures trigger consecutive retries. If not staggered, these retry runs block worker thread pools, starving new search targets.
* **Worker Concurrency Blockages**: Windows process fork pools default to sub-process forking, causing Celery thread crashes. Windows environments must restrict workers to solo thread pool pools (`--pool=solo`).
