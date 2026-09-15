"""Build the first two conjugation groups of the one-qubit Hadamard gate."""

import numpy as np

from clifford_conjugation import Gate, GateSet, SearchLimits, generate_conjugation_groups


def main() -> None:
    x = Gate("X", [[0, 1], [1, 0]])
    z = Gate("Z", [[1, 0], [0, -1]])
    hadamard = Gate("H", np.array([[1, 1], [1, -1]]) / np.sqrt(2))
    pauli_generators = GateSet([x, z])

    groups = generate_conjugation_groups(
        hadamard,
        pauli_generators,
        depth=2,
        limits=SearchLimits(max_elements=100, max_products=1_000),
    )
    for group in groups:
        print(
            f"Gamma_{group.level}: order={group.order}, "
            f"defining_generators={len(group.defining_generators)}, "
            f"complete={group.complete}"
        )


if __name__ == "__main__":
    main()
