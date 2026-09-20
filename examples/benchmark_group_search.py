"""Run a small, reproducible dense group-search benchmark."""

import numpy as np

from clifford_conjugation import (
    Gate,
    SearchLimits,
    pauli_generators,
    run_conjugation_group_benchmark,
)

h = Gate("H", np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2))
benchmark = run_conjugation_group_benchmark(
    h,
    pauli_generators(1),
    limits=SearchLimits(max_elements=64, max_products=1_000),
)
print(benchmark.record.to_json())
