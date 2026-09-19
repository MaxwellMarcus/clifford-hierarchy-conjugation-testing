# Status and roadmap

This file distinguishes implemented behavior from planned work. The package is
an alpha research toolkit for transparent low-qubit experiments, not a general
Clifford-hierarchy decision procedure.

## Current implementation

- `Gate` validates immutable dense unitaries; `GateSet` deduplicates them
  numerically modulo global phase.
- `conjugation_action` and `ConjugationActionTable` expose named generator
  images before attempting group closure.
- Action images can be matched against any named `GateSet`. Tensor Paulis can
  also be recognized directly as binary `PauliWord` objects without building a
  `4**n` dense reference catalog.
- For standard Pauli probes, direct classifications expose the induced binary
  symplectic matrix for each recognized row and verify preservation of the
  symplectic form.
- `generate_group` performs deterministic, bounded breadth-first projective
  closure and records generator words, stop reasons, and completeness.
- Projectively deduplicated defining generators retain every source action-table
  row and probe as stable, named provenance records.
- Conjugation-group computations export a versioned JSON witness containing
  generator words, Pauli classifications, provenance, numerical tolerance, and
  explicit completeness metadata.
- Version-one tensor-Pauli exports can be independently checked with exact
  binary action tables; the verifier checks classifications, provenance, and
  claimed complete Pauli closures without consulting dense matrices.
- Iterated conjugation groups retain their action tables and propagate an
  incomplete-source flag, so a later closure from truncated input is never
  reported as the full group.
- The de Silva--Lautsch case study includes an exact finite-field verifier, a
  numerical five-qubit group analysis, and exact SymPy confirmation of its
  displayed witness.
- The public API, examples, packaging, citation metadata, CI, and regression
  tests are in place. At this checkpoint, 69 tests pass with 89% statement
  coverage and Ruff reports no issues.

## What the current guarantees mean

- `GroupClosure.complete` proves closure only for the supplied dense numerical
  generators. It does not make floating-point canonicalization exact.
- `ConjugationGroup.complete` additionally requires the preceding source of
  conjugators to be complete.
- `PauliActionClassification.preserves_paulis` is a Clifford normalizer test
  only when the table columns generate the whole Pauli group. With fewer
  probes, it describes only those columns.
- General NumPy results are computational evidence. Proof-critical claims
  should be rechecked in exact arithmetic, as the counterexample witness is.

## Prioritized work

### P0: retain algebraic provenance across levels

- Carry recognized labels and provenance into conjugation-group levels and
  human-readable reports.
- [x] Record every source row and probe for each deduplicated defining
  generator, including groups generated from incomplete sources.

### P1: replace dense bottlenecks where structure is known

- Add a symplectic/tableau backend for Pauli and Clifford operations, while
  retaining dense matrices for arbitrary higher-hierarchy gates.
- Avoid materializing every dense action-table cell when only recognition or a
  generated subgroup is required.
- Add reproducible benchmarks over qubit count, source size, group order, and
  truncation limits.

### P1: expand exact verification

- Generalize exact arithmetic beyond tensor-Pauli action tables and the
  dedicated counterexample scripts.
- [x] Allow numerical searches to export compact version-one witnesses that an
  exact binary-Pauli backend can independently verify.
- [x] Add adversarial tolerance tests near projective-canonicalization
  boundaries, including pivot selection, component zeroing, and decimal
  half-steps.

### P2: interoperability and research workflow

- Add optional Qiskit conversion for circuits/operators and explicit qubit
  ordering tests.
- Provide a CLI that exports action tables, classification summaries, closure
  metadata, and witnesses as JSON.
- Add analytically known hierarchy examples and negative cases beyond the
  current Hadamard/phase examples and the five-qubit case study.

The immediate next implementation target is reproducible group-search
benchmarking that separates exact workload dimensions from host runtime and
memory measurements.
