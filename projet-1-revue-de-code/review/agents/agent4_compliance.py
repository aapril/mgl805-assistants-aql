"""Agent 4: requirements-to-evidence matrix, without a legal verdict."""
from .common import analyze, code_payload
from ..models import Criterion


def run(context, model, requirements):
    payload = code_payload(context)
    payload["requirements"] = [{"id": c.id, "text": c.text} for c in requirements.criteria]
    result = analyze(model, 4,
        "Compare each criterion with the diff. Reuse the identifiers and texts exactly. "
        "supported means backed by the visible code, not validated in operation. "
        "not_met requires an explicit contradiction; otherwise use unknown. Cite evidence for each conclusion.", payload)
    # Criteria lost by the model become unknown again; they never disappear.
    by_id = {c.id: c for c in result.criteria}
    result.criteria = [Criterion(id=c.id, text=c.text,
        status=by_id[c.id].status if c.id in by_id and by_id[c.id].evidence.strip() else "unknown",
        evidence=by_id[c.id].evidence if c.id in by_id else "Criterion not evaluated by the model") for c in requirements.criteria]
    return result
