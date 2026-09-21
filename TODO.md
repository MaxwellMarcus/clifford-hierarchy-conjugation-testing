# Running TODO — Clifford-Hierarchy Conjugation Testing

Last updated: 2026-09-21

This is the operational queue for incremental development. Keep
`docs/status-and-roadmap.md` as the higher-level project audit. Each completed
change should be small enough to test, document, commit, and push as one
coherent unit.

## Current focus

- [ ] **Add direct streamed action-image recognition.** Retain algebraic labels
  and coordinates without dense cells, and cross-check reference and Pauli
  recognition against retained action tables.

## Next

- [ ] Add a symplectic/tableau backend for Pauli and Clifford operations while
  retaining dense matrices for arbitrary gates.
- [ ] Add optional Qiskit conversions with explicit endianness and qubit-order
  tests.
- [ ] Add a CLI for action tables, classifications, closure metadata, and JSON
  witness export.
- [ ] Add analytically known positive and negative hierarchy examples beyond
  the current elementary gates and five-qubit counterexample.

## Maintenance

- [ ] Replace deprecated setuptools license-table/classifier metadata with an
  SPDX license expression before the 2027-02-18 removal date.
- [ ] Keep numerical and exact counterexample workflows passing.
- [ ] Require the full test suite, Ruff, examples, counterexample verifiers,
  and package build before pushing an automated change.
- [ ] Preserve explicit incomplete/truncated metadata at every group level.
- [ ] Avoid calling numerical projective equality an exact proof.
- [ ] Keep README, API documentation, version, and citation metadata aligned.

## Completed

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
