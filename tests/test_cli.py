from __future__ import annotations

import json

import numpy as np

from clifford_conjugation import Gate, GateSet, ProjectiveConfig, conjugation_action_table
from clifford_conjugation.cli import ACTION_RESULT_SCHEMA, action_table_payload, main
from clifford_conjugation.standard_gates import pauli_generators


def test_action_payload_includes_matrices_classification_and_tolerance() -> None:
    config = ProjectiveConfig(atol=1e-8, decimals=9)
    hadamard = Gate("H", np.array([[1, 1], [1, -1]]) / np.sqrt(2))
    table = conjugation_action_table(
        GateSet((hadamard,), projective_config=config),
        pauli_generators(1, projective_config=config),
    )

    payload = action_table_payload(table)
    assert payload["schema"] == ACTION_RESULT_SCHEMA
    assert payload["projective_config"] == {"atol": 1e-8, "decimals": 9}
    assert payload["classification"]["preserves_paulis"] is True
    assert [image["pauli"] for image in payload["rows"][0]["images"]] == ["Z_0", "X_0"]
    encoded = np.asarray(payload["rows"][0]["images"][0]["matrix"])
    assert np.allclose(encoded[..., 0], np.diag([1, -1]))
    assert np.allclose(encoded[..., 1], 0)


def test_group_cli_preserves_truncation_as_incomplete(tmp_path, capsys) -> None:
    matrix_path = tmp_path / "hadamard.npy"
    np.save(matrix_path, np.array([[1, 1], [1, -1]]) / np.sqrt(2))

    assert main([str(matrix_path), "--name", "H", "group", "--max-elements", "2"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["completeness"] == {
        "closure_complete": False,
        "complete": False,
        "source_complete": True,
        "stop_reason": "max_elements",
    }
    assert payload["closure"]["discovered_elements"] == 2
    assert payload["closure"]["order"] is None
    assert payload["search"]["limits"]["max_elements"] == 2


def test_action_cli_emits_versioned_json(tmp_path, capsys) -> None:
    matrix_path = tmp_path / "identity.npy"
    np.save(matrix_path, np.eye(2))

    assert main([str(matrix_path), "action"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == ACTION_RESULT_SCHEMA
    assert payload["shape"] == [1, 2]
