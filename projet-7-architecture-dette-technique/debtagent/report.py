"""Reports: Markdown for people, JSON for evaluation and audit."""
from pathlib import Path

MARK = {"measured": " (names and numbers found in the measurement)", "partly": " (SOME NAMES OR NUMBERS NOT MEASURED)",
        "absent": " (NOT FOUND in the measurement)", "contradicts": " (CONTRADICTS the quality gates)", None: ""}
KINDS = ["layer", "cycle", "complexity", "long_function", "duplicate_block", "marker"]


def markdown(r):
    m = r.measurement
    types = {c.marker_id: c for c in r.classification.items}
    lines = ["# Architecture and technical debt report", "", f"Run `{r.run_id}` · model `{r.model}` · repository `{m.root}`", "",
             f"**Recommendation: {r.decision}**", "", "A person reviews the measurement and decides.", "",
             "## Reasons", ""] + [f"- {x}" for x in r.reasons]
    lines += ["", "## Quality gates", "", "| Id | Status | Measured | Threshold | Gate |", "|---|---|---:|---:|---|"]
    lines += [f"| {g.id} | {g.status} | {g.measured:g} | {g.threshold:g} | {g.text} |" for g in r.gates]
    lines += ["", "## Technical debt", "",
              (f"{m.files} files, {m.total_lines} lines of code, {len(m.modules)} modules, {len(m.functions)} functions. "
               f"Estimated remediation: {m.remediation_min} minutes ({m.remediation_min / 60:.1f} h); "
               f"debt ratio {m.debt_ratio_pct}%; duplicated lines {m.duplicated_lines} ({m.duplication_pct}%)."), "",
              "| Kind | Location | Detail | Minutes |", "|---|---|---|---:|"]
    for v in sorted(m.violations, key=lambda v: (KINDS.index(v.kind), v.location)):
        detail = v.detail.replace("|", "/")
        lines.append(f"| {v.kind} | {v.location} | {detail} | {v.remediation_min} |")
    lines += ["", "## Most complex functions", "", "| Function | Line | Lines | Complexity |", "|---|---:|---:|---:|"]
    lines += [f"| {f.module}:{f.name} | {f.line} | {f.length} | {f.complexity} |" for f in m.functions[:10]]
    lines += ["", "## Modules", "", "| Module | Layer | Lines | Fan-in | Fan-out | Instability |", "|---|---|---:|---:|---:|---:|"]
    lines += [f"| {x.name} | {x.layer or 'n/a'} | {x.lines} | {x.fan_in} | {x.fan_out} | {x.instability} |" for x in m.modules if x.lines > 1]
    if m.cycles:
        lines += ["", "## Import cycles", ""] + [f"- {' -> '.join(c + [c[0]])}" for c in m.cycles]
    if m.markers:
        lines += ["", "## Self-admitted debt (markers)", "", "| # | Location | Marker | Type (model) |", "|---:|---|---|---|"]
        for mk in m.markers:
            t = types.get(mk.id)
            text = mk.text.replace("|", "/")
            lines.append(f"| {mk.id} | {mk.module}:{mk.line} | {mk.tag}: {text} | {t.debt_type if t else 'unclassified'} |")
    lines += ["", "## Analysis (model)", "", r.analysis.summary, ""]
    for f in r.analysis.findings:
        lines += [f"- **{f.severity}: {f.title}** ({f.location})", f"  Evidence{MARK[f.grounded]}: {f.evidence}",
                  f"  Recommendation: {f.recommendation}"]
    lines += [f"- Program check: {x.removeprefix('Check: ')}" if x.startswith("Check: ") else f"- Model limitation: {x}"
              for x in r.analysis.limitations]
    return "\n".join(lines) + "\n"


def save(report, root="runs"):
    folder = Path(root) / report.run_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (folder / "report.md").write_text(markdown(report), encoding="utf-8")
    return folder
