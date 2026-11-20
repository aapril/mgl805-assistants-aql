"""Measurement: the facts about the repository, computed without any model."""
import ast

from . import duplication, graph, metrics, safety
from .contracts import (
    Dependency,
    FunctionMetrics,
    Marker,
    Measurement,
    ModuleMetrics,
    Violation,
)


def _resolve(candidates, internal):
    """Internal modules named by one import: the imported modules, or else the longest internal prefix."""
    found = [c for c in candidates[:-1] if c in internal] if len(candidates) > 1 else []
    if found:
        return found
    parts = candidates[-1].split(".")
    prefix = next((".".join(parts[:k]) for k in range(len(parts), 0, -1) if ".".join(parts[:k]) in internal), None)
    return [prefix] if prefix else []


def run(repo, rules):
    root, files, skipped = safety.collect(repo, rules["limits"])
    th, cost = rules["thresholds"], rules["remediation_minutes"]
    parsed, parse_errors, sources = {}, [], {}
    for path in files:
        name = safety.module_name(root, path)
        source = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            parse_errors.append(f"{path.relative_to(root).as_posix()}: {exc.msg} (line {exc.lineno})")
            continue
        parsed[name] = (path, tree, path.name == "__init__.py")
        sources[name] = (source, metrics.code_lines(source))

    internal = set(parsed)
    deps, functions, markers, violations = [], [], [], []
    for name, (path, tree, is_pkg) in parsed.items():
        for candidates, line in metrics.imports(tree, name, is_pkg):
            for target in _resolve(candidates, internal):
                if target != name and not any(d.source == name and d.target == target for d in deps):
                    deps.append(Dependency(source=name, target=target, line=line))
        for qual, node in metrics.functions(tree):
            length = node.end_lineno - node.lineno + 1
            f = FunctionMetrics(module=name, name=qual, line=node.lineno, length=length, complexity=metrics.complexity(node))
            functions.append(f)
            if f.complexity > th["complexity"]:
                violations.append(Violation(kind="complexity", location=f"{name}:{qual}",
                                            detail=f"cyclomatic complexity {f.complexity} above {th['complexity']}",
                                            measured=f.complexity, threshold=th["complexity"],
                                            remediation_min=cost["complexity_point"] * (f.complexity - th["complexity"])))
            if f.length > th["function_lines"]:
                violations.append(Violation(kind="long_function", location=f"{name}:{qual}",
                                            detail=f"{f.length} lines, above {th['function_lines']}",
                                            measured=f.length, threshold=th["function_lines"],
                                            remediation_min=cost["long_function"]))
        for line, tag, text in metrics.markers(sources[name][0]):
            markers.append(Marker(id=len(markers) + 1, module=name, line=line, tag=tag, text=text))
            violations.append(Violation(kind="marker", location=f"{name}:{line}", detail=f"{tag}: {text}",
                                        remediation_min=cost["marker"]))

    edges = [(d.source, d.target) for d in deps]
    for d, a, b in graph.layer_violations(deps, rules.get("layers", {}), rules.get("allowed", {})):
        violations.append(Violation(kind="layer", location=f"{d.source}:{d.line}",
                                    detail=f"{d.source} ({a}) imports {d.target} ({b}); {a} may depend only on {rules['allowed'].get(a, [])}",
                                    remediation_min=cost["layer"]))
    found_cycles = graph.cycles(internal, edges)
    for c in found_cycles:
        violations.append(Violation(kind="cycle", location=c[0], detail="import cycle: " + " -> ".join(c + [c[0]]),
                                    measured=len(c), remediation_min=cost["cycle"]))
    blocks, dup_by_module = duplication.find(sources, th["duplicate_window"])
    for block in duplication.merge(blocks):
        where = ", ".join(f"{m} lines {s}-{e}" for m, s, e in block)
        violations.append(Violation(kind="duplicate_block", location=block[0][0], detail=f"duplicated code: {where}",
                                    measured=block[0][2] - block[0][1] + 1, remediation_min=cost["duplicate_block"]))

    couple = graph.coupling(internal, edges)
    modules = [ModuleMetrics(name=n, path=parsed[n][0].relative_to(root).as_posix(), lines=len(sources[n][1]),
                             layer=graph.layer_of(n, rules.get("layers", {})), fan_in=couple[n][0],
                             fan_out=couple[n][1], instability=couple[n][2]) for n in sorted(internal)]
    total = sum(m.lines for m in modules)
    dup = sum(dup_by_module.values())
    remediation = sum(v.remediation_min for v in violations)
    dev_cost = total * rules["development_minutes_per_line"]
    return Measurement(root=root.name, files=len(files), skipped=skipped, parse_errors=parse_errors, total_lines=total,
                       modules=modules, functions=sorted(functions, key=lambda f: (-f.complexity, f.module, f.line)),
                       dependencies=deps, cycles=found_cycles, duplicated_lines=dup,
                       duplication_pct=round(100 * dup / total, 2) if total else 0.0, markers=markers,
                       violations=violations, remediation_min=remediation,
                       debt_ratio_pct=round(100 * remediation / dev_cost, 2) if dev_cost else 0.0)
