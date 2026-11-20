"""Safety: the analyzed code is data. It is read and parsed, never imported or run.

The agent reads only regular Python files under the repository root, without
following symbolic links, within the limits of the configuration. Every file
skipped is reported, so that a person knows what was not measured.
"""
import os
from pathlib import Path


def collect(root, limits):
    root = Path(root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Repository '{root}' is not a folder.")
    excluded = set(limits.get("exclude_dirs", []))
    files, skipped = [], []
    for folder, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in excluded and not (Path(folder) / d).is_symlink())
        for name in sorted(names):
            if not name.endswith(".py"):
                continue
            path = Path(folder) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                skipped.append(f"{rel}: symbolic link, not followed")
            elif path.stat().st_size > limits["max_file_bytes"]:
                skipped.append(f"{rel}: larger than max_file_bytes")
            elif len(files) >= limits["max_files"]:
                skipped.append(f"{rel}: beyond max_files")
            else:
                files.append(path)
    return root, files, skipped


def module_name(root, path):
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)
