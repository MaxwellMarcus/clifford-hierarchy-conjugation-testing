"""Stable machine-readable summaries of numerical conjugation-group searches."""

from __future__ import annotations

import json
from typing import Any

from .conjugation import ConjugationGroup

WITNESS_SCHEMA = "clifford-conjugation/numerical-witness-v1"


def build_numerical_witness(group: ConjugationGroup) -> dict[str, Any]:
    """Return a JSON-compatible witness for one numerical group search.

    The witness intentionally records numerical tolerances and incomplete-search
    metadata.  It is an inspectable transcript of the dense computation, not an
    exact proof of the represented algebraic claims.
    """

    table = group.action_table
    if table is None:
        raise ValueError("witness export requires retained action-table metadata")

    config = group.defining_generators.projective_config
    classification = table.classify_paulis()
    classification_rows = []
    for conjugator, labels in zip(
        table.conjugators,
        classification.as_rows(),
        strict=True,
    ):
        classification_rows.append(
            {
                "conjugator": conjugator.name,
                "images": [
                    {"probe": probe.name, "pauli": label}
                    for probe, label in zip(table.probe_generators, labels, strict=True)
                ],
            }
        )

    defining_generators = []
    for generator, sources in zip(
        group.defining_generators,
        group.defining_generator_sources,
        strict=True,
    ):
        defining_generators.append(
            {
                "name": generator.name,
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
        )

    closure = group.closure
    return {
        "schema": WITNESS_SCHEMA,
        "level": group.level,
        "num_qubits": group.defining_generators.num_qubits,
        "projective_config": {
            "atol": config.atol,
            "decimals": config.decimals,
        },
        "completeness": {
            "source_complete": group.source_complete,
            "closure_complete": closure.complete,
            "complete": group.complete,
            "stop_reason": closure.stop_reason.value,
        },
        "search": {
            "products_tested": closure.products_tested,
            "max_word_length": closure.max_word_length,
            "limits": {
                "max_elements": closure.limits.max_elements,
                "max_products": closure.limits.max_products,
            },
        },
        "defining_generators": defining_generators,
        "closure": {
            "discovered_elements": len(group.elements),
            "order": group.order,
            "generator_words": [list(word) for word in closure.words],
        },
        "classification": {
            "kind": "tensor_pauli",
            "recognized": classification.recognized_count,
            "total": classification.total_count,
            "all_recognized": classification.all_recognized,
            "rows": classification_rows,
        },
    }


def export_numerical_witness(group: ConjugationGroup, *, indent: int | None = 2) -> str:
    """Serialize :func:`build_numerical_witness` as deterministic JSON."""

    return json.dumps(
        build_numerical_witness(group),
        allow_nan=False,
        indent=indent,
        sort_keys=True,
    )
