import numpy as np
import pytest

from clifford_conjugation import (
    Gate,
    GateSet,
    ProjectiveConfig,
    SearchLimits,
    conjugate,
    generate_conjugation_group,
    generate_conjugation_groups,
    generate_next_conjugation_group,
    projectively_equal,
)

X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.diag([1, -1]).astype(complex)
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)


def test_conjugate_uses_u_p_u_dagger_convention() -> None:
    image = conjugate(Gate("H", H), Gate("X", X))

    assert projectively_equal(image.matrix, Z)
    assert image.name == "H X H†"


def test_hadamard_conjugation_groups_stabilize_at_paulis() -> None:
    probes = GateSet([Gate("X", X), Gate("Z", Z)])
    first, second = generate_conjugation_groups(Gate("H", H), probes, depth=2)

    assert first.complete and second.complete
    assert first.order == 4
    assert second.order == 4
    assert len(first.defining_generators) == 2
    assert first.elements.contains_matrix(X @ Z)
    assert first.action_table is not None
    assert first.action_table.shape == (1, 2)


def test_next_level_propagates_incomplete_source() -> None:
    probes = GateSet([Gate("X", X), Gate("Z", Z)])
    theta = np.pi * np.sqrt(2)
    seed = Gate("R", np.diag([1, np.exp(1j * theta)]))
    first = generate_conjugation_group(
        seed,
        probes,
        limits=SearchLimits(max_elements=3, max_products=100),
    )
    second = generate_next_conjugation_group(
        first,
        probes,
        limits=SearchLimits(max_elements=64, max_products=10_000),
    )

    assert not first.complete
    assert not second.source_complete
    assert not second.complete
    assert second.order is None
    assert second.action_table is not None
    assert not second.action_table.source_complete


def test_set_of_seed_conjugators_is_supported_and_deduplicated() -> None:
    probes = GateSet([Gate("X", X), Gate("Z", Z)])
    seeds = GateSet([Gate("I", np.eye(2)), Gate("H", H)])

    result = generate_conjugation_group(seeds, probes)

    assert result.complete
    assert result.order == 4
    assert len(result.defining_generators) == 2


def test_conjugation_input_validation() -> None:
    probes = GateSet([Gate("X", X)])
    with pytest.raises(ValueError, match="same dimension"):
        conjugate(Gate("X", X), Gate.identity(2))
    with pytest.raises(ValueError, match="depth"):
        generate_conjugation_groups(Gate("X", X), probes, depth=0)
    with pytest.raises(ValueError, match="same dimension"):
        generate_conjugation_group(Gate.identity(2), probes)
    with pytest.raises(TypeError, match="source_complete"):
        generate_conjugation_group(Gate("X", X), probes, source_complete="yes")

    other_config = GateSet(
        [Gate("X", X)],
        projective_config=ProjectiveConfig(decimals=8),
    )
    with pytest.raises(ValueError, match="projective settings"):
        generate_conjugation_group(other_config, probes)
