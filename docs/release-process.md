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

1. checks that `pyproject.toml`, `CITATION.cff`, and a triggering tag (when
   present) identify exactly the same stable `X.Y.Z` release;
2. builds exactly one wheel and one source distribution with `python -m build`;
3. runs strict `twine check` metadata validation;
4. checks the name, version, SPDX license expression, packaged license, typed
   package marker, and essential source-distribution files; and
5. records SHA-256 checksums and uploads the inspected files plus
   `SHA256SUMS` as the `checked-distributions` workflow artifact.

The workflow has read-only repository permissions and contains no PyPI token,
trusted-publisher permission, signing key, release creation, or upload command.
A successful run therefore means that downloadable artifacts passed the stated
checks; it does not mean a release was published.

## Release identity and signed-tag policy

A production release is eligible only when all of these invariants hold:

- `pyproject.toml` and `CITATION.cff` contain the same stable `X.Y.Z` version;
- the immutable tag is exactly `vX.Y.Z`, points to the release commit on
  `main`, and is not moved or reused;
- the tag is annotated and signed by an approved maintainer key, and the
  publication preflight verifies that signature rather than treating a
  matching tag name as authentication; and
- the source commit has passed the protected `main` checks.

`tools/check_release_policy.py` enforces the version and tag-name invariants in
the checked-artifact job. The current workflow does **not** fetch maintainer
keys, verify a tag signature, check tag ancestry, or publish. A successful
`v*` artifact run is therefore not yet publication authorization.

## Protected environment and trusted-publisher boundary

Before a publication job is enabled, repository administrators must create a
GitHub Actions environment named `pypi` with required reviewers, restrict it to
protected `v*` tags, and configure the matching PyPI trusted publisher for this
repository, workflow filename, and environment. The publication job may then
receive `id-token: write` at job scope only; all other permissions remain
read-only. Long-lived PyPI tokens, repository secrets containing credentials,
fork and pull-request publication, and manual-dispatch bypasses are prohibited.

Environment approval is the manual stop for the first real upload. Approval
authorizes only the already identified tag and checked artifacts; it does not
waive the signature, ancestry, version, test, or inspection gates.

## Artifact handoff for a future publication job

The publication job must depend on `build-and-inspect`, download the
`checked-distributions` artifact from that same workflow run, verify
`SHA256SUMS`, and upload only its single wheel and source distribution. It must
not check out source, invoke a build backend, modify metadata, or substitute a
different artifact. This keeps the bytes inspected by the read-only job equal
to the bytes offered to PyPI.

The next repository-only milestone is a non-publishing consumer job that
exercises this download-and-verify handoff. Actual publication remains blocked
on reviewed signer keys plus the external protected-environment and PyPI
trusted-publisher configuration.
