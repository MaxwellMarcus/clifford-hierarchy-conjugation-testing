import json
from dataclasses import replace

import numpy as np
import pytest

from clifford_conjugation import (
    WITNESS_SCHEMA,
    ExactPauliAction,
    Gate,
    GateSet,
    SearchLimits,
    build_numerical_witness,
    export_numerical_witness,
    generate_conjugation_group,
    verify_numerical_witness_exact,
)

X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.diag([1, -1]).astype(complex)
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)


def pauli_probes() -> GateSet:
    return GateSet([Gate("X", X), Gate("Z", Z)])


def test_witness_records_words_classification_provenance_and_tolerance() -> None:
    group = generate_conjugation_group(Gate("H", H), pauli_probes())

    witness = build_numerical_witness(group)

    assert witness["schema"] == WITNESS_SCHEMA
    assert witness["projective_config"] == {"atol": 1e-9, "decimals": 10}
    assert witness["completeness"] == {
        "source_complete": True,
        "closure_complete": True,
        "complete": True,
        "stop_reason": "complete",
    }
    assert witness["closure"]["order"] == 4
    assert witness["closure"]["generator_words"] == [
        [],
        ["H X H†"],
        ["H Z H†"],
        ["H X H†", "H Z H†"],
    ]
    assert witness["classification"] == {
        "kind": "tensor_pauli",
        "recognized": 2,
        "total": 2,
        "all_recognized": True,
        "rows": [
            {
                "conjugator": "H",
                "images": [
                    {"probe": "X", "pauli": "Z_0"},
                    {"probe": "Z", "pauli": "X_0"},
                ],
            }
        ],
    }
    assert witness["defining_generators"][0]["sources"] == [
        {"row": 0, "column": 0, "conjugator": "H", "probe": "X"}
    ]


def test_json_export_is_deterministic_and_machine_readable() -> None:
    group = generate_conjugation_group(Gate("H", H), pauli_probes())

    first = export_numerical_witness(group)
    second = export_numerical_witness(group)

    assert first == second
    assert json.loads(first) == build_numerical_witness(group)


def test_truncated_search_never_exports_a_proven_order() -> None:
    theta = np.pi * np.sqrt(2)
    group = generate_conjugation_group(
        Gate("R", np.diag([1, np.exp(1j * theta)])),
        pauli_probes(),
        limits=SearchLimits(max_elements=3, max_products=100),
    )

    witness = build_numerical_witness(group)

    assert not witness["completeness"]["complete"]
    assert witness["completeness"]["stop_reason"] == "max_elements"
    assert witness["closure"]["discovered_elements"] == 3
    assert witness["closure"]["order"] is None


def test_witness_requires_retained_action_metadata() -> None:
    group = generate_conjugation_group(Gate("H", H), pauli_probes())
    group_without_table = replace(
        group,
        action_table=None,
        defining_generator_sources=(),
    )

    with pytest.raises(ValueError, match="action-table metadata"):
        build_numerical_witness(group_without_table)


def exact_hadamard_action() -> ExactPauliAction:
    return ExactPauliAction.from_labels(
        "H",
        1,
        {"X": "Z_0", "Z": "X_0"},
    )


def test_exact_verifier_checks_classifications_provenance_and_closure() -> None:
    group = generate_conjugation_group(Gate("H", H), pauli_probes())
    payload = export_numerical_witness(group)

    verification = verify_numerical_witness_exact(
        payload,
        {"H": exact_hadamard_action()},
    )

    assert verification.valid
    assert verification.classification_cells_verified == 2
    assert verification.closure_elements_verified == 4
    assert verification.closure_complete_verified
    assert verification.errors == ()


def test_exact_verifier_rejects_tampered_numerical_classification() -> None:
    group = generate_conjugation_group(Gate("H", H), pauli_probes())
    witness = build_numerical_witness(group)
    witness["classification"]["rows"][0]["images"][0]["pauli"] = "X_0"

    verification = verify_numerical_witness_exact(
        witness,
        {"H": exact_hadamard_action()},
    )

    assert not verification.valid
    assert any("exact action gives 'Z_0'" in error for error in verification.errors)


def test_exact_verifier_rejects_tampered_complete_closure() -> None:
    group = generate_conjugation_group(Gate("H", H), pauli_probes())
    witness = build_numerical_witness(group)
    witness["closure"]["generator_words"].pop()
    witness["closure"]["discovered_elements"] = 3
    witness["closure"]["order"] = 3

    verification = verify_numerical_witness_exact(
        witness,
        {"H": exact_hadamard_action()},
    )

    assert not verification.valid
    assert not verification.closure_complete_verified
    assert any("exact generated Pauli group" in error for error in verification.errors)


def test_exact_verifier_rejects_tampered_generator_provenance() -> None:
    group = generate_conjugation_group(Gate("H", H), pauli_probes())
    witness = build_numerical_witness(group)
    witness["defining_generators"][0]["sources"][0]["probe"] = "Z"

    verification = verify_numerical_witness_exact(
        witness,
        {"H": exact_hadamard_action()},
    )

    assert not verification.valid
    assert any("inconsistent source names" in error for error in verification.errors)


def test_exact_verifier_rejects_wrong_schema() -> None:
    verification = verify_numerical_witness_exact(
        {"schema": "future-version", "num_qubits": 1},
        {},
    )

    assert not verification.valid
    assert verification.errors[0].startswith("schema must equal")
