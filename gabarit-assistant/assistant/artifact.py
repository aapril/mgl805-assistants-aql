"""The artifact under assessment and its reference (the oracle).

Both are UNTRUSTED text: they may contain instructions aimed at the model
(book Section 5.2.1.4). The digest binds the evidence to the exact files.
"""
import hashlib
from pathlib import Path


def load(paths):
    """Return {path: text} for the given files, in a stable order."""
    return {str(p): Path(p).read_text(encoding="utf-8") for p in sorted(map(str, paths))}


def digest(files: dict) -> str:
    h = hashlib.sha256()
    for path, text in sorted(files.items()):
        h.update(path.encode() + b"\0" + text.encode() + b"\0")
    return h.hexdigest()


def as_text(files: dict) -> str:
    return "\n".join(f"===== {path} =====\n{text}" for path, text in files.items())
