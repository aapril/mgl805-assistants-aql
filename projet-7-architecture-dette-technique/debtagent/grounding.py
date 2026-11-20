"""Grounding: every name and number the model cites must come from the measurement,
and the model's verdict must agree with the quality gates.

The analyzed code is data, and it can talk to the model: the demo repository
holds a docstring that asks "AI reviewers" to report no technical debt. A
fluent analysis can also name a function that does not exist, quote a
complexity that was never measured, or declare a gate met when it failed. This
module checks the location, the names, the numbers, and the verdict of every
finding, and the verdict of the summary.
"""
import re

_NUM = re.compile(r"(?<![\w.\-])(\d+(?:\.\d+)?)\s*(%)?")
_TICK = re.compile(r"`([^`]{1,120})`")
_DOTTED = re.compile(r"\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\b")
_PATH = re.compile(r"\b([\w./-]+\.py)\b")
_CALL = re.compile(r"\b([A-Za-z_]\w*)\(\)")
_COMPLIES = re.compile(r"within (the )?threshold|below the threshold|\bmeets\b|\bis met\b|\bare met\b|acceptable|"
                       r"no action (is )?needed|compliant|\bno (layer )?violations?\b|\bno (import )?cycles?\b|"
                       r"well[- ](structured|designed)|follows the layered|respects? the (layer|rule)", re.IGNORECASE)
_FAILS = re.compile(r"exceed|not met|\bfails?\b|failing|above|violat|too (high|long|complex)|\bcycle (detected|between)|"
                    r"breaks?|should not", re.IGNORECASE)
_GLOBAL = re.compile(r"no (technical )?debt|recommend (its |the )?approval|ready for (approval|release|production)|"
                     r"approved by the architecture board", re.IGNORECASE)
KEYWORDS = {"layer_violations": ("layer",), "cycles": ("cycle", "circular"),
            "max_complexity": ("complexity",), "duplication_pct": ("duplicat",),
            "debt_ratio_pct": ("debt ratio",), "max_function_lines": ()}


def known_names(m, gates):
    names = {g.id for g in gates} | {"TODO", "FIXME", "HACK", "XXX"}
    for x in m.modules:
        names |= {x.name, x.name.rsplit(".", 1)[-1], x.path, x.path.rsplit("/", 1)[-1]}
        if x.layer:
            names.add(x.layer)
    for f in m.functions:
        short = f.name.rsplit(".", 1)[-1]
        names |= {f.name, short, f"{f.module}:{f.name}", f"{f.module}.{f.name}", f"{f.module.rsplit('.', 1)[-1]}.{f.name}"}
    return names


def known_numbers(m, gates):
    plain = {0.0, 1.0, float(m.files), float(m.total_lines), float(m.duplicated_lines), float(m.remediation_min),
             round(m.remediation_min / 60, 1), round(m.remediation_min / 60, 2), float(len(m.cycles)),
             float(len(m.markers)), float(len(m.violations)), float(len(m.modules)), float(len(m.functions))}
    percent = {m.duplication_pct, m.debt_ratio_pct}
    for x in m.modules:
        plain |= {float(x.lines), float(x.fan_in), float(x.fan_out), x.instability}
    for f in m.functions:
        plain |= {float(f.line), float(f.length), float(f.complexity)}
    for d in m.dependencies:
        plain.add(float(d.line))
    for v in m.violations:
        plain.add(float(v.remediation_min))
        plain |= {float(n) for n in re.findall(r"\d+(?:\.\d+)?", v.detail)}
    for mk in m.markers:
        plain |= {float(mk.line), float(mk.id)}
    for g in gates:
        plain.add(float(g.threshold))
        if g.measured is not None:
            plain.add(float(g.measured))
        if g.metric.endswith("_pct"):
            percent |= {float(g.threshold), float(g.measured or 0)}
    return plain, percent


def _matches(x, vals):
    return any(abs(x - v) <= max(0.01 * abs(v), 0.005) for v in vals)


def _known(name, names):
    n = name.strip().rstrip("()").split(":")[0] if re.search(r":\d+$", name.strip()) else name.strip().rstrip("()")
    return n in names


def cited_names(text):
    found = set(_TICK.findall(text)) | set(_DOTTED.findall(text)) | set(_PATH.findall(text)) | set(_CALL.findall(text))
    return {n for n in found if not re.fullmatch(r"[\d.]+|e\.g|i\.e", n)}


def contradiction(text, gates):
    for g in gates:
        named = g.id in text or any(k in text.lower() for k in KEYWORDS.get(g.metric, ()))
        if not named:
            continue
        if g.status == "not_met" and _COMPLIES.search(text) and not _FAILS.search(text):
            return f"says {g.id} is satisfied, but it was not met (measured {g.measured:g}, threshold {g.threshold:g})"
        if g.status == "met" and g.id in text and _FAILS.search(text) and not _COMPLIES.search(text):
            return f"says {g.id} fails, but it was met (measured {g.measured:g}, threshold {g.threshold:g})"
    failed = [g.id for g in gates if g.status == "not_met"]
    if failed and _GLOBAL.search(text):
        return f"recommends approval or reports no debt, but {', '.join(failed)} failed"
    return None


def location_contradiction(location, text, m):
    """The finding calls a module compliant, but the measurement found violations in it."""
    module = location.strip().split(":")[0]
    found = [v for v in m.violations if v.location.split(":")[0] == module and v.kind != "marker"]
    if found and _COMPLIES.search(text) and not _FAILS.search(text):
        return f"calls {module} compliant, but the measurement found {len(found)} violation(s) in it ({', '.join(sorted({v.kind for v in found}))})"
    return None


def _norm(text):
    return re.sub(r"\s+", " ", text).strip().lower().rstrip(".")


def quoted_marker(evidence, m):
    """The marker whose comment the evidence quotes, if any."""
    e = _norm(evidence)
    for mk in m.markers:
        if len(mk.text) >= 12 and _norm(mk.text) in e:
            return mk
    return None


def restated_gate(text, gates):
    """The text states a failed gate's property as if it held, e.g. 'The technical debt ratio is below 5%.'"""
    t = _norm(text)
    for g in gates:
        if g.status == "not_met" and _norm(g.text) in t:
            return f"states '{g.text}' as a fact, but {g.id} was not met (measured {g.measured:g}, threshold {g.threshold:g})"
    return None


_GENERIC = {"issue", "issues", "problem", "design", "code", "test", "tests", "defect", "documentation", "debt",
            "technical", "high", "medium", "low", "finding", "module", "function"}


def title_mismatch(f):
    """The title names a subject that its evidence never mentions."""
    words = {w for w in re.findall(r"[a-z]{5,}", f.title.lower()) if w not in _GENERIC}
    body = f.evidence.lower()
    if words and not any(w[:5] in body for w in words):
        return f"title '{f.title[:60]}' does not match its evidence"
    return None


def check(analysis, m, gates):
    """Mark every finding; check the summary and the model's own limitations. Return the verdict problems."""
    names, (plain, percent) = known_names(m, gates), known_numbers(m, gates)
    model_limits, notes = list(analysis.limitations), []
    for f in analysis.findings:
        f.source = "model"
        f.grounded = None  # never trust a value written by the model
        text = f"{f.title} {f.evidence}"
        cited = [(float(n), u) for n, u in _NUM.findall(f.evidence)]
        bad_numbers = [f"{x:g}{u}" for x, u in cited if not _matches(x, percent if u else plain | percent)]
        mentioned = cited_names(f.evidence)
        bad_names = sorted(n for n in mentioned if not _known(n, names))
        location_ok = _known(f.location, names)
        marker = quoted_marker(f.evidence, m)
        if marker:  # a quoted debt comment is evidence, but only at its own place
            module, _, line = f.location.strip().partition(":")
            if module != marker.module or (line and line != str(marker.line)):
                bad_names.append(f"location {f.location} (the quoted {marker.tag} is at {marker.module}:{marker.line})")
            mentioned = mentioned | {marker.module}
        mismatch = title_mismatch(f)
        if mismatch:
            bad_names.append(mismatch)
        why = contradiction(text, gates) or location_contradiction(f.location, text, m) or restated_gate(text, gates)
        if why:
            f.grounded = "contradicts"
            notes.append(f"Check: finding '{f.title[:80]}' {why}.")
        elif not cited and not mentioned:
            f.grounded = "absent"
            notes.append(f"Check: finding '{f.title[:80]}': its evidence cites no measured name, number, or debt comment.")
        elif not location_ok or (mentioned and len(bad_names) >= len(mentioned) and not marker) or (cited and len(bad_numbers) == len(cited)):
            f.grounded = "absent"
        elif bad_names or bad_numbers:
            f.grounded = "partly"
        else:
            f.grounded = "measured"
        problems = ([] if location_ok else [f"location {f.location}"]) + bad_names + bad_numbers
        if f.grounded in ("absent", "partly") and problems:
            notes.append(f"Check: finding '{f.title[:80]}': not found in the measurement: {', '.join(problems)}.")
    issues = []
    why = contradiction(analysis.summary, gates) or restated_gate(analysis.summary, gates)
    if why:
        issues.append(f"Check: the summary {why}.")
    for limit in model_limits:
        why = contradiction(limit, gates) or restated_gate(limit, gates)
        if why:
            issues.append(f"Check: the model's limitation '{limit[:80]}' {why}.")
    analysis.limitations.extend(notes + issues)
    return issues


def check_classification(classification, m):
    """Keep one class per known marker; report invented or missing markers."""
    ids, kept, notes = {mk.id for mk in m.markers}, {}, []
    for item in classification.items:
        if item.marker_id not in ids:
            notes.append(f"Check: classification of marker {item.marker_id} removed: no such marker.")
        elif item.marker_id not in kept:
            kept[item.marker_id] = item
    classification.items = [kept[i] for i in sorted(kept)]
    missing = sorted(ids - set(kept))
    if missing and classification.items:
        notes.append(f"Check: markers not classified by the model: {', '.join(map(str, missing))}.")
    return notes
