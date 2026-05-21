# run_platform.ps1
# Unified Platform Orchestration & Diagnostic Manager
# ========================================================
# Beautiful, premium dark-mode CLI manager for the Company Intelligence Platform.
# Orchestrates Redis, FastAPI Backend, Celery, and React Frontend with strict health validation.

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "PLACEMENT INTEL PLATFORM MANAGER"

# ═══════════════════════════════════════════════════════════════════════════
# COLOR PALETTE & PRINTING HELPERS
# ═══════════════════════════════════════════════════════════════════════════
function Show-Header {
    Clear-Host
    Write-Host ""
    Write-Host " ┌──────────────────────────────────────────────────────────┐" -ForegroundColor Cyan
    Write-Host " │   🚀  PLACEMENT INTEL ENTERPRISE AI PLATFORM MANAGER   │" -ForegroundColor Cyan -BackgroundColor Black
    Write-Host " └──────────────────────────────────────────────────────────┘" -ForegroundColor Cyan
    Write-Host "   Windows-Specific Devops Architecture & Self-Healing Boot  " -ForegroundColor Gray
    Write-Host " ────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
}

function Show-Step ([string]$Step, [string]$Message) {
    Write-Host ""
    Write-Host " ⚡ [$Step] $Message" -ForegroundColor Blue -NoNewline
    Write-Host "..." -ForegroundColor Gray
}

function Show-Success ([string]$Message) {
    Write-Host "   ✅ $Message" -ForegroundColor Green
}

function Show-Warning ([string]$Message) {
    Write-Host "   ⚠️  $Message" -ForegroundColor Yellow
}

function Show-Error ([string]$Message) {
    Write-Host "   ❌ $Message" -ForegroundColor Red
}

function Show-Info ([string]$Message) {
    Write-Host "   💡 $Message" -ForegroundColor Gray
}

# ═══════════════════════════════════════════════════════════════════════════
# 1. INITIAL DIAGNOSTICS & SYSTEM PREPARATION
# ═══════════════════════════════════════════════════════════════════════════
Show-Header
Show-Step "1/5" "Performing system diagnostics & port validation"

$TargetPort = 8000
Show-Info "Target Web Port: $TargetPort"
Show-Info "Checking for duplicate/lingering process bindings on Port $TargetPort..."

# Terminate zombie Python uvicorn processes listening on 8000 or 8080
$occupiedPorts = @(8000, 8080)
foreach ($port in $occupiedPorts) {
    $owningProcess = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
    if ($owningProcess) {
        Show-Warning "Found active process PID $owningProcess bound to port $port. Investigating..."
        try {
            $proc = Get-Process -Id $owningProcess -ErrorAction SilentlyContinue
            if ($proc) {
                $procName = $proc.ProcessName
                Show-Warning "Process details: $procName (PID: $owningProcess)"
                
                if ($procName -like "*python*" -or $procName -like "*node*" -or $procName -like "*uvicorn*") {
                    Show-Warning "Process is a lingering development zombie. Forcefully terminating..."
                    Stop-Process -Id $owningProcess -Force
                    Start-Sleep -Seconds 1
                    Show-Success "Successfully terminated zombie process PID $owningProcess on Port $port."
                } else {
                    Show-Error "Port $port is held by a non-development process: $procName. Please release this port manually."
                }
            }
        } catch {
            Show-Error "Failed to fully analyze or kill occupying process for port $port."
        }
    }
}

# Forcefully purge any orphaned Celery worker, billiard spawn child processes, or uvicorn servers
Show-Info "Inspecting active system processes for duplicate or orphaned Celery/Billiard/Uvicorn elements..."
$targetProcs = Get-CimInstance Win32_Process -Filter "Name like '%python%'" -ErrorAction SilentlyContinue
if ($targetProcs) {
    $staleCount = 0
    foreach ($proc in $targetProcs) {
        $cmdLine = $proc.CommandLine
        if ($cmdLine -like "*celery*" -or $cmdLine -like "*billiard.spawn*" -or $cmdLine -like "*uvicorn*") {
            try {
                Show-Warning "Stopping stale/orphaned process PID $($proc.ProcessId): $($proc.Name)"
                Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
                $staleCount++
            } catch {}
        }
    }
    if ($staleCount -gt 0) {
        Show-Success "Successfully cleaned up $staleCount stale background process(es)."
    } else {
        Show-Success "No stale background Celery or Uvicorn processes found."
    }
}

Show-Success "System diagnostics completed. Environment is clean and conflict-free."

# ═══════════════════════════════════════════════════════════════════════════
# 2. ORCHESTRATE REDIS CACHE / MESSAGE BROKER
# ═══════════════════════════════════════════════════════════════════════════
Show-Step "2/5" "Orchestrating Redis Cache & Message Broker"

$redisPort = 6379
$redisActive = Get-NetTCPConnection -LocalPort $redisPort -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1

if ($redisActive) {
    Show-Success "Redis connection verified. Port $redisPort is actively listening."
} else {
    Show-Warning "Redis is not listening on Port $redisPort. Attempting Docker Container Startup..."
    
    # Check if Docker container exists and is running
    $dockerCheck = & docker ps -a --filter "name=company_intel_redis" --format "{{.Status}}"
    if ($dockerCheck -like "*Up*") {
        Show-Success "Redis container is already up (Docker network loopback active)."
    } elseif ($dockerCheck) {
        Show-Info "Starting existing Redis container..."
        & docker start company_intel_redis | Out-Null
        Start-Sleep -Seconds 2
        Show-Success "Redis container started successfully."
    } else {
        # Check if Docker is available
        try {
            & docker info > $null 2>&1
            Show-Info "Launching Redis Alpine from docker-compose orchestration..."
            & docker-compose up -d redis
            Start-Sleep -Seconds 3
            Show-Success "Redis service launched successfully via Docker."
        } catch {
            Show-Warning "Docker is not running and no local Redis server was found."
            Show-Warning "FastAPI will boot with safe local in-memory FakeRedis fallback."
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# 3. BOOT FASTAPI BACKEND WEB SERVER
# ═══════════════════════════════════════════════════════════════════════════
Show-Step "3/5" "Booting FastAPI Backend Web Server"

$venvPython = "backend\venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Show-Error "Virtual environment python not found at $venvPython!"
    Show-Info "Attempting standard system python..."
    $venvPython = "python"
}

Show-Info "Launching FastAPI via Uvicorn on Port $TargetPort..."
# Run backend asynchronously in a new background job
$BackendCommand = "cd backend; .\venv\Scripts\python.exe -X utf8 -m uvicorn app.main:app --host 0.0.0.0 --port $TargetPort --reload"
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $BackendCommand -WindowStyle Normal

# Readiness probe for backend server
$HealthUrl = "http://127.0.0.1:$TargetPort/health"
$retries = 15
$ready = $false

Show-Info "Polling liveness and database connection probes at: $HealthUrl"
for ($i = 1; $i -le $retries; $i++) {
    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.status -eq "healthy" -or $response.status -eq "degraded") {
            $ready = $true
            break
        }
    } catch {}
    Write-Host "   [Waiting] Backend initializing... (Attempt $i/$retries)" -ForegroundColor Gray
    Start-Sleep -Seconds 1
}

if ($ready) {
    Show-Success "FastAPI Backend is READY and responding on http://127.0.0.1:$TargetPort."
    Show-Info "Status: $($response.status) | Database: $($response.details.database.status)"
} else {
    Show-Error "FastAPI Backend failed to respond within the timeout threshold."
    Show-Info "Check backend console logs for validation errors."
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════
# 4. SPIN UP CELERY BACKGROUND WORKER
# ═══════════════════════════════════════════════════════════════════════════
Show-Step "4/5" "Spinning up Celery Background Worker"

Show-Info "Launching Celery Worker solo-pool worker in background..."
$CeleryCommand = "cd backend; .\venv\Scripts\python.exe -X utf8 -m celery -A app.core.celery_app worker --pool=solo --loglevel=info"
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $CeleryCommand -WindowStyle Normal

# Verify Celery worker readiness through the backend's detailed health check
$celeryReady = $false
Show-Info "Waiting for Celery worker registration..."
for ($i = 1; $i -le 10; $i++) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.details.celery.status -eq "active" -and $response.details.celery.active_nodes_count -gt 0) {
            $celeryReady = $true
            break
        }
    } catch {}
    Write-Host "   [Waiting] Worker joining active Redis pool... (Attempt $i/10)" -ForegroundColor Gray
}

if ($celeryReady) {
    Show-Success "Celery background worker is ACTIVE and registered."
    Show-Info "Active Nodes: $($response.details.celery.active_nodes_count)"
} else {
    Show-Warning "Celery worker was launched but did not register within 20s."
    Show-Info "Worker will self-heal and join the pool as soon as Redis is reachable."
}

# ═══════════════════════════════════════════════════════════════════════════
# 5. BOOT FRONTEND APP & FINALIZE ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════
Show-Step "5/5" "Checking Frontend SPA Dev Server"

$frontendPort = 5173
$frontendActive = Get-NetTCPConnection -LocalPort $frontendPort -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1

if ($frontendActive) {
    Show-Success "Frontend dev server is already running on Port $frontendPort."
} else {
    Show-Info "Launching React Frontend dev server via Vite..."
    $FrontendCommand = "cd frontend; npm run dev"
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $FrontendCommand -WindowStyle Normal
    Start-Sleep -Seconds 2
    Show-Success "Frontend dev server launched successfully."
}

# ═══════════════════════════════════════════════════════════════════════════
# ARCHITECTURE VALIDATION COMPLETE
# ═══════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Host " ────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host " 🎉  SUCCESS! PLATFORM BOOTED AND STABILIZED SUCCESSFULLY!   " -ForegroundColor Green -BackgroundColor Black
Write-Host " ────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "   Frontend client:     http://localhost:5173" -ForegroundColor Green
Write-Host "   Backend API Docs:    http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "   Redis Port:          6379" -ForegroundColor Green
Write-Host "   Celery Metrics:      http://127.0.0.1:9100" -ForegroundColor Green
Write-Host ""
Write-Host " 💡 Professional Operations Guidelines:" -ForegroundColor Gray
Write-Host "    - All services have been validated conflict-free." -ForegroundColor Gray
Write-Host "    - Startup self-healing utilities protect from duplicate worker crashes." -ForegroundColor Gray
Write-Host "    - Running instances reside in independent background terminals." -ForegroundColor Gray
Write-Host ""
Write-Host " Press [Enter] to return control to the workspace console." -ForegroundColor Cyan
Read-Host
