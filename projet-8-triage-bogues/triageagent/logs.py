"""Log parsing: records, tracebacks, signatures, deployments. No model.

A record starts with an ISO timestamp and a level; the lines that follow,
such as a Python traceback, belong to it. Records of the same level,
exception, normalized message, and innermost frame in the repository form one
signature. Request identifiers, numbers, and quoted user input are normalized,
so that "Slow search (2.4 s)" and "Slow search (3.1 s)" count as one problem.
"""
import re

from .contracts import Frame, Signature

_START = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (DEBUG|INFO|WARNING|ERROR|CRITICAL) (\S+) ?(.*)$")
_FRAME = re.compile(r'^\s+File "([^"]+)", line (\d+), in (\S+)')
_EXC = re.compile(r"^([A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt|Timeout))(?:: (.*))?$")
_SUSPICIOUS = re.compile(r"ignore (all |any |the )?(previous |prior |above )?instructions|note to the ai|ai (triage )?assistant|"
                         r"you are (now )?(the|an?) |system prompt|attribute (every|all) errors?|report no regression|"
                         r"mark (all|every) .{0,20}(resolved|fixed)", re.IGNORECASE)


def normalize(text):
    text = re.sub(r"request_id=\S+\s*", "", text)
    text = re.sub(r'"[^"]*"|\'[^\']*\'', "<str>", text)
    return re.sub(r"\d+(\.\d+)?", "<n>", text).strip()


def records(text):
    out = []
    for line in text.splitlines():
        m = _START.match(line)
        if m:
            out.append({"time": m.group(1), "level": m.group(2), "logger": m.group(3), "message": m.group(4), "lines": [line]})
        elif out:
            out[-1]["lines"].append(line)
    return out


def frames(lines, prefixes):
    found = []
    for i, line in enumerate(lines):
        m = _FRAME.match(line)
        if m:
            path = m.group(1)
            for p in prefixes:
                if path.startswith(p):
                    path = path[len(p):]
                    break
            code = lines[i + 1].strip() if i + 1 < len(lines) and not _FRAME.match(lines[i + 1]) else ""
            found.append(Frame(file=path, line=int(m.group(2)), function=m.group(3), code=code))
    return found


def exception(lines):
    for line in reversed(lines[1:]):
        m = _EXC.match(line)
        if m:
            return m.group(1), (m.group(2) or "")
    return None, None


def deployments(recs, pattern):
    rx = re.compile(pattern)
    return [(r["time"], m.group("ref")) for r in recs if r["level"] == "INFO" and (m := rx.search(r["message"]))]


def signatures(recs, prefixes, deploy_time, limit):
    groups = {}
    for r in recs:
        if r["level"] not in ("WARNING", "ERROR", "CRITICAL"):
            continue
        fr = frames(r["lines"], prefixes)
        exc, exc_msg = exception(r["lines"])
        in_repo = [f for f in fr if not f.file.startswith("/")]
        place = f"{in_repo[-1].file}:{in_repo[-1].function}" if in_repo else r["logger"]
        message = f"{exc}: {exc_msg}" if exc else normalize(r["message"])
        key = (r["level"], exc, message, place)
        g = groups.setdefault(key, {"level": r["level"], "exception": exc, "message": message, "frames": fr,
                                    "times": [], "sample": "\n".join(r["lines"])[:1500], "suspicious": set()})
        g["times"].append(r["time"])
        for m in _SUSPICIOUS.finditer("\n".join(r["lines"])):
            g["suspicious"].add(m.group(0))
    ordered = sorted(groups.values(), key=lambda g: min(g["times"]))[:limit]
    out = []
    for i, g in enumerate(ordered, 1):
        before = sum(1 for t in g["times"] if deploy_time and t < deploy_time)
        out.append(Signature(id=f"S{i}", level=g["level"], exception=g["exception"], message=g["message"], frames=g["frames"],
                             count=len(g["times"]), count_before_deploy=before, count_after_deploy=len(g["times"]) - before,
                             first_seen=min(g["times"]), last_seen=max(g["times"]), sample=g["sample"],
                             suspicious=sorted(g["suspicious"])))
    return out
