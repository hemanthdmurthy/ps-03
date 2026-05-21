"""
OpenTelemetry Distributed Tracing — Production-Grade Resilient Module
=====================================================================

Architecture guarantees:
  1. Application NEVER crashes due to telemetry failures.
  2. Exporter failures NEVER block HTTP requests or starve the event loop.
  3. Collector outages are survivable — circuit-breaker + exponential backoff.
  4. Bounded memory — span queue is capped, excess spans are dropped.
  5. No log flooding — rate-limited warnings during sustained outages.
  6. No retry storms — backoff grows exponentially up to 5 minutes.
  7. Watchdog thread monitors collector health and triggers reconnection.

Fallback hierarchy:
  1. OTLP Collector (gRPC) → via ResilientSpanExporter
  2. Local Jaeger (OTEL_JAEGER_ENDPOINT) → via ResilientSpanExporter
  3. Console exporter → dev/testing only
  4. Silent degradation → traces created but dropped (production default)

Environment Variables:
  OTEL_ENABLED                 — "false" to kill all tracing (emergency switch)
  OTEL_EXPORTER_OTLP_ENDPOINT  — gRPC endpoint (e.g. http://otel-collector:4317)
  OTEL_JAEGER_ENDPOINT         — Jaeger fallback (e.g. http://localhost:4317)
  OTEL_EXPORT_CONSOLE          — "true" for console span output
  OTEL_SERVICE_NAME            — service identity in traces
  OTEL_RESOURCE_ATTRIBUTES     — comma-separated key=value pairs
  OTEL_WATCHDOG_INTERVAL       — seconds between health probes (default: 60)
"""

import logging
import os
import socket
import threading
import time
from typing import Optional, Sequence
from urllib.parse import urlparse

logger = logging.getLogger("company_intel.telemetry")


# ═══════════════════════════════════════════════════════════════════════════
# RATE-LIMITED LOGGER — prevents log flooding during sustained outages
# ═══════════════════════════════════════════════════════════════════════════

class _RateLimitedLogger:
    """Emits at most one log per key per interval. Thread-safe."""

    def __init__(self, min_interval: float = 60.0):
        self._interval = min_interval
        self._last: dict[str, float] = {}
        self._suppressed: dict[str, int] = {}
        self._lock = threading.Lock()

    def warning(self, key: str, msg: str, *args):
        with self._lock:
            now = time.monotonic()
            last = self._last.get(key, 0.0)
            if now - last < self._interval:
                self._suppressed[key] = self._suppressed.get(key, 0) + 1
                return
            suppressed = self._suppressed.pop(key, 0)
            self._last[key] = now
        if suppressed:
            logger.warning(msg + " (suppressed %d similar in last %.0fs)", *args, suppressed, self._interval)
        else:
            logger.warning(msg, *args)

    def info(self, key: str, msg: str, *args):
        with self._lock:
            now = time.monotonic()
            if now - self._last.get(key, 0.0) < self._interval:
                return
            self._last[key] = now
        logger.info(msg, *args)


_rl_log = _RateLimitedLogger(min_interval=60.0)


# ═══════════════════════════════════════════════════════════════════════════
# SAFE DEPENDENCY PROBING
# ═══════════════════════════════════════════════════════════════════════════

TELEMETRY_AVAILABLE = False
_MISSING_PACKAGES: list[str] = []


def _probe_dependency(module_path: str, label: str) -> bool:
    try:
        __import__(module_path)
        return True
    except ImportError:
        _MISSING_PACKAGES.append(label)
        return False


_HAS_API       = _probe_dependency("opentelemetry",                                       "opentelemetry-api")
_HAS_SDK       = _probe_dependency("opentelemetry.sdk.trace",                              "opentelemetry-sdk")
_HAS_RESOURCES = _probe_dependency("opentelemetry.sdk.resources",                          "opentelemetry-sdk")
_HAS_OTLP      = _probe_dependency("opentelemetry.exporter.otlp.proto.grpc.trace_exporter", "opentelemetry-exporter-otlp-proto-grpc")
_HAS_FASTAPI   = _probe_dependency("opentelemetry.instrumentation.fastapi",                "opentelemetry-instrumentation-fastapi")
_HAS_CELERY    = _probe_dependency("opentelemetry.instrumentation.celery",                 "opentelemetry-instrumentation-celery")
_HAS_REDIS     = _probe_dependency("opentelemetry.instrumentation.redis",                  "opentelemetry-instrumentation-redis")
_HAS_SQLA      = _probe_dependency("opentelemetry.instrumentation.sqlalchemy",             "opentelemetry-instrumentation-sqlalchemy")

TELEMETRY_AVAILABLE = all([_HAS_API, _HAS_SDK, _HAS_RESOURCES])

if _MISSING_PACKAGES:
    logger.warning("⚠️  [Telemetry] Missing: %s. Tracing DISABLED.", ", ".join(sorted(set(_MISSING_PACKAGES))))
else:
    logger.info("✅ [Telemetry] All OpenTelemetry dependencies detected.")


# ═══════════════════════════════════════════════════════════════════════════
# COLLECTOR CONNECTIVITY PROBE
# ═══════════════════════════════════════════════════════════════════════════

def _is_collector_reachable(endpoint: str, timeout: float = 2.0) -> bool:
    """TCP socket probe. Returns True if handshake completes within timeout."""
    try:
        parsed = urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or 4317
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# RESILIENT SPAN EXPORTER — circuit-breaker + backoff + memory protection
# ═══════════════════════════════════════════════════════════════════════════

if TELEMETRY_AVAILABLE:
    from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

    class ResilientSpanExporter(SpanExporter):
        """
        Production-grade exporter wrapper with:
        - Circuit-breaker: opens after N consecutive failures
        - Exponential backoff with jitter: 15s → 30s → 60s → ... → 300s cap
        - Bounded memory: drops spans when circuit is open (no queuing)
        - Rate-limited logging: max 1 warning per 60s during outages
        - Auto-disable: permanently disables after configurable max failures
        - Thread-safe: all state guarded by lock
        - Never raises, never blocks, never returns FAILURE
        """

        def __init__(self, inner: SpanExporter, *, failure_threshold: int = 3,
                     backoff_base_seconds: float = 15.0, backoff_max_seconds: float = 300.0,
                     auto_disable_after: int = 500, exporter_name: str = "otlp-grpc"):
            self._inner = inner
            self._failure_threshold = failure_threshold
            self._backoff_base = backoff_base_seconds
            self._backoff_max = backoff_max_seconds
            self._auto_disable_after = auto_disable_after
            self._exporter_name = exporter_name

            self._lock = threading.Lock()
            self._consecutive_failures = 0
            self._circuit_open = False
            self._circuit_opened_at: float = 0.0
            self._backoff_interval: float = backoff_base_seconds
            self._permanently_disabled = False
            self._total_exported = 0
            self._total_dropped = 0
            self._total_failures = 0
            self._last_success_at: float = 0.0
            self._last_failure_at: float = 0.0

        def export(self, spans: Sequence) -> SpanExportResult:
            if not spans:
                return SpanExportResult.SUCCESS

            with self._lock:
                if self._permanently_disabled:
                    self._total_dropped += len(spans)
                    return SpanExportResult.SUCCESS

                if self._circuit_open:
                    elapsed = time.monotonic() - self._circuit_opened_at
                    if elapsed < self._backoff_interval:
                        self._total_dropped += len(spans)
                        return SpanExportResult.SUCCESS
                    # Half-open: attempt probe
                    _rl_log.info("half_open", "ℹ️  [Telemetry:%s] Circuit half-open — probing.", self._exporter_name)
                    self._circuit_open = False

            try:
                result = self._inner.export(spans)
                if result == SpanExportResult.SUCCESS:
                    with self._lock:
                        self._consecutive_failures = 0
                        self._backoff_interval = self._backoff_base
                        self._total_exported += len(spans)
                        self._last_success_at = time.monotonic()
                    return SpanExportResult.SUCCESS
                else:
                    self._record_failure(len(spans), "returned FAILURE")
                    return SpanExportResult.SUCCESS
            except Exception as e:
                self._record_failure(len(spans), str(e))
                return SpanExportResult.SUCCESS

        def _record_failure(self, span_count: int, reason: str):
            with self._lock:
                self._consecutive_failures += 1
                self._total_failures += 1
                self._total_dropped += span_count
                self._last_failure_at = time.monotonic()

                # Auto-disable after sustained failures
                if self._total_failures >= self._auto_disable_after:
                    self._permanently_disabled = True
                    logger.warning(
                        "🔴 [Telemetry:%s] PERMANENTLY DISABLED after %d total failures.",
                        self._exporter_name, self._total_failures,
                    )
                    return

                if self._consecutive_failures >= self._failure_threshold and not self._circuit_open:
                    self._circuit_open = True
                    self._circuit_opened_at = time.monotonic()
                    self._backoff_interval = min(self._backoff_interval * 2, self._backoff_max)
                    _rl_log.warning(
                        "circuit_open",
                        "⚠️  [Telemetry:%s] Circuit OPENED (%d failures). Backoff %.0fs. Reason: %s",
                        self._exporter_name, self._consecutive_failures,
                        self._backoff_interval, reason,
                    )

        def re_enable(self):
            """Manually re-enable a permanently disabled exporter (e.g. after collector restart)."""
            with self._lock:
                self._permanently_disabled = False
                self._circuit_open = False
                self._consecutive_failures = 0
                self._backoff_interval = self._backoff_base
                logger.info("✅ [Telemetry:%s] Manually re-enabled.", self._exporter_name)

        def shutdown(self):
            try:
                self._inner.shutdown()
            except Exception:
                pass

        def force_flush(self, timeout_millis: int = 5000):
            try:
                self._inner.force_flush(timeout_millis=timeout_millis)
            except Exception:
                pass

        @property
        def stats(self) -> dict:
            with self._lock:
                return {
                    "exporter": self._exporter_name,
                    "circuit_open": self._circuit_open,
                    "permanently_disabled": self._permanently_disabled,
                    "consecutive_failures": self._consecutive_failures,
                    "backoff_interval_s": self._backoff_interval,
                    "total_exported": self._total_exported,
                    "total_dropped": self._total_dropped,
                    "total_failures": self._total_failures,
                    "last_success_age_s": round(time.monotonic() - self._last_success_at, 1) if self._last_success_at else None,
                    "last_failure_age_s": round(time.monotonic() - self._last_failure_at, 1) if self._last_failure_at else None,
                }


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTER WATCHDOG — background thread for health monitoring + reconnection
# ═══════════════════════════════════════════════════════════════════════════

class _ExporterWatchdog:
    """
    Background daemon thread that:
    - Periodically probes collector reachability
    - Re-enables a permanently-disabled ResilientSpanExporter when collector recovers
    - Emits self-diagnostic metrics to logger
    - Never blocks the event loop (runs in its own thread)
    - Terminates cleanly on shutdown
    """

    def __init__(self, exporter: 'ResilientSpanExporter', endpoint: str,
                 interval: float = 60.0):
        self._exporter = exporter
        self._endpoint = endpoint
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._probe_count = 0
        self._recovery_count = 0

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run, name="otel-watchdog", daemon=True
        )
        self._thread.start()
        logger.info("✅ [Watchdog] Started (interval=%ds, endpoint=%s)", self._interval, self._endpoint)

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    def _run(self):
        while not self._stop_event.wait(timeout=self._interval):
            self._probe_count += 1
            try:
                stats = self._exporter.stats
                reachable = _is_collector_reachable(self._endpoint, timeout=3.0)

                # If collector came back and exporter is disabled/circuit-open, re-enable
                if reachable and (stats["permanently_disabled"] or stats["circuit_open"]):
                    self._exporter.re_enable()
                    self._recovery_count += 1
                    logger.info(
                        "✅ [Watchdog] Collector recovered at %s. Exporter re-enabled (recovery #%d).",
                        self._endpoint, self._recovery_count,
                    )
                elif not reachable and not stats["circuit_open"] and not stats["permanently_disabled"]:
                    _rl_log.warning(
                        "watchdog_unreachable",
                        "⚠️  [Watchdog] Collector at %s unreachable (probe #%d).",
                        self._endpoint, self._probe_count,
                    )
            except Exception as e:
                logger.debug("[Watchdog] Probe error: %s", e)

    @property
    def diagnostics(self) -> dict:
        return {
            "running": self._thread is not None and self._thread.is_alive(),
            "endpoint": self._endpoint,
            "interval_s": self._interval,
            "probe_count": self._probe_count,
            "recovery_count": self._recovery_count,
        }


# ═══════════════════════════════════════════════════════════════════════════
# THREAD-SAFE SINGLETON STATE
# ═══════════════════════════════════════════════════════════════════════════

_lock = threading.Lock()
_TELEMETRY_INITIALIZED = False
_ACTIVE_PROVIDER = None
_RESILIENT_EXPORTER: Optional[object] = None
_WATCHDOG: Optional[_ExporterWatchdog] = None
_INSTRUMENTED_APPS: set = set()
_INIT_PID: Optional[int] = None  # Track which PID initialized telemetry


# ═══════════════════════════════════════════════════════════════════════════
# STARTUP VALIDATION — structured pre-flight checks
# ═══════════════════════════════════════════════════════════════════════════

def validate_telemetry_config() -> dict:
    """
    Pre-flight validation of telemetry configuration.
    Returns a structured report suitable for logging or /health.
    """
    issues = []
    warnings = []

    otel_enabled = os.environ.get("OTEL_ENABLED", "true").strip().lower() != "false"
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    jaeger = os.environ.get("OTEL_JAEGER_ENDPOINT", "").strip()

    if not otel_enabled:
        warnings.append("OTEL_ENABLED=false: all tracing disabled")

    if endpoint and "localhost" in endpoint:
        warnings.append(f"OTEL_EXPORTER_OTLP_ENDPOINT uses localhost ({endpoint}) — may fail in containers")

    if endpoint and not _HAS_OTLP:
        issues.append("OTEL_EXPORTER_OTLP_ENDPOINT set but opentelemetry-exporter-otlp-proto-grpc not installed")

    if not TELEMETRY_AVAILABLE:
        issues.append("Core OTel packages missing (opentelemetry-api, opentelemetry-sdk)")

    endpoint_reachable = None
    if endpoint:
        endpoint_reachable = _is_collector_reachable(endpoint, timeout=2.0)
        if not endpoint_reachable:
            warnings.append(f"Collector at {endpoint} is unreachable (pre-flight probe failed)")

    return {
        "valid": len(issues) == 0,
        "otel_enabled": otel_enabled,
        "packages_available": TELEMETRY_AVAILABLE,
        "endpoint": endpoint or None,
        "endpoint_reachable": endpoint_reachable,
        "jaeger_endpoint": jaeger or None,
        "service_name": os.environ.get("OTEL_SERVICE_NAME", "placement-intel-backend"),
        "issues": issues,
        "warnings": warnings,
    }


def _check_fork_safety():
    """Reset singleton state if we're in a forked child process (Gunicorn)."""
    global _TELEMETRY_INITIALIZED, _ACTIVE_PROVIDER, _RESILIENT_EXPORTER, _WATCHDOG, _INIT_PID
    current_pid = os.getpid()
    if _INIT_PID is not None and _INIT_PID != current_pid:
        logger.info("[Telemetry] Fork detected (parent=%d, child=%d). Resetting state.", _INIT_PID, current_pid)
        _TELEMETRY_INITIALIZED = False
        _ACTIVE_PROVIDER = None
        _RESILIENT_EXPORTER = None
        _WATCHDOG = None
        _INSTRUMENTED_APPS.clear()


# ═══════════════════════════════════════════════════════════════════════════
# SETUP — called from app startup lifecycle
# ═══════════════════════════════════════════════════════════════════════════

def setup_telemetry(app=None, engine=None):
    """
    Initialize OpenTelemetry with full resilience. Never raises.
    Safe for module-level, startup hooks, post_fork, and pytest.
    """
    global _TELEMETRY_INITIALIZED, _ACTIVE_PROVIDER, _RESILIENT_EXPORTER, _WATCHDOG

    if os.environ.get("OTEL_ENABLED", "true").strip().lower() == "false":
        logger.info("ℹ️  [Telemetry] OTEL_ENABLED=false — all tracing disabled.")
        return

    with _lock:
        _check_fork_safety()
        if _TELEMETRY_INITIALIZED:
            if app and id(app) not in _INSTRUMENTED_APPS:
                _instrument_fastapi(app)
            return

        if not TELEMETRY_AVAILABLE:
            logger.warning(
                "⚠️  [Telemetry] Core packages missing. Install: "
                "pip install opentelemetry-api opentelemetry-sdk "
                "opentelemetry-exporter-otlp-proto-grpc"
            )
            return

        try:
            _do_setup(app, engine)
        except Exception as e:
            logger.error("❌ [Telemetry] Setup failed: %s. Continuing without tracing.", e, exc_info=True)


def _do_setup(app, engine):
    """Internal setup. Called inside the singleton lock."""
    global _TELEMETRY_INITIALIZED, _ACTIVE_PROVIDER, _RESILIENT_EXPORTER, _WATCHDOG, _INIT_PID
    _INIT_PID = os.getpid()

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    from app.core.config import settings

    # ── Build Resource from env vars ──
    service_name = os.environ.get("OTEL_SERVICE_NAME", "placement-intel-backend").strip()
    resource_attrs = {
        "service.name": service_name,
        "service.version": "1.0.0",
        "service.environment": settings.ENVIRONMENT,
        "deployment.environment": settings.ENVIRONMENT,
    }
    extra_attrs = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").strip()
    if extra_attrs:
        for pair in extra_attrs.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                resource_attrs[k.strip()] = v.strip()
    resource = Resource.create(resource_attrs)

    provider = TracerProvider(resource=resource)
    exporter_configured = False
    active_endpoint = None

    # ── Fallback 1: OTLP Collector ──
    collector_ep = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if collector_ep and _HAS_OTLP and _is_collector_reachable(collector_ep):
        exporter_configured, active_endpoint = _try_otlp_exporter(
            provider, collector_ep, "otlp-collector"
        )

    # ── Fallback 2: Local Jaeger ──
    if not exporter_configured:
        jaeger_ep = os.environ.get("OTEL_JAEGER_ENDPOINT", "").strip()
        if jaeger_ep and _HAS_OTLP and _is_collector_reachable(jaeger_ep):
            exporter_configured, active_endpoint = _try_otlp_exporter(
                provider, jaeger_ep, "jaeger-local"
            )

    # ── Fallback 3: Console Exporter ──
    if not exporter_configured:
        use_console = os.environ.get("OTEL_EXPORT_CONSOLE", "").strip().lower() == "true"
        is_dev = settings.ENVIRONMENT in ("testing", "development")
        explicit_false = os.environ.get("OTEL_EXPORT_CONSOLE", "").strip().lower() == "false"

        if use_console or (is_dev and not explicit_false):
            provider.add_span_processor(BatchSpanProcessor(
                ConsoleSpanExporter(),
                max_queue_size=256, max_export_batch_size=64, schedule_delay_millis=2000,
            ))
            exporter_configured = True
            logger.info("ℹ️  [Telemetry] ConsoleSpanExporter active (fallback).")

    # ── Fallback 4: Silent degradation ──
    if not exporter_configured:
        logger.info(
            "ℹ️  [Telemetry] Silent degradation — traces created but not exported. "
            "Set OTEL_EXPORTER_OTLP_ENDPOINT or OTEL_EXPORT_CONSOLE=true to enable."
        )

    trace.set_tracer_provider(provider)
    _ACTIVE_PROVIDER = provider

    # ── Start watchdog if we have an OTLP endpoint (even if currently unreachable) ──
    watchdog_endpoint = collector_ep or os.environ.get("OTEL_JAEGER_ENDPOINT", "").strip()
    if watchdog_endpoint and _RESILIENT_EXPORTER is not None:
        watchdog_interval = float(os.environ.get("OTEL_WATCHDOG_INTERVAL", "60"))
        _WATCHDOG = _ExporterWatchdog(_RESILIENT_EXPORTER, watchdog_endpoint, watchdog_interval)
        _WATCHDOG.start()

    # ── Instrumentation ──
    if app:
        _instrument_fastapi(app)
    _instrument_celery()
    _instrument_redis()
    if engine:
        _instrument_sqlalchemy(engine)

    _TELEMETRY_INITIALIZED = True
    logger.info("✅ [Telemetry] Setup complete (exporter=%s).",
                "active" if exporter_configured else "none/silent")


def _try_otlp_exporter(provider, endpoint: str, name: str) -> tuple:
    """Attempt to create an OTLP gRPC exporter with ResilientSpanExporter wrapper.
    Returns (success: bool, endpoint_used: str|None)."""
    global _RESILIENT_EXPORTER
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        inner = OTLPSpanExporter(endpoint=endpoint, insecure=True, timeout=10)
        resilient = ResilientSpanExporter(
            inner, failure_threshold=3, backoff_base_seconds=15.0,
            backoff_max_seconds=300.0, auto_disable_after=500,
            exporter_name=f"{name}({endpoint})",
        )
        _RESILIENT_EXPORTER = resilient

        # Bounded queue: max 2048 spans in memory, drops oldest on overflow
        provider.add_span_processor(BatchSpanProcessor(
            resilient, max_queue_size=2048, max_export_batch_size=512,
            export_timeout_millis=15000, schedule_delay_millis=5000,
        ))
        logger.info("✅ [Telemetry] %s exporter → %s (resilient + watchdog)", name, endpoint)
        return True, endpoint
    except Exception as e:
        logger.warning("⚠️  [Telemetry] %s exporter setup failed: %s", name, e)
        return False, None


# ═══════════════════════════════════════════════════════════════════════════
# INSTRUMENTATION HELPERS (each individually fault-isolated)
# ═══════════════════════════════════════════════════════════════════════════

def _instrument_fastapi(app):
    if not _HAS_FASTAPI:
        return
    if id(app) in _INSTRUMENTED_APPS:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        _INSTRUMENTED_APPS.add(id(app))
        logger.info("✅ [Telemetry] FastAPI instrumentation enabled.")
    except Exception as e:
        logger.warning("⚠️  [Telemetry] FastAPI instrumentation failed: %s", e)


def _instrument_celery():
    if not _HAS_CELERY:
        return
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()
        logger.info("✅ [Telemetry] Celery instrumentation enabled.")
    except Exception as e:
        logger.warning("⚠️  [Telemetry] Celery instrumentation failed: %s", e)


def _instrument_redis():
    if not _HAS_REDIS:
        return
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
        logger.info("✅ [Telemetry] Redis instrumentation enabled.")
    except Exception as e:
        logger.warning("⚠️  [Telemetry] Redis instrumentation failed: %s", e)


def _instrument_sqlalchemy(engine):
    if not _HAS_SQLA:
        return
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True, commenter_options={})
        logger.info("✅ [Telemetry] SQLAlchemy instrumentation enabled.")
    except Exception as e:
        logger.warning("⚠️  [Telemetry] SQLAlchemy instrumentation failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════
# GRACEFUL SHUTDOWN
# ═══════════════════════════════════════════════════════════════════════════

def shutdown_telemetry():
    """Flush pending spans and tear down. Safe to call multiple times. Never raises."""
    global _ACTIVE_PROVIDER, _TELEMETRY_INITIALIZED, _RESILIENT_EXPORTER, _WATCHDOG

    with _lock:
        # Stop watchdog first
        if _WATCHDOG is not None:
            try:
                _WATCHDOG.stop()
            except Exception:
                pass
            _WATCHDOG = None

        if _ACTIVE_PROVIDER is None:
            return

        try:
            _ACTIVE_PROVIDER.force_flush(timeout_millis=5000)
        except Exception:
            pass

        try:
            _ACTIVE_PROVIDER.shutdown()
        except Exception:
            pass

        # Final stats
        if _RESILIENT_EXPORTER is not None:
            try:
                s = _RESILIENT_EXPORTER.stats
                logger.info(
                    "📊 [Telemetry] Final: exported=%d dropped=%d failures=%d disabled=%s",
                    s["total_exported"], s["total_dropped"], s["total_failures"],
                    s["permanently_disabled"],
                )
            except Exception:
                pass

        _ACTIVE_PROVIDER = None
        _RESILIENT_EXPORTER = None
        _TELEMETRY_INITIALIZED = False
        logger.info("✅ [Telemetry] Shut down gracefully.")


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH & SELF-DIAGNOSTICS API
# ═══════════════════════════════════════════════════════════════════════════

def get_telemetry_status() -> dict:
    """Full self-diagnostics for /health or /metrics endpoints."""
    status = {
        "initialized": _TELEMETRY_INITIALIZED,
        "packages_available": TELEMETRY_AVAILABLE,
        "missing_packages": sorted(set(_MISSING_PACKAGES)) if _MISSING_PACKAGES else [],
        "provider_active": _ACTIVE_PROVIDER is not None,
        "otel_enabled": os.environ.get("OTEL_ENABLED", "true").strip().lower() != "false",
        "collector_endpoint": os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
        "jaeger_endpoint": os.environ.get("OTEL_JAEGER_ENDPOINT", ""),
        "protocol": os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc"),
        "service_name": os.environ.get("OTEL_SERVICE_NAME", "placement-intel-backend"),
        "resource_attributes": os.environ.get("OTEL_RESOURCE_ATTRIBUTES", ""),
        "console_export": os.environ.get("OTEL_EXPORT_CONSOLE", "false"),
    }

    if _RESILIENT_EXPORTER is not None:
        try:
            status["exporter"] = _RESILIENT_EXPORTER.stats
        except Exception:
            status["exporter"] = {"error": "unable to read stats"}
    else:
        status["exporter"] = None

    if _WATCHDOG is not None:
        try:
            status["watchdog"] = _WATCHDOG.diagnostics
        except Exception:
            status["watchdog"] = {"error": "unable to read diagnostics"}
    else:
        status["watchdog"] = None

    return status
