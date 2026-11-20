"""Deterministic load generator: closed model, one thread per virtual user.

The measurements, not the model, are the evidence. The generator uses only the
standard library so that its behavior can be read and tested. For serious work,
replace it with Locust, k6, or JMeter and keep the same Measurement contract.
"""
import json
import random
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from .contracts import EndpointStats, Measurement


def percentile(values, p):
    if not values:
        return 0.0
    v = sorted(values)
    k = (len(v) - 1) * p / 100
    f, c = int(k), min(int(k) + 1, len(v) - 1)
    return round(v[f] + (v[c] - v[f]) * (k - f), 2)


def _call(target, step, timeout):
    data = json.dumps(step.body).encode() if step.body is not None else None
    req = urllib.request.Request(target.rstrip("/") + step.path, data=data, method=step.method,
                                 headers={"Content-Type": "application/json"} if data else {})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read()
            ok = 200 <= r.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        ok = False
    return (time.perf_counter() - start) * 1000, ok


def run(target, scenario, seed=7, timeout=10.0):
    lock = threading.Lock()
    samples = {(s.method, s.path): [] for s in scenario.steps}
    errors = {k: 0 for k in samples}
    weights = [s.weight for s in scenario.steps]
    deadline = time.monotonic() + scenario.duration_s

    def user(n):
        rng = random.Random(seed + n)  # reproducible request mix
        while time.monotonic() < deadline:
            step = rng.choices(scenario.steps, weights)[0]
            ms, ok = _call(target, step, timeout)
            with lock:
                samples[(step.method, step.path)].append(ms)
                if not ok:
                    errors[(step.method, step.path)] += 1
            if scenario.think_time_ms:
                time.sleep(scenario.think_time_ms / 1000)

    started = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()
    threads = [threading.Thread(target=user, args=(i,), daemon=True) for i in range(scenario.virtual_users)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.monotonic() - t0
    stats = []
    for (method, path), v in samples.items():
        n = len(v)
        stats.append(EndpointStats(method=method, path=path, requests=n, errors=errors[(method, path)],
                                   error_rate=round(errors[(method, path)] / n, 4) if n else 0.0,
                                   mean_ms=round(sum(v) / n, 2) if n else 0.0,
                                   p50_ms=percentile(v, 50), p95_ms=percentile(v, 95),
                                   p99_ms=percentile(v, 99), max_ms=round(max(v), 2) if v else 0.0))
    total = sum(s.requests for s in stats)
    errs = sum(s.errors for s in stats)
    return Measurement(target=target, scenario=scenario, started_at=started, elapsed_s=round(elapsed, 2),
                       total_requests=total, throughput_rps=round(total / elapsed, 2) if elapsed else 0.0,
                       error_rate=round(errs / total, 4) if total else 0.0, endpoints=stats)
