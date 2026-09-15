# Five-qubit counterexample reproduction

These are the three checks originally developed for the counterexample analysis:

| Script | Arithmetic | Purpose |
|---|---|---|
| `verify_counterexample.py` | Exact over \(\mathbb F_2\) | Verifies the symplectic conditions and exhausts the 135 target Lagrangians. |
| `analyze_conjugation_groups.py` | Numerical NumPy matrices | Enumerates the first conjugation group, constructs second-group generators, and searches for a third-group non-Clifford witness. |
| `exact_counterexample_witness.py` | Exact symbolic matrices | Confirms the witness returned by the numerical search. |

The first script delegates to the tested package implementation. The numerical
search uses rounded projective keys, so its witness is treated as evidence until
the symbolic script confirms the exact matrix identity.

The generic convention and bounded implementation of the first two group
levels are documented in [`docs/api.md`](../../docs/api.md). The exploratory
script remains self-contained so the original research calculation can still be
reproduced independently of later package abstractions.
