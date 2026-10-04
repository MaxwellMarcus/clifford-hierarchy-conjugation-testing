from __future__ import annotations

import runpy
import subprocess
from pathlib import Path

import pytest

check_tag_provenance = runpy.run_path(
    str(Path(__file__).parents[1] / "tools" / "check_tag_provenance.py")
)["check_tag_provenance"]


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(root), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _signed_repository(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repository"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Release Test")
    _git(root, "config", "user.email", "release@example.test")
    (root / "payload.txt").write_text("release\n", encoding="utf-8")
    _git(root, "add", "payload.txt")
    _git(root, "commit", "-m", "release")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")

    key = tmp_path / "release_signing_key"
    subprocess.run(
        ("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)),
        check=True,
    )
    public_key = key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    allowed_signers = tmp_path / "allowed_signers"
    allowed_signers.write_text(f"release@example.test {public_key}\n", encoding="utf-8")
    return root, key, allowed_signers


def _sign_tag(root: Path, key: Path, tag: str) -> None:
    _git(
        root,
        "-c",
        "gpg.format=ssh",
        "-c",
        f"user.signingkey={key}",
        "tag",
        "-s",
        "-m",
        tag,
        tag,
    )


def test_approved_signed_tag_on_main_is_accepted(tmp_path: Path) -> None:
    root, key, allowed_signers = _signed_repository(tmp_path)
    _sign_tag(root, key, "v1.2.3")

    assert check_tag_provenance(
        root,
        tag="v1.2.3",
        allowed_signers=allowed_signers,
    ) == _git(root, "rev-parse", "HEAD")


def test_lightweight_tag_is_rejected(tmp_path: Path) -> None:
    root, _, allowed_signers = _signed_repository(tmp_path)
    _git(root, "tag", "v1.2.3")

    with pytest.raises(ValueError, match="annotated"):
        check_tag_provenance(root, tag="v1.2.3", allowed_signers=allowed_signers)


def test_signed_tag_off_main_is_rejected(tmp_path: Path) -> None:
    root, key, allowed_signers = _signed_repository(tmp_path)
    _git(root, "switch", "-c", "side")
    (root / "side.txt").write_text("not on main\n", encoding="utf-8")
    _git(root, "add", "side.txt")
    _git(root, "commit", "-m", "side release")
    _sign_tag(root, key, "v1.2.3")

    with pytest.raises(ValueError, match="not reachable"):
        check_tag_provenance(root, tag="v1.2.3", allowed_signers=allowed_signers)


def test_unapproved_signing_key_is_rejected(tmp_path: Path) -> None:
    root, key, _ = _signed_repository(tmp_path)
    _sign_tag(root, key, "v1.2.3")
    other_key = tmp_path / "other_key"
    subprocess.run(
        ("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(other_key)),
        check=True,
    )
    other_public = other_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    allowed_signers = tmp_path / "other_allowed_signers"
    allowed_signers.write_text(f"other@example.test {other_public}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not approved"):
        check_tag_provenance(root, tag="v1.2.3", allowed_signers=allowed_signers)
