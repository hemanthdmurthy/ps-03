# app/utils/port_validator.py
"""
Self-Healing Port Validator and Cleanup Service
=================================================
Identifies and automatically resolves port binding conflicts on startup.
Detects active listeners on Windows systems, locates duplicate Python/Node zombie
processes, forcefully clears conflicting sockets, and logs detailed diagnostic traces.
"""

import os
import sys
import socket
import subprocess
import logging
from typing import Optional, Tuple
from app.core.config import settings

logger = logging.getLogger("company_intel.utils.port_validator")

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a TCP port is currently occupied by attempting to bind to it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            # Set socket reuse flag to prevent TIME_WAIT false positives on quick restarts
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return False
        except socket.error:
            return True

def get_process_details_by_pid(pid: int) -> Tuple[str, str]:
    """Retrieves the executable name and command line of a process using Windows utilities."""
    name = "unknown"
    cmdline = "unknown"
    try:
        # Get process name using tasklist
        tasklist_out = subprocess.check_output(
            f'tasklist /FI "PID eq {pid}" /NH',
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        if tasklist_out and "No tasks are running" not in tasklist_out:
            parts = tasklist_out.strip().split()
            if len(parts) > 0:
                name = parts[0]
                
        # Get process command line using wmic
        wmic_out = subprocess.check_output(
            f'wmic process where ProcessId={pid} get CommandLine /value',
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        for line in wmic_out.splitlines():
            if line.startswith("CommandLine="):
                cmdline = line.split("CommandLine=", 1)[1].strip()
                break
    except Exception:
        pass
    return name, cmdline

def get_process_on_port(port: int) -> Optional[int]:
    """Finds the PID of the process listening on a specified port using netstat on Windows."""
    try:
        output = subprocess.check_output(
            "netstat -ano",
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL
        )
        for line in output.splitlines():
            # Match listening socket on port
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    try:
                        pid = int(parts[-1])
                        return pid
                    except ValueError:
                        continue
    except Exception as e:
        logger.error(f"[Port Check] Failed to execute netstat: {e}")
    return None

def terminate_process(pid: int, reason: str = "Conflicting port usage") -> bool:
    """Forcefully terminates a conflicting process using taskkill."""
    try:
        logger.warning(f"⚠️ [Port Cleanup] Terminating PID {pid} due to: {reason}...")
        subprocess.check_call(
            f"taskkill /F /PID {pid}",
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logger.info(f"✅ [Port Cleanup] Successfully terminated PID {pid}.")
        return True
    except Exception as e:
        logger.error(f"❌ [Port Cleanup] Failed to terminate PID {pid}: {e}")
        return False

def clean_and_verify_port(port: int) -> bool:
    """
    Main self-healing entrypoint. Detects duplicate/zombie servers,
    terminates them, and verifies port readiness.
    """
    if not is_port_in_use(port):
        logger.info(f"❇️ [Port Validator] Target Port {port} is FREE and available for binding.")
        return True

    logger.warning(f"⚠️ [Port Validator] Target Port {port} is occupied! Initiating self-healing socket scan...")
    pid = get_process_on_port(port)
    if not pid:
        logger.error(f"❌ [Port Validator] Port {port} is occupied, but netstat did not return a valid PID. (Could be an active OS service).")
        return False

    name, cmdline = get_process_details_by_pid(pid)
    logger.warning(f"🔍 [Port Conflict] Occupying Process detected:")
    logger.warning(f"   - PID:          {pid}")
    logger.warning(f"   - Process Name: {name}")
    logger.warning(f"   - Command Line: {cmdline}")

    # Check if it is a Python or Node duplicate/zombie
    is_safe_to_kill = any(kw in name.lower() for kw in ("python", "node", "uvicorn")) or \
                      any(kw in cmdline.lower() for kw in ("uvicorn", "app.main", "celery", "npm", "vite"))

    if is_safe_to_kill:
        logger.warning(f"🔄 [Port Validator] Safe zombie candidate detected. Initiating automated recovery...")
        terminated = terminate_process(pid, reason=f"Lingering duplicate/zombie listening on web port {port}")
        if terminated:
            # Recheck
            if not is_port_in_use(port):
                logger.info(f"❇️ [Port Validator] Socket recovery SUCCESSFUL. Port {port} is now free.")
                return True
            else:
                logger.error(f"❌ [Port Validator] Process killed but port {port} remains blocked (waiting for TCP TIME_WAIT release).")
                return False
    else:
        logger.error(
            f"❌ [Port Validator] Conflicting process PID {pid} ({name}) is not identified as a safe development zombie. "
            f"Please terminate this process manually."
        )
    return False

def execute_pre_startup_check():
    """
    Determines if the current process is starting up as the main web server,
    and runs the port conflict validation if appropriate.
    """
    # Only run the port binding validation if we are launching the API Web Server.
    # Exclude if running celery worker, celery beat, db migrations, or tests.
    args_str = " ".join(sys.argv).lower()
    is_celery = "celery" in args_str
    is_alembic = "alembic" in args_str
    is_test = "pytest" in args_str or "test" in args_str
    
    # We run port validation if we are in main execution or if we were launched by uvicorn
    is_web_server = any(kw in args_str for kw in ("uvicorn", "main.py")) or __name__ == "__main__"
    
    if is_web_server and not (is_celery or is_alembic or is_test):
        port = settings.PORT
        logger.info("=" * 60)
        logger.info(f"🚀 [BACKEND PRE-STARTUP HEALTH CHECK]")
        logger.info(f"   Target Port:       {port}")
        logger.info(f"   Platform OS:       {sys.platform}")
        logger.info(f"   Process PID:       {os.getpid()}")
        logger.info(f"   Command Args:      {sys.argv}")
        logger.info("=" * 60)
        
        success = clean_and_verify_port(port)
        if not success:
            logger.critical(f"🛑 [Startup Aborted] Port {port} is blocked and self-healing failed. Terminating to prevent crash loops.")
            sys.exit(1)
        else:
            logger.info("📡 [Startup Allowed] Precheck verified. Handing over to web server binding process.")
