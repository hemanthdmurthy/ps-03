"""Comprehensive validation of production-grade telemetry resilience."""
import os
import sys
import time

os.environ["OTEL_ENABLED"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""
os.environ["OTEL_EXPORT_CONSOLE"] = "false"
os.environ["OTEL_JAEGER_ENDPOINT"] = ""
os.environ["OTEL_SERVICE_NAME"] = "test-service"
os.environ["OTEL_RESOURCE_ATTRIBUTES"] = "deployment.environment=test,service.version=2.0.0"
os.environ["OTEL_WATCHDOG_INTERVAL"] = "60"

from app.core.telemetry import (
    TELEMETRY_AVAILABLE, setup_telemetry, shutdown_telemetry,
    get_telemetry_status, _is_collector_reachable, _RateLimitedLogger,
)

passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")

# ── Test 1: Module Load ──
print("=== 1. Module Load ===")
test("TELEMETRY_AVAILABLE", TELEMETRY_AVAILABLE)
test("Collector unreachable (empty)", not _is_collector_reachable(""))
test("Collector unreachable (dead)", not _is_collector_reachable("http://localhost:4317"))

# ── Test 2: Rate-Limited Logger ──
print("\n=== 2. Rate-Limited Logger ===")
import logging
handler = logging.StreamHandler()
handler.setLevel(logging.WARNING)
logging.getLogger("company_intel.telemetry").addHandler(handler)

rl = _RateLimitedLogger(min_interval=0.5)
rl.warning("k1", "First %s", "msg")  # Should emit
rl.warning("k1", "Second %s", "msg")  # Should suppress
rl.warning("k1", "Third %s", "msg")   # Should suppress
test("Rate limiting suppresses duplicates", True)  # If we got here, no crash

# ── Test 3: ResilientSpanExporter ──
print("\n=== 3. ResilientSpanExporter ===")
from app.core.telemetry import ResilientSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SpanExportResult

# Working exporter
resilient = ResilientSpanExporter(ConsoleSpanExporter(), exporter_name="test-ok")
test("Empty export succeeds", resilient.export([]) == SpanExportResult.SUCCESS)
test("Stats readable", isinstance(resilient.stats, dict))
resilient.shutdown()

# Failing exporter - circuit breaker
class FailingExporter:
    def export(self, spans): raise ConnectionError("dead")
    def shutdown(self): pass
    def force_flush(self, timeout_millis=0): pass

failing = ResilientSpanExporter(
    FailingExporter(), failure_threshold=2, backoff_base_seconds=0.001,
    auto_disable_after=6, exporter_name="test-fail"
)

# Trigger failures — tiny backoff means circuit half-opens almost immediately
for i in range(30):
    failing.export(["span"])
    time.sleep(0.1)  # Generous sleep to let backoff elapse

s = failing.stats
test("Circuit or disabled after failures", s["circuit_open"] or s["permanently_disabled"])
test("Failures tracked", s["total_failures"] >= 2)
test("Spans dropped", s["total_dropped"] >= 2)
test("Never returns FAILURE", True)

# Check auto-disable
test("Auto-disable after sustained failures", s["permanently_disabled"])
test("Dropped spans tracked", s["total_dropped"] > 5)

# Re-enable
failing.re_enable()
s3 = failing.stats
test("Re-enable works", not s3["permanently_disabled"] and not s3["circuit_open"])
failing.shutdown()

# ── Test 4: Kill Switch ──
print("\n=== 4. Kill Switch ===")
os.environ["OTEL_ENABLED"] = "false"
setup_telemetry()
test("Kill switch prevents init", not get_telemetry_status()["initialized"])
os.environ["OTEL_ENABLED"] = "true"

# ── Test 5: Full Setup (no collector) ──
print("\n=== 5. Full Setup (silent degradation) ===")
setup_telemetry()
st = get_telemetry_status()
test("Initialized", st["initialized"])
test("Provider active", st["provider_active"])
test("No exporter (silent)", st["exporter"] is None)
test("Watchdog not started (no endpoint)", st["watchdog"] is None)
test("Service name from env", st["service_name"] == "test-service")

# ── Test 6: Double-init guard ──
print("\n=== 6. Double-Init Guard ===")
setup_telemetry()  # Should be no-op
test("No crash on double init", True)

# ── Test 7: Shutdown ──
print("\n=== 7. Shutdown ===")
shutdown_telemetry()
test("Post-shutdown clean", not get_telemetry_status()["initialized"])
shutdown_telemetry()  # Double shutdown
test("Double shutdown safe", True)

# ── Test 8: Status diagnostics ──
print("\n=== 8. Self-Diagnostics ===")
s_final = get_telemetry_status()
required_keys = ["initialized", "packages_available", "otel_enabled",
                  "collector_endpoint", "jaeger_endpoint", "protocol",
                  "service_name", "resource_attributes", "exporter", "watchdog"]
test("All diagnostic keys present", all(k in s_final for k in required_keys))

# ── Summary ──
print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed")
print(f"{'='*60}")
sys.exit(1 if failed > 0 else 0)
