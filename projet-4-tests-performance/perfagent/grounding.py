"""Numeric grounding: every number the model cites must be a measured number.

A fluent analysis can quote a latency that was never measured. This module
extracts the numbers and endpoint paths of each finding and checks them
against the measurement, the requirements, and the executed scenario.
"""
import re

_NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(%|ms|s|rps|req/s)?", re.I)
_PATH = re.compile(r"(?<![\w])(/[A-Za-z0-9_\-/?=&.]*)")


def known_values(measurement, slos, scenario):
    vals = set()
    if measurement:
        for f in ("elapsed_s", "total_requests", "throughput_rps"):
            vals.add(float(getattr(measurement, f)))
        vals.add(measurement.error_rate * 100)
        vals.add(measurement.error_rate)
        for e in measurement.endpoints:
            for f in ("requests", "errors", "mean_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"):
                vals.add(float(getattr(e, f)))
            vals.add(e.error_rate * 100)
            vals.add(e.error_rate)
    for s in slos:
        vals.add(float(s.threshold))
        if s.measured is not None:
            vals.add(float(s.measured))
    vals.update({float(scenario.virtual_users), float(scenario.duration_s), float(scenario.think_time_ms)})
    for n in (50, 95, 99):  # percentile names, not measurements
        vals.add(float(n))
    return vals


def _matches(x, vals):
    return any(abs(x - v) <= max(1.0, 0.02 * abs(v)) for v in vals)


def check(analysis, measurement, slos, scenario, catalog_paths):
    vals = known_values(measurement, slos, scenario)
    for f in analysis.findings:
        f.source = "model"
        f.grounded = None  # never trust a value written by the model
        numbers = [float(n) for n, _ in _NUM.findall(f.evidence)]
        paths = [p.split("?")[0] for p in _PATH.findall(f.evidence) if len(p) > 1]
        bad_paths = [p for p in paths if p not in catalog_paths]
        if not numbers and not paths:
            continue
        matched = [x for x in numbers if _matches(x, vals)]
        unmatched = [x for x in numbers if not _matches(x, vals)]
        if bad_paths or (numbers and not matched):
            f.grounded = "absent"
        elif unmatched:
            f.grounded = "partly"
        else:
            f.grounded = "measured"
        if f.grounded != "measured":
            what = ", ".join([str(x) for x in unmatched] + bad_paths)
            analysis.limitations.append(f"Finding '{f.title[:80]}': not found in the measurements: {what}.")
    return analysis
