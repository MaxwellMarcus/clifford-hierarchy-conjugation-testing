import numpy as np
import pytest

from clifford_conjugation import (
    Gate,
    GateSet,
    ProjectiveConfig,
    canonicalize_projective,
    projectively_equal,
)

IDENTITY = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)


def test_gate_validates_and_reports_shape() -> None:
    gate = Gate("X", X)

    assert gate.dimension == 2
    assert gate.num_qubits == 1
    assert not gate.matrix.flags.writeable
    with pytest.raises(ValueError):
        gate.matrix[0, 0] = 2


@pytest.mark.parametrize(
    "matrix, message",
    [
        (np.ones((2, 3)), "square"),
        (np.eye(3), "power of two"),
        (np.array([[1, 1], [0, 1]]), "unitary"),
        (np.array([[np.inf, 0], [0, 1]]), "finite"),
    ],
)
def test_gate_rejects_invalid_matrices(matrix: np.ndarray, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Gate("bad", matrix)


def test_gate_composition_and_adjoint() -> None:
    phase = Gate("S", np.diag([1, 1j]), validation_atol=1e-7)
    x_gate = Gate("X", X, validation_atol=1e-6)

    assert projectively_equal(phase.then(phase).matrix, np.diag([1, -1]))
    assert projectively_equal(phase.then(phase.dagger()).matrix, IDENTITY)
    assert phase.dagger().validation_atol == 1e-7
    assert phase.then(x_gate).validation_atol == 1e-6
    assert Gate.identity(2).num_qubits == 2


def test_projective_normalization_removes_global_phase_and_noise() -> None:
    noisy = 1j * X + np.array([[1e-12, 0], [0, -1e-12]])
    config = ProjectiveConfig(atol=1e-10, decimals=9)

    assert projectively_equal(noisy, X, config)
    assert np.array_equal(canonicalize_projective(1j * X, config), X)
    with pytest.raises(ValueError, match="zero matrix"):
        canonicalize_projective(np.zeros((2, 2)), config)


def test_projective_key_erases_signed_zero_after_rounding() -> None:
    config = ProjectiveConfig(atol=1e-12, decimals=0)
    positive_zero = np.array([[1, 0.1], [0, 1]], dtype=complex)
    negative_zero = np.array([[1, -0.1], [0, 1]], dtype=complex)

    assert projectively_equal(positive_zero, negative_zero, config)


def test_pivot_selection_can_separate_nearby_unitaries_at_atol_boundary() -> None:
    config = ProjectiveConfig(atol=1e-6, decimals=12)

    def boundary_unitary(sine: float) -> np.ndarray:
        cosine = np.sqrt(1.0 - sine**2)
        return np.array([[1j * sine, cosine], [cosine, 1j * sine]])

    at_boundary = boundary_unitary(config.atol)
    above_boundary = boundary_unitary(np.nextafter(config.atol, np.inf))

    assert np.allclose(at_boundary, above_boundary, atol=1e-20, rtol=0)
    assert not projectively_equal(at_boundary, above_boundary, config)


def test_component_threshold_merges_atol_but_separates_just_above() -> None:
    config = ProjectiveConfig(atol=1e-3, decimals=5)
    identity = np.eye(2, dtype=complex)

    def phase_with_imaginary_part(imaginary: float) -> complex:
        return np.sqrt(1.0 - imaginary**2) + 1j * imaginary

    at_boundary = np.diag([1, phase_with_imaginary_part(config.atol)])
    above_boundary = np.diag(
        [1, phase_with_imaginary_part(np.nextafter(config.atol, np.inf))]
    )

    assert projectively_equal(identity, at_boundary, config)
    assert not projectively_equal(identity, above_boundary, config)


def test_decimal_rounding_can_merge_distinct_unitaries() -> None:
    config = ProjectiveConfig(atol=1e-6, decimals=2)
    positive_phase = np.diag([1, np.exp(0.004j)])
    negative_phase = np.diag([1, np.exp(-0.004j)])

    assert not np.allclose(positive_phase, negative_phase, atol=config.atol, rtol=0)
    assert projectively_equal(positive_phase, negative_phase, config)


def test_decimal_half_step_can_separate_nearby_unitaries() -> None:
    config = ProjectiveConfig(atol=1e-6, decimals=2)
    below_half_step = np.diag([1, np.exp(0.0049j)])
    above_half_step = np.diag([1, np.exp(0.0051j)])

    assert not projectively_equal(below_half_step, above_half_step, config)


def test_gate_set_eliminates_projective_duplicates() -> None:
    gates = GateSet(
        [Gate("I", IDENTITY), Gate("phase-I", 1j * IDENTITY), Gate("X", X)]
    )

    assert [gate.name for gate in gates] == ["I", "X"]
    assert gates.contains_matrix(-X)
    assert gates.match_matrix(1j * X).name == "X"
    assert not gates.contains_matrix(np.eye(4))
    assert gates.match_matrix(np.zeros((2, 2))) is None


def test_gate_set_rejects_ambiguous_names_and_dimensions() -> None:
    with pytest.raises(ValueError, match="different operators"):
        GateSet([Gate("same", IDENTITY), Gate("same", X)])
    with pytest.raises(ValueError, match="same dimension"):
        GateSet([Gate("I", IDENTITY), Gate.identity(2)])
    with pytest.raises(ValueError, match="at least one"):
        GateSet([])


def test_projective_config_validation() -> None:
    with pytest.raises(ValueError, match="positive finite"):
        ProjectiveConfig(atol=0)
    with pytest.raises(ValueError, match="nonnegative"):
        ProjectiveConfig(decimals=-1)
