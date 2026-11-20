"""Numeric grounding: every number the model cites must be a measured number,
in the right unit, and the model's verdict must agree with the requirements.

A fluent analysis can quote a latency that was never measured, give a measured
rate in the wrong unit, or quote the right number with the wrong conclusion.
On November 20, 2026, qwen2.5-coder:1.5b wrote that "the reservation failure
rate is 0.0249%, which is within the threshold": the number was measured, but
it is a fraction (2.49%), and the requirement (< 1%) had failed. This module
checks the numbers, their units, the endpoint paths, and the verdict.
"""
import re

_NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(%|ms|s\b|rps|req/s)?", re.I)
_PATH = re.compile(r"(?<![\w])(/[A-Za-z0-9_\-/?=&.]*)")
_COMPLIES = re.compile(r"within (the )?threshold|below the threshold|meets|\bis met\b|acceptable|no action needed|as expected|performing well", re.I)
_FAILS = re.compile(r"exceed|not met|\bfails?\b|failing|above the threshold|violat|too slow", re.I)
RATE_METRICS = {"error_rate"}


def known_values(measurement, slos, scenario):
    """Return (plain, percent): values as measured, and rates expressed in percent."""
    plain, percent = set(), {50.0, 95.0, 99.0}  # percentile names, not measurements
    if measurement:
        plain.update(float(getattr(measurement, f)) for f in ("elapsed_s", "total_requests", "throughput_rps"))
        plain.add(measurement.error_rate)
        percent.add(round(measurement.error_rate * 100, 4))
        for e in measurement.endpoints:
            plain.update(float(getattr(e, f)) for f in ("requests", "errors", "mean_ms", "p50_ms", "p95_ms", "p99_ms", "max_ms"))
            plain.add(e.error_rate)
            percent.add(round(e.error_rate * 100, 4))
    for s in slos:
        plain.add(float(s.threshold))
        percent.add(round(float(s.threshold) * 100, 4))
        if s.measured is not None:
            plain.add(float(s.measured))
    plain.update({float(scenario.virtual_users), float(scenario.duration_s), float(scenario.think_time_ms), 50.0, 95.0, 99.0})
    return plain, percent


def _matches(x, vals):
    return any(abs(x - v) <= max(0.02 * abs(v), 0.01) for v in vals)


def _contradiction(text, numbers, slos):
    """The finding cites the measured value of a requirement and states the opposite verdict."""
    for s in slos:
        if s.measured is None or s.status == "not_measured":
            continue
        cited = any(abs(x - s.measured) <= max(0.02 * abs(s.measured), 0.0001) for x in numbers)
        if not cited:
            continue
        if s.status == "not_met" and _COMPLIES.search(text) and not _FAILS.search(text):
            return f"says {s.id} is satisfied, but it was not met (measured {s.measured}, threshold {s.threshold})"
        if s.status == "met" and _FAILS.search(text) and not _COMPLIES.search(text):
            return f"says {s.id} fails, but it was met (measured {s.measured}, threshold {s.threshold})"
    return None


def check(analysis, measurement, slos, scenario, catalog_paths):
    plain, percent = known_values(measurement, slos, scenario)
    for f in analysis.findings:
        f.source = "model"
        f.grounded = None  # never trust a value written by the model
        cited = [(float(n), (u or "").lower()) for n, u in _NUM.findall(f.evidence)]
        paths = [p.split("?")[0] for p in _PATH.findall(f.evidence) if len(p) > 1]
        bad_paths = [p for p in paths if p not in catalog_paths]
        if not cited and not paths:
            continue
        unmatched = [f"{x}{u}" for x, u in cited if not _matches(x, percent if u == "%" else plain)]
        contradiction = _contradiction(" ".join([f.title, f.evidence, f.recommendation]), [x for x, _ in cited], slos)
        if contradiction:
            f.grounded = "contradicts"
            analysis.limitations.append(f"Finding '{f.title[:80]}' {contradiction}.")
        elif bad_paths or (cited and len(unmatched) == len(cited)):
            f.grounded = "absent"
        elif unmatched:
            f.grounded = "partly"
        else:
            f.grounded = "measured"
        if f.grounded in ("absent", "partly") or (unmatched and f.grounded == "contradicts"):
            analysis.limitations.append(f"Finding '{f.title[:80]}': not found in the measurements, or in another unit: {', '.join(unmatched + bad_paths)}.")
    return analysis
