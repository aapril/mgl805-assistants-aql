"""Performance requirements: the oracle, written by people, evaluated by rules.

Each SLO names a metric, a threshold, and the load at which it must hold. A
requirement measured at a lower load than required is neither met nor failed:
it is not measured, and a person must decide.
"""
import json
from pathlib import Path
from .contracts import SloResult


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["slos"]


def _value(m, slo):
    if slo.get("endpoint"):
        method, path = slo["endpoint"].split(" ", 1)
        ep = next((e for e in m.endpoints if e.method == method and e.path == path), None)
        if ep is None or ep.requests == 0:
            return None
        return getattr(ep, slo["metric"])
    return getattr(m, slo["metric"])


def evaluate(slos, measurement):
    results = []
    for s in slos:
        threshold = s.get("max", s.get("min"))
        if measurement is None:
            results.append(SloResult(id=s["id"], text=s["text"], status="not_measured", threshold=threshold))
            continue
        value = _value(measurement, s)
        too_light = measurement.scenario.virtual_users < s.get("at_virtual_users", 0)
        if value is None or too_light:
            results.append(SloResult(id=s["id"], text=s["text"], status="not_measured", measured=value, threshold=threshold))
            continue
        ok = value <= s["max"] if "max" in s else value >= s["min"]
        results.append(SloResult(id=s["id"], text=s["text"], status="met" if ok else "not_met",
                                 measured=value, threshold=threshold))
    return results
