"""Inspect generator images before attempting conjugation-group closure."""

import numpy as np

from clifford_conjugation import (
    Gate,
    GateSet,
    conjugation_action_table,
    pauli_generators,
)


def main() -> None:
    identity = Gate.identity(1)
    hadamard = Gate("H", np.array([[1, 1], [1, -1]]) / np.sqrt(2))
    phase = Gate("S", np.diag([1, 1j]))

    table = conjugation_action_table(
        GateSet([identity, hadamard, phase]),
        pauli_generators(1),
    )
    classification = table.classify_paulis()

    print(
        f"table shape: {table.shape}; unique projective images: {len(table.unique_images)}; "
        f"Pauli coverage: {classification.coverage:.0%}"
    )
    for action, labels in zip(table, classification.as_rows(unknown="not Pauli"), strict=True):
        for probe, label in zip(table.probe_generators, labels, strict=True):
            print(f"{action.conjugator.name} {probe.name} {action.conjugator.name}† = {label}")


if __name__ == "__main__":
    main()
