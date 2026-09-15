import numpy as np
import pytest

from clifford_conjugation import (
    Gate,
    embed_one_qubit_gate,
    pauli_generators,
    projective_pauli_group,
    projectively_equal,
)

PAULI_X = np.array([[0, 1], [1, 0]], dtype=complex)
PAULI_Z = np.diag([1, -1]).astype(complex)


def test_one_qubit_pauli_generators_have_standard_order() -> None:
    probes = pauli_generators(1)

    assert [gate.name for gate in probes] == ["X_0", "Z_0"]
    assert np.array_equal(probes[0].matrix, PAULI_X)
    assert np.array_equal(probes[1].matrix, PAULI_Z)


def test_two_qubit_embedding_uses_qubit_zero_as_most_significant() -> None:
    identity = np.eye(2)
    probes = pauli_generators(2)

    assert [gate.name for gate in probes] == ["X_0", "X_1", "Z_0", "Z_1"]
    assert projectively_equal(probes[0].matrix, np.kron(PAULI_X, identity))
    assert projectively_equal(probes[1].matrix, np.kron(identity, PAULI_X))
    assert projectively_equal(probes[2].matrix, np.kron(PAULI_Z, identity))
    assert projectively_equal(probes[3].matrix, np.kron(identity, PAULI_Z))


def test_projective_pauli_catalog_has_algebraic_word_labels() -> None:
    one_qubit = projective_pauli_group(1)
    two_qubit = projective_pauli_group(2)

    assert [gate.name for gate in one_qubit] == ["I", "X_0", "Y_0", "Z_0"]
    assert len(two_qubit) == 16
    xz = next(gate for gate in two_qubit if gate.name == "X_0 Z_1")
    assert projectively_equal(xz.matrix, np.kron(PAULI_X, PAULI_Z))


def test_projective_pauli_catalog_enforces_size_limit() -> None:
    with pytest.raises(ValueError, match="exceeding max_elements"):
        projective_pauli_group(3, max_elements=63)
    with pytest.raises(TypeError, match="max_elements must be an integer"):
        projective_pauli_group(1, max_elements=True)
    with pytest.raises(ValueError, match="max_elements must be at least 1"):
        projective_pauli_group(1, max_elements=0)


def test_embedding_accepts_a_custom_name() -> None:
    phase = Gate("S", np.diag([1, 1j]))
    embedded = embed_one_qubit_gate(phase, 1, 2, name="phase-on-target")

    assert embedded.name == "phase-on-target"
    assert projectively_equal(embedded.matrix, np.kron(np.eye(2), phase.matrix))


def test_embedding_validation_is_explicit() -> None:
    with pytest.raises(TypeError, match="must be a Gate"):
        embed_one_qubit_gate(PAULI_X, 0, 1)
    with pytest.raises(ValueError, match="one-qubit"):
        embed_one_qubit_gate(Gate.identity(2), 0, 2)
    with pytest.raises(IndexError, match="outside"):
        embed_one_qubit_gate(Gate("X", PAULI_X), 2, 2)
    with pytest.raises(TypeError, match="qubit must be an integer"):
        embed_one_qubit_gate(Gate("X", PAULI_X), True, 2)
    with pytest.raises(TypeError, match="num_qubits must be an integer"):
        embed_one_qubit_gate(Gate("X", PAULI_X), 0, 2.0)
    with pytest.raises(TypeError, match="integer"):
        pauli_generators(True)
    with pytest.raises(ValueError, match="at least 1"):
        pauli_generators(0)
