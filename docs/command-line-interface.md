# Command-line interface

The `clifford-conjugation` command reads an arbitrary unitary from a NumPy
`.npy` file and emits one deterministic, versioned JSON document. Qubit zero
uses the package's leftmost, most-significant tensor-factor convention.

Export a Pauli-generator action table, including every numerical matrix and
its direct tensor-Pauli classification:

```console
clifford-conjugation unitary.npy --name U --atol 1e-9 action
```

Run bounded projective closure and export a numerical witness:

```console
clifford-conjugation unitary.npy --name U group \
  --max-elements 4096 --max-products 1000000
```

The group document records projective tolerances, generator provenance,
classifications, search limits, words, and stop reason. A truncated search has
`"complete": false` and `"order": null`; the discovered prefix is never
reported as the full group order. These dense complex128 records are numerical
evidence, not exact algebraic proofs.
