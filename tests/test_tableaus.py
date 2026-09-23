import numpy as np
import pytest

from clifford_conjugation import (
    Gate,
    GateSet,
    PauliWord,
    SearchLimits,
    StopReason,
    SymplecticTableau,
    cnot_tableau,
    generate_group,
    generate_tableau_group,
    hadamard_tableau,
    phase_tableau,
    projective_pauli_group,
    recognize_pauli_word,
    tableau_from_dense_clifford,
)

H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
S = np.diag([1, 1j]).astype(complex)


def test_projective_pauli_arithmetic_is_exact() -> None:
    x = PauliWord(1, 1, 0)
    y = PauliWord(1, 1, 1)
    z = PauliWord(1, 0, 1)

    assert x.multiply(z) == y
    assert not x.commutes_with(z)
    assert y.commutes_with(y)
    with pytest.raises(ValueError, match="same qubit count"):
        x.multiply(PauliWord(2, 1, 0))


def test_standard_tableaus_have_expected_pauli_actions() -> None:
    x0 = PauliWord(2, 2, 0)
    x1 = PauliWord(2, 1, 0)
    z0 = PauliWord(2, 0, 2)
    z1 = PauliWord(2, 0, 1)

    assert hadamard_tableau(0, 2).apply(x0) == z0
    assert phase_tableau(1, 2).apply(x1) == PauliWord(2, 1, 1)
    assert cnot_tableau(0, 1, 2).apply(x0) == x0.multiply(x1)
    assert cnot_tableau(0, 1, 2).apply(z1) == z0.multiply(z1)


def test_dense_clifford_extraction_matches_exact_constructors() -> None:
    cnot = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
        dtype=complex,
    )

    assert tableau_from_dense_clifford(Gate("H", H)) == hadamard_tableau(0, 1)
    assert tableau_from_dense_clifford(Gate("S", S)) == phase_tableau(0, 1)
    assert tableau_from_dense_clifford(Gate("CNOT", cnot)) == cnot_tableau(0, 1, 2)
    t_gate = Gate("T", np.diag([1, np.exp(1j * np.pi / 4)]))
    assert tableau_from_dense_clifford(t_gate) is None


def test_two_qubit_tableau_matches_dense_action_on_every_pauli() -> None:
    cnot = np.array(
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]],
        dtype=complex,
    )
    tableau = cnot_tableau(0, 1, 2)
    for pauli in projective_pauli_group(2):
        word = recognize_pauli_word(pauli.matrix)
        dense_image = cnot @ pauli.matrix @ cnot.conj().T
        assert word is not None
        assert tableau.apply(word) == recognize_pauli_word(dense_image)


def test_exact_action_closure_matches_dense_one_qubit_cliffords() -> None:
    h_tableau = hadamard_tableau(0, 1)
    s_tableau = phase_tableau(0, 1)
    exact = generate_tableau_group({"H": h_tableau, "S": s_tableau})
    dense = generate_group(
        GateSet([Gate("H", H), Gate("S", S)]),
        limits=SearchLimits(max_elements=32, max_products=128),
    )
    dense_actions = {tableau_from_dense_clifford(gate) for gate in dense.elements}

    assert dense.complete and dense.order == 24
    assert exact.complete and exact.order == 6
    assert set(exact.elements) == dense_actions
    assert exact.words[0] == ()


def test_tableau_closure_preserves_explicit_incomplete_state() -> None:
    closure = generate_tableau_group(
        {"H": hadamard_tableau(0, 1), "S": phase_tableau(0, 1)},
        limits=SearchLimits(max_elements=2, max_products=100),
    )

    assert not closure.complete
    assert closure.order is None
    assert closure.stop_reason is StopReason.MAX_ELEMENTS
    assert len(closure.elements) == 2


def test_tableau_validation_rejects_non_symplectic_and_mismatched_inputs() -> None:
    with pytest.raises(ValueError, match="symplectic"):
        SymplecticTableau(1, np.zeros((2, 2), dtype=np.uint8))
    with pytest.raises(ValueError, match="different"):
        cnot_tableau(0, 0, 1)
    with pytest.raises(ValueError, match="same qubit count"):
        hadamard_tableau(0, 1).compose(SymplecticTableau.identity(2))
    with pytest.raises(ValueError, match="same qubit count"):
        hadamard_tableau(0, 1).apply(PauliWord(2, 1, 0))
