"""Safety limits: enforced by the program, whatever the model proposes.

A load test is a controlled denial of service. The planner can only choose
among the endpoints of the catalog, against a target of the allowlist, within
the limits of the configuration. Every adjustment is reported.
"""
from urllib.parse import urlparse
from .contracts import Scenario


class UnsafeTarget(ValueError):
    pass


def check_target(target: str, config: dict):
    host = urlparse(target).hostname or ""
    if host not in config["allowed_hosts"]:
        raise UnsafeTarget(f"Target host '{host}' is not in allowed_hosts; refusing to send any request.")


def clamp(scenario: Scenario, config: dict):
    limits, catalog = config["limits"], {(e["method"], e["path"]) for e in config["catalog"]}
    s = scenario.model_copy(deep=True)
    notes = []
    kept = [st for st in s.steps if (st.method, st.path) in catalog]
    for st in s.steps:
        if (st.method, st.path) not in catalog:
            notes.append(f"Removed step {st.method} {st.path}: not in the endpoint catalog.")
    if not kept:
        raise ValueError("No step of the proposed scenario is in the endpoint catalog.")
    s.steps = kept
    for field, key in (("virtual_users", "max_virtual_users"), ("duration_s", "max_duration_s")):
        if getattr(s, field) > limits[key]:
            notes.append(f"{field} reduced from {getattr(s, field)} to {limits[key]} (limit {key}).")
            setattr(s, field, limits[key])
    return s, notes
