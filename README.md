# Clifford Hierarchy Conjugation Testing

[![CI](https://github.com/MaxwellMarcus/clifford-hierarchy-conjugation-testing/actions/workflows/ci.yml/badge.svg)](https://github.com/MaxwellMarcus/clifford-hierarchy-conjugation-testing/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)

Research code for exact and numerical analysis of conjugation groups in the
Clifford hierarchy. It now includes a small public API for dense quantum gates,
finite projective gate sets, bounded group closure, and iterated conjugation
groups. The initial case study reproduces checks for the five-qubit
counterexample in Theorem 8.1 of de Silva and Lautsch,
[arXiv:2609.11903](https://arxiv.org/abs/2609.11903).

## What is included

- An exact, dependency-free finite-field verifier for the symplectic conditions,
  including exhaustive enumeration of all 135 target Lagrangians.
- A numerical five-qubit conjugation-group analysis that finds an explicit
  non-Clifford witness in the third conjugation group.
- A separate SymPy script that verifies that witness exactly.
- Validated, immutable dense `Gate` objects and projectively deduplicated
  `GateSet` collections.
- Standard dense `X_i, Z_i` generating sets with an explicit tensor-order
  convention.
- Generator-image actions and multi-conjugator action tables that can be
  inspected without enumerating the generated group.
- Projective recognition against named reference sets, including conventional
  Pauli-word labels and explicit classification coverage. Action tables can be
  recognized directly as Paulis without constructing a `4**n` dense catalog.
- Bounded finite-group and iterated conjugation-group generation whose results
  distinguish proven closure from a truncated search.
- Regression tests, continuous integration, packaging metadata, and citation
  information.

The matrix API is intended for transparent low-qubit experiments. The two
counterexample matrix scripts are research artifacts: one is explicitly
numerical, while the other uses exact symbolic arithmetic.

## Quick start

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
verify-counterexample
python -m pytest
python examples/basic_conjugation_groups.py
python examples/action_table.py
```

To run the research scripts directly:

```bash
python examples/de_silva_lautsch/analyze_conjugation_groups.py
python examples/de_silva_lautsch/exact_counterexample_witness.py
```

## Basic API

```python
import numpy as np

from clifford_conjugation import Gate, GateSet, SearchLimits, generate_group

x = Gate("X", [[0, 1], [1, 0]])
z = Gate("Z", [[1, 0], [0, -1]])
h = Gate("H", np.array([[1, 1], [1, -1]]) / np.sqrt(2))

closure = generate_group(
    GateSet([h, z]),
    limits=SearchLimits(max_elements=100, max_products=1_000),
)
assert closure.complete and closure.order == 8
```

See [the API guide](docs/api.md) for generator-image actions, the precise
conjugation convention, projective-equality policy, iteration methods, and
incomplete-search semantics. [Status and roadmap](docs/status-and-roadmap.md)
separates the current guarantees from the next research-engineering steps.

## Expected exact result

The finite-field computation finds 15 Lagrangians invariant under `A`, one
invariant under `B`, and no common invariant Lagrangian. It also verifies the
nilpotency conditions used by the relevant hierarchy criteria. See the command's
JSON output and `tests/test_de_silva_lautsch.py` for the complete regression
contract.

## Scope and numerical caution

This repository investigates specific algebraic conditions; it is not a general
proof assistant for Clifford-hierarchy membership. Group generation uses dense
matrices and is exponential in qubit count and often worse in group size. Every
search therefore has explicit element and product limits. Results from NumPy use
a projective canonicalization tolerance and should be confirmed symbolically
when used as proof. The exact scripts are labeled separately so computational
evidence is not confused with a theorem.

## License and citation

The code is available under the MIT License. Citation metadata is provided in
`CITATION.cff`.
