import runpy
from pathlib import Path

import pytest

check_release_identity = runpy.run_path(
    str(Path(__file__).parents[1] / "tools" / "check_release_policy.py")
)["check_release_identity"]


def _write_release_identity(root: Path, project_version: str, citation_version: str) -> None:
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "example"\nversion = "{project_version}"\n',
        encoding="utf-8",
    )
    (root / "CITATION.cff").write_text(
        f'cff-version: 1.2.0\nversion: "{citation_version}"\n',
        encoding="utf-8",
    )


def test_release_identity_requires_matching_project_citation_and_tag(tmp_path: Path) -> None:
    _write_release_identity(tmp_path, "1.2.3", "1.2.3")

    assert check_release_identity(tmp_path, tag="v1.2.3") == "1.2.3"


def test_release_identity_rejects_mismatched_citation_version(tmp_path: Path) -> None:
    _write_release_identity(tmp_path, "1.2.3", "1.2.2")

    with pytest.raises(ValueError, match="does not match"):
        check_release_identity(tmp_path, tag="v1.2.3")


@pytest.mark.parametrize("tag", ["1.2.3", "v1.2.2", "v1.2.3-reissued"])
def test_release_identity_rejects_noncanonical_tags(tmp_path: Path, tag: str) -> None:
    _write_release_identity(tmp_path, "1.2.3", "1.2.3")

    with pytest.raises(ValueError, match="must be exactly"):
        check_release_identity(tmp_path, tag=tag)


def test_release_identity_rejects_nonstable_version_form(tmp_path: Path) -> None:
    _write_release_identity(tmp_path, "1.2.3rc1", "1.2.3rc1")

    with pytest.raises(ValueError, match="stable X.Y.Z"):
        check_release_identity(tmp_path)
