# Heartbeat Recovery Report

## 1. Dynamic Lock Management
- Transitioned to Redis dynamic heartbeat-based locks for long-running workflows.
- Implemented a background thread/coroutine that renews lock heartbeats every 60 seconds.

## 2. Lock Expiration Safeguards
- Created Lua-script based `EXPIRE` renewal strategies to ensure atomicity in Redis lock extensions.
- Designed stale lock cleanup jobs to harvest dropped locks.
- Orphan worker detection allows tasks to be re-assigned quickly if a heartbeat drops off for more than 3 consecutive intervals.

## 3. Recovery Validation
- Simulations confirmed that killing a worker mid-execution results in lock expiration within 5 minutes, allowing another worker to safely claim and resume the job.
- Validated heartbeat recovery processes under high concurrency.
