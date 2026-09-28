import numpy as np
import pytest

from clifford_conjugation import (
    analyze_diagonal_c3,
    ccz_gate,
    conjugation_action,
    conjugation_action_table,
    controlled_t_gate,
    eighth_root_diagonal_gate,
    pauli_generators,
)


def _numerical_x_image_clifford_flags(gate) -> tuple[bool, ...]:
    probes = pauli_generators(gate.num_qubits)
    action = conjugation_action(gate, probes)
    return tuple(
        conjugation_action_table(action.image(qubit), probes)
        .classify_paulis()
        .preserves_paulis
        for qubit in range(gate.num_qubits)
    )


def test_ccz_is_exactly_proper_third_level() -> None:
    exponents = (0, 0, 0, 0, 0, 0, 0, 4)
    analysis = analyze_diagonal_c3(exponents)

    assert analysis.phase_polynomial_coefficients == (0, 0, 0, 0, 0, 0, 0, 4)
    assert analysis.x_images_are_clifford == (True, True, True)
    assert not analysis.is_clifford
    assert analysis.is_in_third_level
    assert analysis.is_proper_third_level
    assert _numerical_x_image_clifford_flags(ccz_gate()) == (
        True,
        True,
        True,
    )


def test_controlled_t_is_exactly_outside_third_level() -> None:
    analysis = analyze_diagonal_c3((0, 0, 0, 1))

    assert analysis.phase_polynomial_coefficients == (0, 0, 0, 1)
    assert analysis.x_images_are_clifford == (False, False)
    assert not analysis.is_clifford
    assert not analysis.is_in_third_level
    assert not analysis.is_proper_third_level
    assert _numerical_x_image_clifford_flags(controlled_t_gate()) == (False, False)


def test_eighth_root_constructor_normalizes_exact_exponents() -> None:
    gate = eighth_root_diagonal_gate("phase", (8, -1))

    assert np.allclose(gate.matrix, np.diag([1, np.exp(-1j * np.pi / 4)]))
    assert analyze_diagonal_c3((8, -1)).phase_exponents == (0, 7)


@pytest.mark.parametrize("exponents", [(), (0,), (0, 0, 0)])
def test_exact_diagonal_analysis_requires_qubit_dimension(exponents) -> None:
    with pytest.raises(ValueError, match="power of two"):
        analyze_diagonal_c3(exponents)


@pytest.mark.parametrize("exponents", [(0, 1.0), (0, True), "01"])
def test_exact_diagonal_analysis_requires_integer_exponents(exponents) -> None:
    with pytest.raises(TypeError, match="integers"):
        analyze_diagonal_c3(exponents)
