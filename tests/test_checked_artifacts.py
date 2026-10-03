import hashlib
import runpy
from pathlib import Path

import pytest

check_checked_artifacts = runpy.run_path(
    str(Path(__file__).parents[1] / "tools" / "check_checked_artifacts.py")
)["check_checked_artifacts"]


def _write_checked_artifacts(dist_dir: Path) -> tuple[Path, Path]:
    dist_dir.mkdir()
    wheel = dist_dir / "example-1.2.3-py3-none-any.whl"
    sdist = dist_dir / "example-1.2.3.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    (dist_dir / "SHA256SUMS").write_text(
        f"{hashlib.sha256(wheel.read_bytes()).hexdigest()}  {wheel.name}\n"
        f"{hashlib.sha256(sdist.read_bytes()).hexdigest()}  {sdist.name}\n",
        encoding="utf-8",
    )
    return wheel, sdist


def test_checked_artifact_handoff_verifies_one_wheel_and_sdist(tmp_path: Path) -> None:
    wheel, sdist = _write_checked_artifacts(tmp_path / "dist")

    assert check_checked_artifacts(tmp_path / "dist") == (wheel, sdist)


def test_checked_artifact_handoff_rejects_checksum_mismatch(tmp_path: Path) -> None:
    wheel, _ = _write_checked_artifacts(tmp_path / "dist")
    wheel.write_bytes(b"changed")

    with pytest.raises(ValueError, match="checksum mismatch"):
        check_checked_artifacts(tmp_path / "dist")


@pytest.mark.parametrize(
    ("filename", "contents", "message"),
    [
        ("extra.txt", b"unexpected", "unexpected files"),
        ("second.whl", b"duplicate", "exactly one wheel"),
    ],
)
def test_checked_artifact_handoff_rejects_wrong_payload_shape(
    tmp_path: Path,
    filename: str,
    contents: bytes,
    message: str,
) -> None:
    dist_dir = tmp_path / "dist"
    _write_checked_artifacts(dist_dir)
    (dist_dir / filename).write_bytes(contents)

    with pytest.raises(ValueError, match=message):
        check_checked_artifacts(dist_dir)
