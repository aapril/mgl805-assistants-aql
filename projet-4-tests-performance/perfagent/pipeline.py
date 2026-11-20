"""Fixed order: plan, clamp, measure, evaluate, explain, ground, decide."""
from datetime import datetime, timezone
from uuid import uuid4
from . import grounding, loadgen, safety, slo as slo_mod
from .contracts import Analysis, Report


def run(config, requirements_text, slos, target, model, seed=7):
    safety.check_target(target, config)  # before anything else, and before any model
    payload = {"requirements_text": requirements_text, "requirements": slos,
               "catalog": config["catalog"], "limits": config["limits"],
               "default_duration_s": config["limits"]["default_duration_s"]}
    proposed = model.plan(payload)
    executed, adjustments = safety.clamp(proposed, config)
    measurement = loadgen.run(target, executed, seed=seed)
    results = slo_mod.evaluate(slos, measurement)
    try:
        analysis = model.analyze({"requirements": [r.model_dump() for r in results],
                                  "measurement": measurement.model_dump()})
    except Exception as exc:  # a failed explanation never hides the measurements
        analysis = Analysis(summary="Analysis not completed.",
                            limitations=[f"Failure {type(exc).__name__}: {str(exc)[:200]}"])
    catalog_paths = {e["path"].split("?")[0] for e in config["catalog"]}
    grounding.check(analysis, measurement, results, executed, catalog_paths)
    from .decision import decide
    decision, reasons = decide(measurement, results, analysis, adjustments)
    return Report(run_id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(), model=model.name,
                  proposed=proposed, executed=executed, adjustments=adjustments, measurement=measurement,
                  slos=results, analysis=analysis, decision=decision, reasons=reasons)
