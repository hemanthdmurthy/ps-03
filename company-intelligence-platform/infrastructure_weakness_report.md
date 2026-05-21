# Placement Intel Portal
## SRE Infrastructure Weakness Report
**Date:** 2026-05-20 12:18:28

---

### Infrastructure Vulnerabilities

1. **Unprotected Synchronous API Startups**: FastAPI gateway containers will hang during startup if Supabase PG connections experience network lag.
2. **Missing Out-of-Memory (OOM) Protection**: Sudden container terminates leave orphaned lock keys in the Redis registry, blocking corporate research runs.
3. **Missing Metrics Scraping Outage Safeguards**: The observability stack (Prometheus / Grafana) drops stats silently upon node outages without pushing alerts to SRE teams.

---

### Infrastructure Recommendations
* **Pre-Boot Migrations**: Implement a strict pre-boot entrypoint rule in all backend container Dockerfiles.
* **OOM Caps**: Set soft/hard limits for Celery worker container resource bounds to prevent OS kills.
