import numpy as np
import pytest

from clifford_conjugation import PauliWord, projective_pauli_group, recognize_pauli_word

X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.diag([1, -1]).astype(complex)
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)


def test_direct_recognition_matches_two_qubit_catalog_labels() -> None:
    catalog = projective_pauli_group(2)

    assert {recognize_pauli_word(gate.matrix).label for gate in catalog} == {
        gate.name for gate in catalog
    }


@pytest.mark.parametrize("phase", [1, -1, 1j, np.exp(0.37j)])
def test_recognition_ignores_global_phase(phase: complex) -> None:
    word = recognize_pauli_word(phase * np.kron(Y, Z))

    assert word == PauliWord(num_qubits=2, x_mask=2, z_mask=3)
    assert word.label == "Y_0 Z_1"
    assert str(word) == "Y_0 Z_1"


@pytest.mark.parametrize(
    "matrix",
    [
        H,
        2 * X,
        np.zeros((2, 2)),
        np.array([[0, 1], [1j, 0]]),
        np.array([[0, 1], [1, 0]], dtype=complex) + 0.1 * np.eye(2),
    ],
)
def test_recognition_rejects_non_paulis(matrix: np.ndarray) -> None:
    assert recognize_pauli_word(matrix) is None


def test_recognition_tolerates_small_dense_noise() -> None:
    noisy = np.array(X, copy=True)
    noisy[0, 0] = 1e-12
    noisy[1, 1] = -1e-12

    assert recognize_pauli_word(noisy).label == "X_0"


def test_recognition_validates_matrix_shape() -> None:
    with pytest.raises(ValueError, match="square"):
        recognize_pauli_word(np.ones((2, 3)))
    with pytest.raises(ValueError, match="power of two"):
        recognize_pauli_word(np.eye(3))


def test_pauli_word_validates_masks() -> None:
    with pytest.raises(ValueError, match="does not fit"):
        PauliWord(1, x_mask=2, z_mask=0)
    with pytest.raises(TypeError, match="z_mask"):
        PauliWord(1, x_mask=0, z_mask=False)
