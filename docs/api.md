# Dense-matrix API

This package provides a deliberately small API for low-qubit experiments. It
does not attempt to replace a circuit simulator or a computer-algebra proof.

## Operators and finite sets

`Gate(name, matrix)` validates that its dense complex matrix is square, unitary,
and has power-of-two dimension. The stored matrix is copied and made read-only.
`GateSet` requires same-size `Gate` objects and removes duplicates modulo global
phase while preserving the first representative.

`pauli_generators(n)` constructs the usual projective Pauli generating set in
the order `X_0, ..., X_(n-1), Z_0, ..., Z_(n-1)`. Qubit zero is the leftmost,
most-significant Kronecker factor, matching the counterexample scripts.
`embed_one_qubit_gate(gate, qubit, n)` exposes the same convention for other
one-qubit gates.

Numerical projective equality is controlled by `ProjectiveConfig`. The
canonicalization fixes the phase of the first numerically nonzero entry, zeros
small real and imaginary parts, and rounds the result before hashing. This makes
small numerical searches reproducible, but approximate equality is not exact
algebra. Use exact arithmetic to confirm proof-critical witnesses, as the
counterexample example does.

## Conjugation actions without closure

Use `conjugation_action` when the immediate question is how a gate maps a
chosen generating set:

```python
action = conjugation_action(h, pauli_generators(1))
assert projectively_equal(action.image("X_0").matrix, z.matrix)
```

A `ConjugationAction` stores exactly one image per named domain generator.
`image(name_or_index)` retrieves a cell, `as_dict()` returns a name-to-image
mapping, and `apply_word(["X", "Z"])` evaluates the image of the matrix product
`X @ Z` using the homomorphism property of conjugation. The empty word maps to
the identity. None of these operations enumerates the generated group.

For a finite collection of possible conjugators, use an action table:

```python
table = conjugation_action_table(GateSet([identity, h]), pauli_generators(1))
assert table.shape == (2, 2)
hx_image = table.image("H", "X_0")
generators_for_closure = table.unique_images
```

Rows are conjugators, columns are probe generators, and `unique_images`
deduplicates all cells modulo global phase. Construction performs exactly one
dense conjugation per table cell; it does not call `generate_group`.
`source_complete=False` records that a table's rows came from only a partial
earlier search. `generate_conjugation_group` builds and retains this table as
its `action_table` before attempting closure.

Deduplication does not discard provenance. `unique_image_sources` is aligned
with `unique_images`; every entry is a tuple of all `GeneratorSource` records
that produced that projective image, in stable row-major order. Each record
contains the source row and column indices, conjugator and probe names, and a
human-readable `label` such as `H conjugates X_0`. Generated
`ConjugationGroup` results expose the same mapping as
`defining_generator_sources`, including when `source_complete` is false.

## Projective recognition and algebraic labels

Every `GateSet` is also a named projective reference set.
`references.match_matrix(matrix)` returns the retained matching `Gate`, or
`None` if the operator is unknown. Global phase is ignored using the reference
set's `ProjectiveConfig`.

`projective_pauli_group(n)` creates a catalog with conventional tensor-word
labels such as `I`, `Y_1`, and `X_0 Z_2`. The catalog contains exactly `4**n`
dense matrices, so it defaults to a hard limit of 1,024 elements. Raise
`max_elements` deliberately if a larger dense catalog is appropriate.

When the reference class is specifically the tensor-Pauli group, prefer the
direct recognizer:

```python
classification = table.classify_paulis()
assert classification.preserves_paulis
assert classification.label("H", "X_0") == "Z_0"
```

This checks the monomial pattern and relative signs of each dense image rather
than materializing all `4**n` Paulis. `PauliWord` records the result as binary
X and Z masks and exposes a conventional tensor-word label. If the columns are
a complete Pauli generating set, `preserves_paulis` is the usual normalizer
test that every represented conjugator is Clifford. For an arbitrary subset of
probes, it means only that the supplied probes have Pauli images.

For a table whose probes are the standard `pauli_generators(n)` in X-then-Z
order, `classification.symplectic_matrix(conjugator)` returns the induced
read-only binary matrix. It verifies the symplectic identity before returning.
`row_preserves_paulis(conjugator)` reports the Pauli-normalizer result for one
row without conflating it with aggregate table coverage.

An entire action table can be classified at once:

```python
paulis = projective_pauli_group(1)
classification = table.classify(paulis)

assert classification.label("H", "X_0") == "Z_0"
assert classification.coverage == 1.0
print(classification.as_rows(unknown="not Pauli"))
```

`ActionImageClassification` retains both the matching reference gates and the
original table. It reports `recognized_count`, `coverage`, `all_recognized`, and
the named coordinates of `unrecognized` cells. An unmatched entry is evidence
only that it is absent from the chosen reference set—not that it lies outside a
larger algebraic class.

## Finite group closure

```python
closure = generate_group(
    generators,
    limits=SearchLimits(max_elements=4096, max_products=1_000_000),
)
```

`generate_group` performs a breadth-first search from the identity, using right
multiplication by each generator and identifying matrices up to global phase.
It returns a `GroupClosure`, not a bare collection:

- `complete` is true only if the search exhausted its frontier.
- `order` is an integer only for a complete closure; it is `None` otherwise.
- `stop_reason` is `complete`, `max_elements`, or `max_products`.
- `elements` is the full group when complete and only the discovered prefix when
  truncated.
- `words` records one generator-name word for each discovered element.

If the search terminates, closure under the generators proves that the finite
set of unitaries is a group. The limits keep infinite or unexpectedly large
groups from running without a bound.

## Conjugation-group convention

Let \(P\) be the supplied probe generating set (normally the single-qubit Pauli
\(X_i,Z_i\) generators). For a gate \(U\), this repository defines

\[
  \Gamma_1(U)=\left\langle U p U^\dagger : p\in P\right\rangle.
\]

Later levels use every element of the preceding group:

\[
  \Gamma_{j+1}(U)=
  \left\langle v p v^\dagger : v\in\Gamma_j(U),\ p\in P\right\rangle.
\]

This is the convention used in
`examples/de_silva_lautsch/analyze_conjugation_groups.py`: its `gamma_1` is
generated by conjugating the ten five-qubit Pauli generators by the
counterexample unitary, and its second-level defining generators are all
\(v p v^\dagger\) with \(v\in\Gamma_1\).

Use `generate_conjugation_group` for one level,
`generate_next_conjugation_group` for explicit iteration, or
`generate_conjugation_groups(..., depth=n)` for a tower. If a preceding level is
truncated, later computations can still be inspected, but `source_complete` and
`complete` remain false. Thus a finite closure from incomplete input is never
misreported as the full next group.

The recommended workflow is therefore:

1. Inspect `conjugation_action` for a single gate or
   `conjugation_action_table` for a known finite source.
2. Use `classify_paulis()` for direct Pauli recognition, or classify against a
   different named projective reference set.
3. Call bounded group generation only when closure is actually needed.

## Numerical witness export

`build_numerical_witness(group)` returns a versioned, JSON-compatible record of
a conjugation-group computation. `export_numerical_witness(group)` serializes
the same record as deterministic JSON. The version-one schema includes closure
generator words, direct tensor-Pauli classifications, all deduplicated-generator
provenance, projective comparison settings, resource limits, and separate source
and closure completeness flags.

```python
from clifford_conjugation import export_numerical_witness

payload = export_numerical_witness(gamma_1)
```

The export is a compact numerical transcript for independent inspection. It
does not upgrade floating-point recognition to an exact proof, and a truncated
search always exports `null` for its group order.

## Minimal example

```python
import numpy as np

from clifford_conjugation import (
    Gate,
    GateSet,
    SearchLimits,
    generate_conjugation_groups,
)

x = Gate("X", [[0, 1], [1, 0]])
z = Gate("Z", [[1, 0], [0, -1]])
h = Gate("H", np.array([[1, 1], [1, -1]]) / np.sqrt(2))

gamma_1, gamma_2 = generate_conjugation_groups(
    h,
    GateSet([x, z]),
    depth=2,
    limits=SearchLimits(max_elements=100, max_products=1_000),
)

assert gamma_1.complete and gamma_1.order == 4
assert gamma_2.complete and gamma_2.order == 4
```
