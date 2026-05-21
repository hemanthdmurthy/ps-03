"""Deep endpoint diagnostics for localhost:4317"""
import socket
import sys
import os

print("=" * 70)
print("FULL ENDPOINT DIAGNOSTICS FOR localhost:4317")
print("=" * 70)

# 1. DNS Resolution
print("\n[1] DNS Resolution for 'localhost'")
print("-" * 50)
try:
    results = socket.getaddrinfo("localhost", 4317, socket.AF_UNSPEC, socket.SOCK_STREAM)
    for family, socktype, proto, canonname, sockaddr in results:
        fam = {socket.AF_INET: "IPv4", socket.AF_INET6: "IPv6"}.get(family, str(family))
        print(f"  {fam} -> {sockaddr}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. Socket probes
print("\n[2] TCP Socket Probe Matrix")
print("-" * 50)
probes = [
    ("127.0.0.1", 4317, "IPv4 gRPC"),
    ("127.0.0.1", 4318, "IPv4 HTTP"),
    ("localhost", 4317, "DNS gRPC"),
    ("localhost", 4318, "DNS HTTP"),
]
for host, port, label in probes:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        errno = s.connect_ex((host, port))
        s.close()
        if errno == 0:
            status = "OPEN (listening)"
        elif errno == 10061:
            status = "REFUSED (nothing listening)"
        else:
            status = f"ERROR (errno={errno})"
        print(f"  {label:20s} {host}:{port} -> {status}")
    except Exception as e:
        print(f"  {label:20s} {host}:{port} -> EXCEPTION: {e}")

# IPv6
print("\n[3] IPv6 Probes")
print("-" * 50)
for port in [4317, 4318]:
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.settimeout(2)
        errno = s.connect_ex(("::1", port))
        s.close()
        if errno == 0:
            status = "OPEN"
        elif errno == 10061:
            status = "REFUSED"
        else:
            status = f"ERROR({errno})"
        print(f"  [::1]:{port} -> {status} (errno={errno})")
    except Exception as e:
        print(f"  [::1]:{port} -> EXCEPTION: {e}")

# 3. Port collision scan
print("\n[4] Port Collision Analysis (4310-4320 range)")
print("-" * 50)
found_any = False
for port in range(4310, 4321):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        errno = s.connect_ex(("127.0.0.1", port))
        s.close()
        if errno == 0:
            print(f"  Port {port}: OPEN (something is listening)")
            found_any = True
    except:
        pass
if not found_any:
    print("  No ports in 4310-4320 range are open. Entire range is vacant.")

# 4. Exporter retry analysis
print("\n[5] Exporter Retry Behavior Analysis")
print("-" * 50)
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    
    e = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
    print(f"  Endpoint: {e._endpoint}")
    print(f"  Insecure: {e._insecure}")
    print(f"  Timeout:  {e._timeout}s")
    
    # BatchSpanProcessor defaults
    bsp = BatchSpanProcessor(e)
    print(f"  BSP max_queue_size:       {bsp.max_queue_size}")
    print(f"  BSP max_export_batch:     {bsp.max_export_batch_size}")
    print(f"  BSP schedule_delay_ms:    {bsp.schedule_delay_millis}")
    print(f"  BSP export_timeout_ms:    {bsp.export_timeout_millis}")
    
    bsp.shutdown()
    e.shutdown()
except Exception as ex:
    print(f"  ERROR: {ex}")

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
