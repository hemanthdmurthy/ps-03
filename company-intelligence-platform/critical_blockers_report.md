# Placement Intel Portal
## SRE Top Critical Blockers Report
**Date:** 2026-05-20 12:19:16

---

### Critical Blockers Summary

#### 1. [RCA-001] Synchronous Database Migration Lag blocks Uvicorn Gateway
* **Blocker Class:** Startup Blocker
* **Remediation Action:** Move 'reconcile_database_schema()' to a standalone pre-boot container script, decoupling migration dependencies from web server initializations.

#### 2. [RCA-002] Settings Key Configuration Mismatch Blocks Portal Access
* **Blocker Class:** Auth Blocker
* **Remediation Action:** Rename all references to settings.SECRET_KEY inside security and token helpers to reference settings.JWT_SECRET_KEY.
