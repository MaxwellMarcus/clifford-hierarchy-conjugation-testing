# Release process

The repository has a checked release workflow, but it does not publish to a
package index. This deliberately separates artifact reproducibility from
credentialed publication.

## Current checked-artifact policy

`.github/workflows/release.yml` runs for `v*` tags and manual dispatches. Its
validation matrix must pass on Python 3.10 and 3.12 before the artifact job can
start. Validation includes Ruff, the full pytest suite, every documented
example, and all three numerical/exact counterexample workflows.

The gated artifact job then:

1. builds exactly one wheel and one source distribution with `python -m build`;
2. runs strict `twine check` metadata validation;
3. checks the name, version, SPDX license expression, packaged license, typed
   package marker, and essential source-distribution files; and
4. uploads the inspected files as the `checked-distributions` workflow
   artifact.

The workflow has read-only repository permissions and contains no PyPI token,
trusted-publisher permission, signing key, release creation, or upload command.
A successful run therefore means that downloadable artifacts passed the stated
checks; it does not mean a release was published.

## Publication remains a separate milestone

Automatic publication should only be added after the tag and version policy,
signed-tag requirement, protected release environment, and trusted-publisher
configuration are agreed and documented. The future publication job must
depend on the existing validation and artifact checks, consume the inspected
artifacts rather than rebuild them, and preserve a manual stop before the first
real upload.
