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
2. for tag-triggered runs, requires an annotated SSH-signed tag, verifies its
   signature against `.github/release-signers`, and proves its commit is
   reachable from `origin/main`;
3. builds exactly one wheel and one source distribution with `python -m build`;
4. runs strict `twine check` metadata validation;
5. checks the name, version, SPDX license expression, packaged license, typed
   package marker, and essential source-distribution files; and
6. records SHA-256 checksums and uploads the inspected files plus
   `SHA256SUMS` as the `checked-distributions` workflow artifact.

The workflow has read-only repository permissions and contains no PyPI token,
trusted-publisher permission, signing key, release creation, or upload command.
A successful run therefore means that downloadable artifacts passed the stated
checks; it does not mean a release was published.

After the build job, a dependent non-publishing consumer downloads
`checked-distributions`, requires exactly one wheel, one source distribution,
and `SHA256SUMS`, and recomputes both hashes with
`tools/check_checked_artifacts.py`. The consumer requests only
`contents: read`: it has no OIDC permission, package-index upload step, or
build command. This exercises the byte-for-byte handoff without treating it as
publication.

## Release identity and signed-tag policy

A production release is eligible only when all of these invariants hold:

- `pyproject.toml` and `CITATION.cff` contain the same stable `X.Y.Z` version;
- the immutable tag is exactly `vX.Y.Z`, points to the release commit on
  `main`, and is not moved or reused;
- the tag is annotated and signed by an approved maintainer key, and the
  publication preflight verifies that signature rather than treating a
  matching tag name as authentication; and
- the source commit has passed the protected `main` checks.

`tools/check_release_policy.py` enforces the version and tag-name invariants.
`tools/check_tag_provenance.py` rejects lightweight tags, signatures absent
from the committed SSH allowlist, and tagged commits outside `origin/main`.
The approved signer is:

```text
maxwellmarcus2024@gmail.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICABJCm3i6AuPPjImVJ4eRDRBmoREzbOPmUlIhz7tKRm
```

Changing the allowlist is a security-sensitive repository change and does not
retroactively authorize a moved tag. Manual workflow dispatches are useful for
non-release artifact inspection and have no tag to authenticate. The current
workflow still does **not** publish, so a successful `v*` artifact run is not
publication authorization.

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

Actual publication remains blocked on the matching PyPI trusted-publisher
configuration. The GitHub `pypi` environment, required reviewer, custom `v*`
deployment policy, and active ruleset preventing updates and deletion of `v*`
tags were configured and audited on 2026-10-06.

Run the fail-closed preflight after an administrator configures those controls:

```bash
python tools/check_publication_prerequisites.py --json
```

The GitHub checks are read directly through the authenticated `gh` CLI. The
environment audit requires the exact user reviewer `MaxwellMarcus`; a
nonempty reviewer list containing a different user or team does not pass. PyPI
does not expose trusted-publisher configuration through its public project API,
so an administrator must inspect the PyPI project settings and then rerun with
`--pypi-publisher-confirmed`. That flag attests only the exact tuple printed by
the tool: owner `MaxwellMarcus`, repository
`clifford-hierarchy-conjugation-testing`, workflow `release.yml`, and
environment `pypi`.

The `v*` tag ruleset must restrict both updates and deletions. Blocking only
non-fast-forward changes is insufficient for an immutable release tag because
moving a tag forward would still change the authenticated release identity.

On 2026-10-08 the GitHub audit passed all four repository-side checks,
including the exact required-reviewer identity. The PyPI project is not yet
published, and no pending trusted publisher could be confirmed from the
available unauthenticated PyPI session. Publication remains disabled until an
administrator creates the exact pending publisher tuple and reruns the
preflight with `--pypi-publisher-confirmed`.
