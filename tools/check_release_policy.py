"""Validate the immutable version identity for a prospective release."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

STABLE_VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")


def _project_version(path: Path) -> str:
    in_project = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_project = stripped == "[project]"
            continue
        if in_project:
            key, separator, value = stripped.partition("=")
            if separator and key.strip() == "version":
                return value.strip().strip('"\'')
    raise ValueError("pyproject.toml must contain project.version")


def _citation_version(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "version":
            return value.strip().strip('"\'')
    raise ValueError("CITATION.cff must contain a top-level version")


def check_release_identity(project_root: Path, *, tag: str | None = None) -> str:
    """Return the package version after checking release identity invariants."""

    version = _project_version(project_root / "pyproject.toml")
    if STABLE_VERSION.fullmatch(version) is None:
        raise ValueError(f"project version must use stable X.Y.Z form, got {version!r}")

    citation_version = _citation_version(project_root / "CITATION.cff")
    if citation_version != version:
        raise ValueError(
            f"CITATION.cff version {citation_version!r} does not match project version {version!r}"
        )

    if tag is not None and tag != f"v{version}":
        raise ValueError(f"release tag must be exactly v{version}, got {tag!r}")
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--tag")
    arguments = parser.parse_args()
    tag = arguments.tag
    if tag is None and os.environ.get("GITHUB_REF_TYPE") == "tag":
        tag = os.environ.get("GITHUB_REF_NAME")
    version = check_release_identity(arguments.project_root, tag=tag)
    print(f"release identity valid for version {version}")


if __name__ == "__main__":
    main()
