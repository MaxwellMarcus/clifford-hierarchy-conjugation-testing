import numpy as np
import pytest

from clifford_conjugation import (
    Gate,
    GateSet,
    SearchLimits,
    StopReason,
    generate_group,
)

X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.diag([1, -1]).astype(complex)
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)


def test_single_pauli_generator_closes_projectively() -> None:
    closure = generate_group(GateSet([Gate("X", X)]))

    assert closure.complete
    assert closure.stop_reason is StopReason.COMPLETE
    assert closure.order == 2
    assert closure.words == ((), ("X",))
    assert closure.elements.contains_matrix(-X)


def test_hadamard_and_z_generate_eight_element_projective_group() -> None:
    closure = generate_group(GateSet([Gate("H", H), Gate("Z", Z)]))

    assert closure.complete
    assert closure.order == 8
    assert closure.max_word_length > 0


def test_max_elements_returns_an_explicitly_truncated_prefix() -> None:
    irrational_phase = np.exp(1j * np.pi * np.sqrt(2))
    rotation = Gate("R", np.diag([1, irrational_phase]))

    closure = generate_group(
        GateSet([rotation]),
        limits=SearchLimits(max_elements=4, max_products=100),
    )

    assert not closure.complete
    assert closure.stop_reason is StopReason.MAX_ELEMENTS
    assert closure.order is None
    assert len(closure.elements) == 4


def test_max_products_can_stop_even_after_all_elements_are_discovered() -> None:
    closure = generate_group(
        GateSet([Gate("X", X)]),
        limits=SearchLimits(max_elements=10, max_products=1),
    )

    assert not closure.complete
    assert closure.stop_reason is StopReason.MAX_PRODUCTS
    assert closure.order is None
    assert len(closure.elements) == 2
    assert closure.products_tested == 1


def test_search_limits_are_positive() -> None:
    with pytest.raises(ValueError, match="max_elements"):
        SearchLimits(max_elements=0)
    with pytest.raises(ValueError, match="max_products"):
        SearchLimits(max_products=0)
