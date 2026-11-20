"""Duplicated code: identical windows of normalized code lines in two places.

Lines are stripped of indentation and comments; blank lines, comment lines and
import lines are ignored. A window of N consecutive lines that appears more
than once marks all its lines as duplicated. Renamed functions do not hide a
copy, because the def line is only one line of the window.
"""
import hashlib


def _normalized(source, code):
    out = []
    for i, line in enumerate(source.splitlines(), 1):
        text = line.split("#", 1)[0].strip() if "#" in line and "'" not in line and '"' not in line else line.strip()
        if i in code and text and not text.startswith(("import ", "from ")):
            out.append((i, text))
    return out


def find(sources, window):
    """sources: {module: (source, code line numbers)}. Returns (blocks, duplicated lines per module)."""
    seen = {}
    for module, (source, code) in sources.items():
        lines = _normalized(source, code)
        for k in range(len(lines) - window + 1):
            chunk = lines[k:k + window]
            text = "\n".join(t for _, t in chunk)
            if len(text) < 80:  # too short to matter
                continue
            seen.setdefault(hashlib.sha1(text.encode()).hexdigest(), []).append((module, chunk[0][0], chunk[-1][0]))
    duplicated = {m: set() for m in sources}
    blocks = []
    for places in seen.values():
        if len(places) < 2:
            continue
        for module, start, end in places:
            duplicated[module].update(range(start, end + 1))
        blocks.append(places)
    return blocks, {m: len(v & sources[m][1]) for m, v in duplicated.items()}


def merge(blocks):
    """Merge overlapping windows into one block per pair of places."""
    merged = {}
    for places in blocks:
        key = tuple(sorted(m for m, _, _ in places))
        for m, s, e in places:
            spans = merged.setdefault(key, {}).setdefault(m, [])
            if spans and s <= spans[-1][1] + 1:
                spans[-1] = (spans[-1][0], max(spans[-1][1], e))
            else:
                spans.append((s, e))
    result = []
    for key, by_module in merged.items():
        count = min(len(v) for v in by_module.values())
        for i in range(count):
            result.append([(m, *by_module[m][i]) for m in sorted(by_module)])
    return result
