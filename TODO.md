# Running TODO — Clifford-Hierarchy Conjugation Testing

Last updated: 2026-10-05

This is the operational queue for incremental development. Keep
`docs/status-and-roadmap.md` as the higher-level project audit. Each completed
change should be small enough to test, document, commit, and push as one
coherent unit.

## Current focus

- [ ] **Configure and re-audit the external trusted-publisher prerequisites.**
  Create the currently missing protected `pypi` environment, required
  reviewers, immutable `v*` tag ruleset, and matching PyPI trusted publisher;
  then obtain a passing fail-closed preflight before enabling upload.

## Next

- [ ] Implement trusted publication from the checked artifacts only after the
  external configuration is confirmed.

## Maintenance

- [ ] Keep numerical and exact counterexample workflows passing.
- [ ] Require the full test suite, Ruff, examples, counterexample verifiers,
  and package build before pushing an automated change.
- [ ] Preserve explicit incomplete/truncated metadata at every group level.
- [ ] Avoid calling numerical projective equality an exact proof.
- [ ] Keep README, API documentation, version, and citation metadata aligned.

## Completed

- [x] 2026-10-05 — Add a fail-closed external publication preflight with
  focused tests, record that the live repository currently has neither a
  `pypi` environment nor tag rulesets, and keep upload disabled.

- [x] 2026-10-04 — Document the approved maintainer SSH key and require an
  annotated tag with a valid allowlisted signature whose commit is reachable
  from `origin/main`, without enabling trusted publication.

- [x] 2026-10-03 — Add a dependent, read-only consumer job that downloads
  `checked-distributions`, requires exactly one wheel and source distribution,
  verifies their recorded SHA-256 hashes, and neither rebuilds nor requests
  OIDC credentials.

- [x] 2026-10-02 — Define stable tag/project/citation version invariants,
  signed-tag and protected-environment requirements, the scoped OIDC trusted-
  publisher boundary, and a no-rebuild artifact handoff; enforce version
  identity and include SHA-256 checksums in checked artifacts.

- [x] 2026-10-01 — Add a read-only release workflow that gates wheel/sdist
  builds on the full validation matrix, strictly checks metadata and required
  contents, uploads inspected artifacts, and documents that no publication
  credentials or upload step are present.

- [x] 2026-09-30 — Carry direct tensor-Pauli labels, binary X/Z masks, and all
  deduplicated row/probe sources into every generated conjugation-group level,
  with deterministic reports that preserve incomplete-source and unknown-order
  states.

- [x] 2026-09-29 — Replace deprecated license-table metadata and the redundant
  license classifier with an SPDX `MIT` expression, explicitly ship `LICENSE`,
  require a PEP 639-capable setuptools, and inspect rebuilt wheel/sdist
  metadata.

- [x] 2026-09-28 — Add exact eighth-root diagonal phase-polynomial checks,
  proving CCZ is properly in C3 and controlled-T is outside C3, with dense
  conjugation cross-checks and a runnable example.

- [x] 2026-09-27 — Add a structured JSON CLI for numerical action tables and
  group witnesses, preserving projective tolerances, provenance, search limits,
  stop reasons, and explicit incomplete closure states.

- [x] 2026-09-24 — Add optional Qiskit operator/circuit conversions with an
  explicit tensor-factor reversal and asymmetric qubit-order round-trip tests.

- [x] 2026-09-23 — Add exact phase-free Pauli arithmetic, binary symplectic
  Clifford actions, bounded closure with explicit incomplete states, and dense
  one- and two-qubit action/closure cross-checks.
- [x] 2026-09-22 — Add direct streamed named-reference and tensor-Pauli
  recognition that retains algebraic labels, binary coordinates, and source
  coordinates without dense action-table cells, cross-checked against retained
  tables.
- [x] 2026-09-21 — Add an opt-in streamed subgroup-generator path that retains
  only projectively unique dense images and provenance, cross-checked against
  retained action tables and closure results.
- [x] 2026-09-20 — Add versioned reproducible group-search benchmarks over
  qubit count, source size, finite order, closure limits, runtime, and Python
  peak memory, with exact workloads separated from host measurements.
- [x] 2026-09-19 — Add adversarial unitary tests at projective pivot,
  component-threshold, and decimal-rounding boundaries, and document how close
  representatives can merge or separate.
- [x] 2026-09-18 — Add an independent exact binary-Pauli verifier for
  version-one exports, including action classifications, provenance, and
  claimed complete closures.
- [x] 2026-09-17 — Export a versioned compact numerical witness with generator
  words, Pauli classifications, provenance, tolerance, and completeness data.
- [x] 2026-09-16 — Preserve every action-table row and probe after projective
  generator deduplication and propagate the provenance into generated groups.
- [x] 2026-09-15 — Add immutable dense `Gate` and projectively deduplicated
  `GateSet` structures.
- [x] 2026-09-15 — Add bounded group closure with completeness and truncation
  metadata.
- [x] 2026-09-15 — Add named conjugation-action tables and word evaluation.
- [x] 2026-09-15 — Add named-reference and direct tensor-Pauli recognition.
- [x] 2026-09-15 — Extract and validate induced binary symplectic matrices.
- [x] 2026-09-15 — Validate the numerical and exact five-qubit counterexample
  workflows.

## Rules for automated maintenance

1. Work from the first unchecked, currently feasible item unless a failing
   build or correctness bug has higher priority.
2. Split work that cannot be completed safely in one run into a concrete next
   milestone and update this file.
3. Move finished work to `Completed` with the date and a concise result.
4. Preserve existing APIs unless a documented breaking change is genuinely
   necessary.
5. Do not push unless all relevant validation passes.
