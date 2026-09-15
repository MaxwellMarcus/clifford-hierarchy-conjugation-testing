# Clifford Hierarchy Conjugation Testing

[![CI](https://github.com/MaxwellMarcus/clifford-hierarchy-conjugation-testing/actions/workflows/ci.yml/badge.svg)](https://github.com/MaxwellMarcus/clifford-hierarchy-conjugation-testing/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)

Research code for exact and numerical analysis of conjugation groups in the
Clifford hierarchy. The initial case study reproduces checks for the five-qubit
counterexample in Theorem 8.1 of de Silva and Lautsch,
[arXiv:2609.11903](https://arxiv.org/abs/2609.11903).

## What is included

- An exact, dependency-free finite-field verifier for the symplectic conditions,
  including exhaustive enumeration of all 135 target Lagrangians.
- A numerical five-qubit conjugation-group analysis that finds an explicit
  non-Clifford witness in the third conjugation group.
- A separate SymPy script that verifies that witness exactly.
- Regression tests, continuous integration, packaging metadata, and citation
  information.

The exact finite-field verifier is the maintained library interface. The two
matrix scripts in `examples/de_silva_lautsch/` are research artifacts: one is
explicitly numerical, while the other uses exact symbolic arithmetic.

## Quick start

Python 3.10 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
verify-counterexample
python -m pytest
```

To run the research scripts directly:

```bash
python examples/de_silva_lautsch/analyze_conjugation_groups.py
python examples/de_silva_lautsch/exact_counterexample_witness.py
```

## Expected exact result

The finite-field computation finds 15 Lagrangians invariant under `A`, one
invariant under `B`, and no common invariant Lagrangian. It also verifies the
nilpotency conditions used by the relevant hierarchy criteria. See the command's
JSON output and `tests/test_de_silva_lautsch.py` for the complete regression
contract.

## Scope and numerical caution

This repository investigates specific algebraic conditions; it is not a general
proof assistant for Clifford-hierarchy membership. Results from NumPy use a
projective canonicalization tolerance and should be confirmed symbolically when
used as proof. The exact scripts are labeled separately so computational evidence
is not confused with a theorem.

## License and citation

The code is available under the MIT License. Citation metadata is provided in
`CITATION.cff`.
