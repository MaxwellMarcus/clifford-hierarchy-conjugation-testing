"""Verify that a release tag is annotated, approved, and on ``origin/main``."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _git(
    project_root: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(project_root), *arguments),
        check=check,
        capture_output=True,
        text=True,
    )


def check_tag_provenance(
    project_root: Path,
    *,
    tag: str,
    main_ref: str = "origin/main",
    allowed_signers: Path | None = None,
) -> str:
    """Return the tagged commit after signature and main-history verification."""

    if not tag or tag.startswith("-"):
        raise ValueError("tag must be a nonempty ref name")
    signers = allowed_signers or project_root / ".github" / "release-signers"
    if not signers.is_file():
        raise ValueError(f"approved signer allowlist does not exist: {signers}")

    tag_ref = f"refs/tags/{tag}"
    object_type = _git(project_root, "cat-file", "-t", tag_ref, check=False)
    if object_type.returncode != 0:
        raise ValueError(f"release tag does not exist: {tag}")
    if object_type.stdout.strip() != "tag":
        raise ValueError(f"release tag must be annotated, got {object_type.stdout.strip()!r}")

    verification = _git(
        project_root,
        "-c",
        "gpg.format=ssh",
        "-c",
        f"gpg.ssh.allowedSignersFile={signers.resolve()}",
        "verify-tag",
        "--raw",
        tag_ref,
        check=False,
    )
    if verification.returncode != 0:
        detail = verification.stderr.strip() or verification.stdout.strip()
        raise ValueError(f"release tag signature is not approved: {detail}")

    commit = _git(project_root, "rev-parse", f"{tag_ref}^{{commit}}").stdout.strip()
    ancestry = _git(
        project_root,
        "merge-base",
        "--is-ancestor",
        commit,
        main_ref,
        check=False,
    )
    if ancestry.returncode == 1:
        raise ValueError(f"release commit {commit} is not reachable from {main_ref}")
    if ancestry.returncode != 0:
        detail = ancestry.stderr.strip() or ancestry.stdout.strip()
        raise ValueError(f"could not verify {main_ref} ancestry: {detail}")
    return commit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--tag", required=True)
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument("--allowed-signers", type=Path)
    arguments = parser.parse_args()
    commit = check_tag_provenance(
        arguments.project_root,
        tag=arguments.tag,
        main_ref=arguments.main_ref,
        allowed_signers=arguments.allowed_signers,
    )
    print(f"approved signed release tag {arguments.tag} points to {commit} on {arguments.main_ref}")


if __name__ == "__main__":
    main()
