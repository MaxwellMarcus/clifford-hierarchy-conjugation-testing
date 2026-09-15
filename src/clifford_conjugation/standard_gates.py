"""Standard dense gates for small-qubit conjugation experiments."""

from __future__ import annotations

from itertools import product

import numpy as np

from .operators import DEFAULT_PROJECTIVE_CONFIG, Gate, GateSet, ProjectiveConfig

_PAULI_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
_PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
_PAULI_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
_PAULI_FACTORS = {
    "I": np.eye(2, dtype=np.complex128),
    "X": _PAULI_X,
    "Y": _PAULI_Y,
    "Z": _PAULI_Z,
}
DEFAULT_PAULI_CATALOG_LIMIT = 1024


def embed_one_qubit_gate(
    gate: Gate,
    qubit: int,
    num_qubits: int,
    *,
    name: str | None = None,
) -> Gate:
    """Embed a one-qubit gate into a dense ``num_qubits``-qubit operator.

    Qubit zero is the leftmost, most-significant tensor factor.  For example,
    embedding ``X`` on qubit zero of a two-qubit system returns ``X ⊗ I``.
    """

    if not isinstance(gate, Gate):
        raise TypeError("gate must be a Gate")
    if gate.num_qubits != 1:
        raise ValueError("only one-qubit gates can be embedded by this function")
    _validate_qubit_index(qubit, num_qubits)
    factors = [np.eye(2, dtype=np.complex128) for _ in range(num_qubits)]
    factors[qubit] = gate.matrix
    matrix = np.array([[1]], dtype=np.complex128)
    for factor in factors:
        matrix = np.kron(matrix, factor)
    return Gate(
        name or f"{gate.name}_{qubit}",
        matrix,
        validation_atol=gate.validation_atol,
    )


def pauli_generators(
    num_qubits: int,
    *,
    projective_config: ProjectiveConfig = DEFAULT_PROJECTIVE_CONFIG,
) -> GateSet:
    """Return ``X_0,...,X_(n-1),Z_0,...,Z_(n-1)`` as dense gates.

    These ``2 * num_qubits`` matrices generate the projective Pauli group.  The
    qubit-zero-most-significant convention matches the counterexample scripts.
    """

    if not isinstance(num_qubits, int) or isinstance(num_qubits, bool):
        raise TypeError("num_qubits must be an integer")
    if num_qubits < 1:
        raise ValueError("num_qubits must be at least 1")
    x = Gate("X", _PAULI_X)
    z = Gate("Z", _PAULI_Z)
    gates = [
        embed_one_qubit_gate(x, qubit, num_qubits)
        for qubit in range(num_qubits)
    ] + [
        embed_one_qubit_gate(z, qubit, num_qubits)
        for qubit in range(num_qubits)
    ]
    return GateSet(gates, projective_config=projective_config)


def projective_pauli_group(
    num_qubits: int,
    *,
    max_elements: int = DEFAULT_PAULI_CATALOG_LIMIT,
    projective_config: ProjectiveConfig = DEFAULT_PROJECTIVE_CONFIG,
) -> GateSet:
    """Return the named projective ``n``-qubit Pauli group as dense gates.

    Labels use tensor words such as ``X_0 Z_2`` and omit identity factors.  The
    all-identity word is named ``I``.  Because the catalog has exactly ``4**n``
    dense matrices, construction is refused when it would exceed
    ``max_elements``.
    """

    if not isinstance(num_qubits, int) or isinstance(num_qubits, bool):
        raise TypeError("num_qubits must be an integer")
    if num_qubits < 1:
        raise ValueError("num_qubits must be at least 1")
    if not isinstance(max_elements, int) or isinstance(max_elements, bool):
        raise TypeError("max_elements must be an integer")
    if max_elements < 1:
        raise ValueError("max_elements must be at least 1")
    group_order = 4**num_qubits
    if group_order > max_elements:
        raise ValueError(
            f"the projective Pauli catalog has {group_order} elements, "
            f"exceeding max_elements={max_elements}"
        )

    gates: list[Gate] = []
    for letters in product(_PAULI_FACTORS, repeat=num_qubits):
        matrix = np.array([[1]], dtype=np.complex128)
        for letter in letters:
            matrix = np.kron(matrix, _PAULI_FACTORS[letter])
        label = " ".join(
            f"{letter}_{qubit}"
            for qubit, letter in enumerate(letters)
            if letter != "I"
        )
        gates.append(Gate(label or "I", matrix))
    return GateSet(gates, projective_config=projective_config)


def _validate_qubit_index(qubit: int, num_qubits: int) -> None:
    if not isinstance(num_qubits, int) or isinstance(num_qubits, bool):
        raise TypeError("num_qubits must be an integer")
    if num_qubits < 1:
        raise ValueError("num_qubits must be at least 1")
    if not isinstance(qubit, int) or isinstance(qubit, bool):
        raise TypeError("qubit must be an integer")
    if not 0 <= qubit < num_qubits:
        raise IndexError(f"qubit {qubit} is outside a {num_qubits}-qubit system")
