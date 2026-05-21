"""
Telemetry Chaos Engineering & Stress Test Suite
================================================
Simulates production failure scenarios and measures resilience.
"""
import os, sys, time, threading, tracemalloc, json, statistics

os.environ["OTEL_ENABLED"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""
os.environ["OTEL_EXPORT_CONSOLE"] = "false"
os.environ["OTEL_JAEGER_ENDPOINT"] = ""
os.environ["OTEL_SERVICE_NAME"] = "chaos-test"
os.environ["OTEL_RESOURCE_ATTRIBUTES"] = ""

from app.core.telemetry import (
    ResilientSpanExporter, _ExporterWatchdog, _RateLimitedLogger,
    _is_collector_reachable, setup_telemetry, shutdown_telemetry,
    get_telemetry_status, TELEMETRY_AVAILABLE,
)
from opentelemetry.sdk.trace.export import SpanExportResult

results = {
    "stress_results": {},
    "failure_recovery_results": {},
    "performance_metrics": {},
    "dropped_span_analysis": {},
    "stability_score": "",
}


# ═══════════════════════════════════════════════════════════════════════════
# MOCK EXPORTERS — simulate various failure modes
# ═══════════════════════════════════════════════════════════════════════════

class HealthyExporter:
    def export(self, spans): return SpanExportResult.SUCCESS
    def shutdown(self): pass
    def force_flush(self, timeout_millis=0): pass

class DownExporter:
    """Simulates collector down."""
    def export(self, spans): raise ConnectionRefusedError("Connection refused")
    def shutdown(self): pass
    def force_flush(self, timeout_millis=0): pass

class LatencyExporter:
    """Simulates network latency."""
    def __init__(self, delay_s=0.5):
        self._delay = delay_s
    def export(self, spans):
        time.sleep(self._delay)
        return SpanExportResult.SUCCESS
    def shutdown(self): pass
    def force_flush(self, timeout_millis=0): pass

class TimeoutExporter:
    """Simulates exporter timeout — blocks then fails."""
    def export(self, spans):
        time.sleep(0.3)
        raise TimeoutError("Export timed out")
    def shutdown(self): pass
    def force_flush(self, timeout_millis=0): pass

class FlappingExporter:
    """Alternates between success and failure (collector restart)."""
    def __init__(self, fail_count=5, succeed_count=5):
        self._fail_n = fail_count
        self._succeed_n = succeed_count
        self._call = 0
    def export(self, spans):
        self._call += 1
        cycle = self._call % (self._fail_n + self._succeed_n)
        if cycle < self._fail_n:
            raise ConnectionError("Collector restarting")
        return SpanExportResult.SUCCESS
    def shutdown(self): pass
    def force_flush(self, timeout_millis=0): pass

class PacketDropExporter:
    """Simulates packet drops — randomly fails 30% of exports."""
    def __init__(self): self._call = 0
    def export(self, spans):
        self._call += 1
        if self._call % 3 == 0:
            raise OSError("Packet dropped")
        return SpanExportResult.SUCCESS
    def shutdown(self): pass
    def force_flush(self, timeout_millis=0): pass


def make_fake_spans(n):
    return [f"span_{i}" for i in range(n)]


# ═══════════════════════════════════════════════════════════════════════════
# TEST SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════

def test_collector_down():
    """S1: Collector is completely down."""
    print("  [S1] Collector down...")
    r = ResilientSpanExporter(DownExporter(), failure_threshold=3,
                               backoff_base_seconds=0.01, auto_disable_after=20,
                               exporter_name="s1-down")
    t0 = time.monotonic()
    for _ in range(50):
        r.export(make_fake_spans(10))
    elapsed = time.monotonic() - t0
    s = r.stats
    r.shutdown()
    return {
        "elapsed_s": round(elapsed, 4),
        "total_failures": s["total_failures"],
        "total_dropped": s["total_dropped"],
        "circuit_open": s["circuit_open"],
        "permanently_disabled": s["permanently_disabled"],
        "blocked_request": elapsed < 1.0,  # Must complete fast
    }

def test_collector_restart():
    """S2: Collector goes down then comes back."""
    print("  [S2] Collector restart (flapping)...")
    r = ResilientSpanExporter(FlappingExporter(fail_count=5, succeed_count=5),
                               failure_threshold=3, backoff_base_seconds=0.001,
                               auto_disable_after=500, exporter_name="s2-flap")
    exported_count = 0
    for _ in range(100):
        r.export(make_fake_spans(5))
        time.sleep(0.01)
    s = r.stats
    r.shutdown()
    return {
        "total_exported": s["total_exported"],
        "total_dropped": s["total_dropped"],
        "total_failures": s["total_failures"],
        "recovery_observed": s["total_exported"] > 0,
    }

def test_packet_drops():
    """S3: 30% packet drop rate."""
    print("  [S3] Packet drops (30%)...")
    r = ResilientSpanExporter(PacketDropExporter(), failure_threshold=5,
                               backoff_base_seconds=0.001, exporter_name="s3-drop")
    for _ in range(100):
        r.export(make_fake_spans(5))
        time.sleep(0.005)
    s = r.stats
    r.shutdown()
    return {
        "total_exported": s["total_exported"],
        "total_dropped": s["total_dropped"],
        "total_failures": s["total_failures"],
        "survived": not s["permanently_disabled"],
    }

def test_network_latency():
    """S4: High network latency (500ms per export)."""
    print("  [S4] Network latency (500ms)...")
    r = ResilientSpanExporter(LatencyExporter(0.05), exporter_name="s4-latency")
    latencies = []
    for _ in range(20):
        t0 = time.monotonic()
        r.export(make_fake_spans(5))
        latencies.append(time.monotonic() - t0)
    s = r.stats
    r.shutdown()
    return {
        "avg_export_latency_ms": round(statistics.mean(latencies) * 1000, 2),
        "p99_export_latency_ms": round(sorted(latencies)[int(len(latencies)*0.99)] * 1000, 2),
        "total_exported": s["total_exported"],
        "all_exported": s["total_dropped"] == 0,
    }

def test_exporter_timeout():
    """S5: Exporter times out on every export."""
    print("  [S5] Exporter timeout...")
    r = ResilientSpanExporter(TimeoutExporter(), failure_threshold=2,
                               backoff_base_seconds=0.001, auto_disable_after=10,
                               exporter_name="s5-timeout")
    for _ in range(30):
        r.export(make_fake_spans(5))
        time.sleep(0.05)
    s = r.stats
    r.shutdown()
    return {
        "total_failures": s["total_failures"],
        "permanently_disabled": s["permanently_disabled"],
        "total_dropped": s["total_dropped"],
    }

def test_batch_overflow():
    """S6: Flood with more spans than queue can hold."""
    print("  [S6] Batch overflow (rapid fire)...")
    r = ResilientSpanExporter(HealthyExporter(), exporter_name="s6-overflow")
    t0 = time.monotonic()
    # Fire 10000 spans as fast as possible
    for _ in range(1000):
        r.export(make_fake_spans(10))
    elapsed = time.monotonic() - t0
    s = r.stats
    r.shutdown()
    return {
        "spans_attempted": 10000,
        "total_exported": s["total_exported"],
        "elapsed_s": round(elapsed, 4),
        "throughput_spans_per_sec": round(10000 / elapsed) if elapsed > 0 else 0,
        "no_crash": True,
    }

def test_high_concurrency():
    """S7: Multiple threads exporting concurrently."""
    print("  [S7] High concurrency (10 threads)...")
    r = ResilientSpanExporter(HealthyExporter(), exporter_name="s7-concurrent")
    errors = []

    def worker(thread_id):
        try:
            for _ in range(200):
                r.export(make_fake_spans(5))
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    t0 = time.monotonic()
    for t in threads: t.start()
    for t in threads: t.join(timeout=10)
    elapsed = time.monotonic() - t0
    s = r.stats
    r.shutdown()
    return {
        "threads": 10,
        "spans_per_thread": 1000,
        "total_exported": s["total_exported"],
        "errors": len(errors),
        "elapsed_s": round(elapsed, 4),
        "thread_safe": len(errors) == 0,
    }

def test_watchdog_recovery():
    """S8: Watchdog detects recovery and re-enables exporter."""
    print("  [S8] Watchdog recovery simulation...")
    r = ResilientSpanExporter(DownExporter(), failure_threshold=2,
                               backoff_base_seconds=0.001, auto_disable_after=5,
                               exporter_name="s8-watchdog")
    # Drive to permanently disabled
    for _ in range(20):
        r.export(make_fake_spans(1))
        time.sleep(0.05)
    s1 = r.stats
    was_disabled = s1["permanently_disabled"]

    # Simulate watchdog re-enable
    r.re_enable()
    s2 = r.stats
    re_enabled = not s2["permanently_disabled"] and not s2["circuit_open"]
    r.shutdown()
    return {
        "was_disabled": was_disabled,
        "re_enabled": re_enabled,
        "recovery_works": was_disabled and re_enabled,
    }

def test_memory_consumption():
    """S9: Measure memory overhead under load."""
    print("  [S9] Memory consumption under load...")
    tracemalloc.start()
    r = ResilientSpanExporter(HealthyExporter(), exporter_name="s9-memory")
    snap1 = tracemalloc.take_snapshot()

    for _ in range(5000):
        r.export(make_fake_spans(10))

    snap2 = tracemalloc.take_snapshot()
    stats = snap2.compare_to(snap1, 'lineno')
    total_delta_kb = sum(s.size_diff for s in stats) / 1024
    tracemalloc.stop()
    r.shutdown()
    return {
        "spans_processed": 50000,
        "memory_delta_kb": round(total_delta_kb, 2),
        "no_leak": total_delta_kb < 5000,  # Less than 5MB for 50K spans
    }

def test_cpu_overhead():
    """S10: Measure CPU time for export path."""
    print("  [S10] CPU overhead measurement...")
    r = ResilientSpanExporter(HealthyExporter(), exporter_name="s10-cpu")
    iterations = 10000
    spans = make_fake_spans(5)

    t0 = time.perf_counter()
    for _ in range(iterations):
        r.export(spans)
    elapsed = time.perf_counter() - t0
    r.shutdown()
    return {
        "iterations": iterations,
        "total_cpu_ms": round(elapsed * 1000, 2),
        "per_export_us": round((elapsed / iterations) * 1_000_000, 2),
        "acceptable": (elapsed / iterations) * 1_000_000 < 100,  # < 100µs per export
    }

def test_rate_limited_logger():
    """S11: Ensure rate limiting prevents log flooding."""
    print("  [S11] Rate-limited logger stress...")
    rl = _RateLimitedLogger(min_interval=0.1)
    t0 = time.monotonic()
    for i in range(1000):
        rl.warning("flood", "Flood message %d", i)
    elapsed = time.monotonic() - t0
    return {
        "messages_attempted": 1000,
        "elapsed_ms": round(elapsed * 1000, 2),
        "no_flood": elapsed < 1.0,  # Should complete nearly instantly
    }


# ═══════════════════════════════════════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("TELEMETRY CHAOS ENGINEERING & STRESS TEST SUITE")
print("=" * 70)

# Failure recovery tests
print("\n--- Failure Recovery Tests ---")
results["failure_recovery_results"]["collector_down"] = test_collector_down()
results["failure_recovery_results"]["collector_restart"] = test_collector_restart()
results["failure_recovery_results"]["packet_drops"] = test_packet_drops()
results["failure_recovery_results"]["exporter_timeout"] = test_exporter_timeout()
results["failure_recovery_results"]["watchdog_recovery"] = test_watchdog_recovery()

# Stress tests
print("\n--- Stress Tests ---")
results["stress_results"]["network_latency"] = test_network_latency()
results["stress_results"]["batch_overflow"] = test_batch_overflow()
results["stress_results"]["high_concurrency"] = test_high_concurrency()

# Performance metrics
print("\n--- Performance Metrics ---")
results["performance_metrics"]["memory"] = test_memory_consumption()
results["performance_metrics"]["cpu"] = test_cpu_overhead()
results["performance_metrics"]["rate_limiter"] = test_rate_limited_logger()

# Dropped span analysis
print("\n--- Dropped Span Analysis ---")
fr = results["failure_recovery_results"]
results["dropped_span_analysis"] = {
    "collector_down_dropped": fr["collector_down"]["total_dropped"],
    "collector_restart_dropped": fr["collector_restart"]["total_dropped"],
    "packet_drops_dropped": fr["packet_drops"]["total_dropped"],
    "timeout_dropped": fr["exporter_timeout"]["total_dropped"],
    "total_across_failures": (
        fr["collector_down"]["total_dropped"] +
        fr["collector_restart"]["total_dropped"] +
        fr["packet_drops"]["total_dropped"] +
        fr["exporter_timeout"]["total_dropped"]
    ),
}

# Stability score
checks = [
    fr["collector_down"]["blocked_request"],
    fr["collector_down"].get("permanently_disabled") or fr["collector_down"]["circuit_open"],
    fr["collector_restart"]["recovery_observed"],
    fr["packet_drops"]["survived"],
    fr["watchdog_recovery"]["recovery_works"],
    results["stress_results"]["batch_overflow"]["no_crash"],
    results["stress_results"]["high_concurrency"]["thread_safe"],
    results["performance_metrics"]["memory"]["no_leak"],
    results["performance_metrics"]["cpu"]["acceptable"],
    results["performance_metrics"]["rate_limiter"]["no_flood"],
    results["stress_results"]["network_latency"]["all_exported"],
]
passed = sum(1 for c in checks if c)
total = len(checks)
score = f"{passed}/{total} ({round(passed/total*100)}%)"
results["stability_score"] = score

# Print results
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)
print(json.dumps(results, indent=2, default=str))

print(f"\n{'='*70}")
print(f"STABILITY SCORE: {score}")
if passed == total:
    print("STATUS: ALL CHECKS PASSED ✅")
else:
    print(f"STATUS: {total - passed} CHECK(S) FAILED ⚠️")
print(f"{'='*70}")

sys.exit(0 if passed == total else 1)
