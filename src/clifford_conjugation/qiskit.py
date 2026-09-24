"""Optional Qiskit conversions with an explicit qubit-order boundary."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from .operators import Gate


def gate_from_qiskit(value: Any, *, name: str | None = None) -> Gate:
    """Convert a Qiskit operator or circuit to this package's dense convention.

    Qiskit displays basis states as ``|q_(n-1) ... q_0>`` whereas this package
    assigns qubit zero to the leftmost, most-significant tensor factor.  The
    conversion therefore reverses the tensor-factor order rather than merely
    copying the displayed matrix.
    """

    Operator = _qiskit_operator_type()
    operator = Operator(value)
    matrix = np.asarray(operator.data, dtype=np.complex128)
    gate_name = name or getattr(value, "name", None) or "qiskit_operator"
    return Gate(gate_name, _reverse_qubit_order(matrix))


def gate_to_qiskit_operator(gate: Gate) -> Any:
    """Return a Qiskit ``Operator`` with the same numbered-qubit action."""

    Operator = _qiskit_operator_type()
    return Operator(_reverse_qubit_order(gate.matrix))


def gate_to_qiskit_circuit(gate: Gate) -> Any:
    """Return a Qiskit circuit implementing ``gate`` on the same qubit labels."""

    try:
        from qiskit import QuantumCircuit
        from qiskit.circuit.library import UnitaryGate
    except ModuleNotFoundError as exc:  # pragma: no cover - optional install
        raise ModuleNotFoundError(
            'Qiskit conversion requires: pip install -e ".[qiskit]"'
        ) from exc

    circuit = QuantumCircuit(gate.num_qubits, name=gate.name)
    qiskit_matrix = _reverse_qubit_order(gate.matrix)
    circuit.append(UnitaryGate(qiskit_matrix, label=gate.name), circuit.qubits)
    return circuit


def _qiskit_operator_type() -> Any:
    try:
        from qiskit.quantum_info import Operator
    except ModuleNotFoundError as exc:  # pragma: no cover - optional install
        raise ModuleNotFoundError(
            'Qiskit conversion requires: pip install -e ".[qiskit]"'
        ) from exc
    return Operator


def _reverse_qubit_order(matrix: NDArray[np.complex128]) -> NDArray[np.complex128]:
    dimension = matrix.shape[0]
    num_qubits = dimension.bit_length() - 1
    if matrix.ndim != 2 or matrix.shape != (dimension, dimension) or 1 << num_qubits != dimension:
        raise ValueError("Qiskit operator dimension must be a positive power of two")
    permutation = np.array(
        [int(f"{index:0{num_qubits}b}"[::-1], 2) for index in range(dimension)],
        dtype=np.intp,
    )
    return matrix[np.ix_(permutation, permutation)]
