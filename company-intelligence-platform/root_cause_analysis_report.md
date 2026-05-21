# Placement Intel Portal
## SRE Root Cause Analysis (RCA) Report
**Date:** 2026-05-20 12:18:28
**Lead Architect:** Principal Debugging Expert & Reliability Analyst

---

### Executive Vulnerability Summary
This document analyzes the exact root causes, trigger conditions, failure propagation chains, and recommended mitigations for all core failures discovered in the Placement Intel Portal system.

### [RCA-001] Synchronous Database Schema Reconciliation Blocks ASGI Event Loop
* **Severity:** HIGH | **Category:** Architectural / Startup
* **Exact Root Cause:** The backend's main database module executes the synchronous function 'reconcile_database_schema' inside imports or the FastAPI 'startup' event sequence, blocking the single active ASGI event loop thread.
* **Trigger Conditions:** Alembic migrations or database startup connection lag during container scaling.
* **Affected Modules:** `app.core.database, app.main`
* **Failure Propagation:** Database connection lag -> Blocks import or startup thread -> Uvicorn cannot process liveness check pings -> Docker/Kubernetes container health probes fail -> Rolling deployment rollback loop.

#### SRE Impact Assessment:
* **Infrastructure Impact:** Failed container health checks and rolling rollbacks.
* **API Impact:** FastAPI gateway cannot process any HTTP client queries during startup.
* **Performance Impact:** Startup latency spikes from 200ms to over 20 seconds.

#### Diagnostic Steps & Correction Plan:
* **Reproduction Steps:**
  1. Configure a temporary database connection timeout in settings.
  2. Shutdown or add a 15-second latency delay to the PostgreSQL container.
  3. Execute 'python backend/app/main.py' to boot the backend gateway.
  4. Observe that the Uvicorn web server hangs, refusing any incoming liveness TCP probes.
* **Expected Behavior:** Database schema updates run in an isolated pre-boot migration job, allowing the FastAPI web gateway to boot instantly and return status checks immediately.
* **Actual Behavior:** Uvicorn locks and blocks all incoming connections until the synchronous database socket timeout expires.
* **Recommended Fix:** `Extract 'reconcile_database_schema()' out of application imports. Run it inside a separate pre-boot container entrypoint script before booting Uvicorn.`
* **Prevention Strategy:** Enforce strict linting rules blocking the import or synchronous execution of IO-bound operations in backend routing frameworks.
* **SRE Monitoring Recommendation:** Track container startup timings and set alerting policies in Prometheus if Uvicorn boot takes >5 seconds.

---

### [RCA-002] Settings Configuration Attribute Mismatch ('SECRET_KEY' vs 'JWT_SECRET_KEY')
* **Severity:** MEDIUM | **Category:** Configuration / Security
* **Exact Root Cause:** Helper utility modules or test scripts reference 'settings.SECRET_KEY' for token signing and validation, while the core Pydantic 'Settings' model defines the parameter as 'JWT_SECRET_KEY'.
* **Trigger Conditions:** Attempting stateless JWT generation, validation, or login signature audits.
* **Affected Modules:** `app.utils.security, validation_suite, run_smoke_tests`
* **Failure Propagation:** REST user login POST request -> Calls security module -> References missing SECRET_KEY attribute -> Throws AttributeError exception -> Returns HTTP 500 error envelope to frontend login page.

#### SRE Impact Assessment:
* **Infrastructure Impact:** None.
* **API Impact:** Stateless login router fails, rendering bearer authentication offline.
* **Performance Impact:** None.

#### Diagnostic Steps & Correction Plan:
* **Reproduction Steps:**
  1. Open a terminal and run the smoke testing suite or launch a login unit test.
  2. Access the login REST endpoint: POST /api/v1/auth/login.
  3. Observe an HTTP 500 response containing an AttributeError exception regarding settings.SECRET_KEY.
* **Expected Behavior:** All security, validation, and auth libraries reference settings.JWT_SECRET_KEY to verify access tokens.
* **Actual Behavior:** Attribute error crash prevents user session creations.
* **Recommended Fix:** `Update all instances referencing 'settings.SECRET_KEY' to use 'settings.JWT_SECRET_KEY' as configured in config.py.`
* **Prevention Strategy:** Add static Pydantic verification hooks to config initializers to enforce property name consistency.
* **SRE Monitoring Recommendation:** Alert SRE teams if auth endpoints return sudden bursts of HTTP 500 errors.

---

### [RCA-003] Thread Collision and Event Loop Failures on Synchronous Contexts
* **Severity:** MEDIUM | **Category:** Async / Concurrency
* **Exact Root Cause:** Calling 'asyncio.get_event_loop()' inside utility modules executing in synchronous threads (such as Celery worker solo pools or testing runners) raises a 'RuntimeError' in Python 3.10+ if no active loop is registered in that specific thread.
* **Trigger Conditions:** Running Redis lock sweeps or PostgreSQL CRUD operations within synchronous test suites or Celery task processes.
* **Affected Modules:** `app.services.redis_service, app.core.database, run_smoke_tests`
* **Failure Propagation:** Celery worker executes task -> Invokes Redis get/set lock helper -> Calls get_event_loop() -> Throws 'RuntimeError: There is no current event loop in thread' -> Task terminates immediately as failed.

#### SRE Impact Assessment:
* **Infrastructure Impact:** Workers repeatedly crash or mark jobs as failed.
* **API Impact:** None.
* **Performance Impact:** Redis caching and locks are bypassed, causing data latency.

#### Diagnostic Steps & Correction Plan:
* **Reproduction Steps:**
  1. Execute an async-dependent database or Redis query from a synchronous test runner.
  2. Use asyncio.get_event_loop().run_until_complete() without prior loop setups.
  3. Observe a RuntimeError crash regarding missing event loops in the MainThread.
* **Expected Behavior:** Utilities dynamically detect active event loops, safely spinning up new event loop sessions using asyncio.new_event_loop() if needed.
* **Actual Behavior:** RuntimeError exception interrupts task and db execution pipelines.
* **Recommended Fix:** `Implement robust fallback loops using a try-except block wrapping 'asyncio.run()' and falling back to 'asyncio.new_event_loop()' on failure.`
* **Prevention Strategy:** Avoid mixing synchronous frameworks (like standard Celery) with pure async operations without thread-safe event loop wrappers.
* **SRE Monitoring Recommendation:** Configure logging parsers to trace 'RuntimeError' errors in SRE log aggregations.

---

### [RCA-004] Orphaned Mutex Locks on Out-of-Memory (OOM) Worker Kills
* **Severity:** HIGH | **Category:** Cache / Queues
* **Exact Root Cause:** Sudden worker kills (e.g. by OS OOM sweepers) prevent Python from executing 'try/except/finally' blocks or Celery task recovery callbacks, leaving active Redis mutex keys locked for 30 minutes.
* **Trigger Conditions:** Celery workers processing heavy AI target crawls exceeding memory capacity bounds.
* **Affected Modules:** `app.services.orchestration_manager, app.services.redis_service`
* **Failure Propagation:** Worker killed by OS -> Redis lock key remains active -> Next company research request enqueued -> Orchestrator blocks because lock is held -> System hangs for 30 minutes.

#### SRE Impact Assessment:
* **Infrastructure Impact:** Container OOM restarts.
* **API Impact:** None.
* **Performance Impact:** None.

#### Diagnostic Steps & Correction Plan:
* **Reproduction Steps:**
  1. Initiate a deep corporate target research query.
  2. Forcefully kill the active Celery worker process using OS taskkill or SIGKILL while crawling.
  3. Try submitting another research query for the exact same target company name.
  4. Observe that the system locks the request, blocking execution until the 30-minute TTL expires.
* **Expected Behavior:** Orphaned locks are swept and released dynamically by heartbeat daemons or automatic sweeper schedules.
* **Actual Behavior:** Stuck locks block execution pipelines, freezing target company research runs.
* **Recommended Fix:** `Implement Lock Heartbeats. Reduce TTL to 5 minutes, extending locks dynamically every 60 seconds from the active crawler worker.`
* **Prevention Strategy:** Set strict memory limits in Docker container parameters to prevent unhandled worker crashes.
* **SRE Monitoring Recommendation:** Alert SRE teams if memory limits exceed 90% or if lock ages exceed 10 minutes without state updates.

---

