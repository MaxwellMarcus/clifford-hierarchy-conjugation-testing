from __future__ import annotations

import numpy as np
import pytest

qiskit = pytest.importorskip("qiskit")

from qiskit import QuantumCircuit  # noqa: E402
from qiskit.quantum_info import Operator  # noqa: E402

from clifford_conjugation import (  # noqa: E402
    Gate,
    embed_one_qubit_gate,
    gate_from_qiskit,
    gate_to_qiskit_circuit,
    gate_to_qiskit_operator,
)

X = Gate("X", [[0, 1], [1, 0]])


@pytest.mark.parametrize("qiskit_qubit", [0, 1])
def test_qiskit_numbered_qubits_map_to_most_significant_internal_order(
    qiskit_qubit: int,
) -> None:
    circuit = QuantumCircuit(2)
    circuit.x(qiskit_qubit)

    converted = gate_from_qiskit(circuit)

    assert np.array_equal(
        converted.matrix,
        embed_one_qubit_gate(X, qiskit_qubit, 2).matrix,
    )


def test_qiskit_cnot_control_target_order_is_preserved() -> None:
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)
    expected = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
        dtype=complex,
    )

    assert np.array_equal(gate_from_qiskit(circuit).matrix, expected)


def test_operator_and_circuit_round_trips_preserve_asymmetric_gate() -> None:
    matrix = np.array(
        [[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 1j, 0], [0, 0, 0, -1j]],
        dtype=complex,
    )
    gate = Gate("asymmetric", matrix)

    operator = gate_to_qiskit_operator(gate)
    circuit = gate_to_qiskit_circuit(gate)

    assert np.allclose(gate_from_qiskit(operator).matrix, gate.matrix)
    assert np.allclose(gate_from_qiskit(circuit).matrix, gate.matrix)
    assert np.allclose(Operator(circuit).data, operator.data)
