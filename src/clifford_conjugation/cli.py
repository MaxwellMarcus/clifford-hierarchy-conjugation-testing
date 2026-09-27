"""Structured JSON command-line interface for dense conjugation experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .actions import ConjugationActionTable, conjugation_action_table
from .conjugation import generate_conjugation_group
from .groups import SearchLimits
from .operators import Gate, GateSet, ProjectiveConfig
from .standard_gates import pauli_generators
from .witnesses import build_numerical_witness

ACTION_RESULT_SCHEMA = "clifford-conjugation/action-table-v1"


def _complex_matrix_payload(matrix: np.ndarray) -> list[list[list[float]]]:
    return [
        [[float(value.real), float(value.imag)] for value in row]
        for row in matrix
    ]


def action_table_payload(table: ConjugationActionTable) -> dict[str, object]:
    """Return a versioned, lossless JSON-compatible action-table record."""

    classification = table.classify_paulis()
    config = table.conjugators.projective_config
    rows = []
    for action, labels in zip(table, classification.as_rows(), strict=True):
        rows.append(
            {
                "conjugator": action.conjugator.name,
                "images": [
                    {
                        "probe": probe.name,
                        "name": image.name,
                        "matrix": _complex_matrix_payload(image.matrix),
                        "pauli": label,
                    }
                    for probe, image, label in zip(
                        table.probe_generators,
                        action.images,
                        labels,
                        strict=True,
                    )
                ],
            }
        )
    return {
        "schema": ACTION_RESULT_SCHEMA,
        "claim_scope": "dense numerical projective comparison; not an exact proof",
        "num_qubits": table.conjugators.num_qubits,
        "projective_config": {"atol": config.atol, "decimals": config.decimals},
        "source_complete": table.source_complete,
        "shape": list(table.shape),
        "classification": {
            "kind": "tensor_pauli",
            "recognized": classification.recognized_count,
            "total": classification.total_count,
            "all_recognized": classification.all_recognized,
            "preserves_paulis": classification.preserves_paulis,
        },
        "rows": rows,
        "unique_images": [
            {
                "name": image.name,
                "sources": [
                    {
                        "row": source.row_index,
                        "column": source.column_index,
                        "conjugator": source.conjugator,
                        "probe": source.probe,
                    }
                    for source in sources
                ],
            }
            for image, sources in zip(
                table.unique_images,
                table.unique_image_sources,
                strict=True,
            )
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clifford-conjugation",
        description="Emit versioned JSON for low-qubit dense conjugation experiments.",
    )
    parser.add_argument("matrix", type=Path, help="NumPy .npy file containing a unitary")
    parser.add_argument("--name", default="U", help="stable name for the input unitary")
    parser.add_argument("--atol", type=float, default=1e-9)
    parser.add_argument("--decimals", type=int, default=10)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("action", help="export the Pauli-generator action table")
    group = subparsers.add_parser("group", help="export a numerical group witness")
    group.add_argument("--level", type=int, default=1)
    group.add_argument("--max-elements", type=int, default=4096)
    group.add_argument("--max-products", type=int, default=1_000_000)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run an action or group analysis and print deterministic JSON."""

    args = _parser().parse_args(argv)
    config = ProjectiveConfig(atol=args.atol, decimals=args.decimals)
    matrix = np.load(args.matrix, allow_pickle=False)
    gate = Gate(args.name, matrix, validation_atol=args.atol)
    conjugators = GateSet((gate,), projective_config=config)
    probes = pauli_generators(gate.num_qubits, projective_config=config)
    if args.command == "action":
        payload = action_table_payload(conjugation_action_table(conjugators, probes))
    else:
        group = generate_conjugation_group(
            conjugators,
            probes,
            level=args.level,
            limits=SearchLimits(
                max_elements=args.max_elements,
                max_products=args.max_products,
            ),
        )
        payload = build_numerical_witness(group)
    print(json.dumps(payload, allow_nan=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - console-script entry point
    raise SystemExit(main())
