"""Verify a checked wheel/sdist handoff without rebuilding either artifact."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import re
from pathlib import Path

SHA256_LINE = re.compile(r"(?P<digest>[0-9a-f]{64}) [ *](?P<filename>[^/]+)")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_checked_artifacts(dist_dir: Path) -> tuple[Path, Path]:
    """Return the sole wheel and sdist after strict checksum verification."""

    if not dist_dir.is_dir():
        raise ValueError(f"artifact directory does not exist: {dist_dir}")
    entries = tuple(sorted(dist_dir.iterdir()))
    if any(not path.is_file() or path.is_symlink() for path in entries):
        raise ValueError("artifact directory must contain only regular files")

    wheels = tuple(path for path in entries if path.name.endswith(".whl"))
    sdists = tuple(path for path in entries if path.name.endswith(".tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("artifact must contain exactly one wheel and one source distribution")

    checksum_path = dist_dir / "SHA256SUMS"
    expected_names = {wheels[0].name, sdists[0].name}
    if {path.name for path in entries} != expected_names | {checksum_path.name}:
        raise ValueError("artifact contains unexpected files")

    checksums: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        match = SHA256_LINE.fullmatch(line)
        if match is None:
            raise ValueError(f"malformed SHA256SUMS line: {line!r}")
        filename = match.group("filename")
        if filename in checksums:
            raise ValueError(f"duplicate checksum entry: {filename}")
        checksums[filename] = match.group("digest")
    if set(checksums) != expected_names:
        raise ValueError("SHA256SUMS must name exactly the wheel and source distribution")

    for path in (*wheels, *sdists):
        if not hmac.compare_digest(_sha256(path), checksums[path.name]):
            raise ValueError(f"checksum mismatch for {path.name}")
    return wheels[0], sdists[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", nargs="?", type=Path, default=Path("dist"))
    arguments = parser.parse_args()
    wheel, sdist = check_checked_artifacts(arguments.dist_dir)
    print(f"checked artifact handoff valid: {wheel.name}, {sdist.name}")


if __name__ == "__main__":
    main()
