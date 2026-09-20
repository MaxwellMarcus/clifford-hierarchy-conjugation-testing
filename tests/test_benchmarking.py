from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from clifford_conjugation import (
    GROUP_SEARCH_BENCHMARK_SCHEMA,
    Gate,
    GateSet,
    SearchLimits,
    build_group_search_benchmark_record,
    generate_conjugation_group,
    pauli_generators,
    run_conjugation_group_benchmark,
)

H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)


def test_group_search_benchmark_json_schema_is_stable() -> None:
    result = generate_conjugation_group(
        Gate("H", H),
        pauli_generators(1),
        limits=SearchLimits(max_elements=64, max_products=1_000),
    )
    record = build_group_search_benchmark_record(
        result,
        source_size=1,
        probe_generator_count=2,
        runtime_seconds=0.125,
        peak_python_memory_bytes=4096,
    )

    assert json.loads(record.to_json()) == {
        "measurements": {
            "peak_python_memory_bytes": 4096,
            "runtime_seconds": 0.125,
        },
        "outcome": {
            "closure_complete": True,
            "complete": True,
            "group_order": 4,
            "source_complete": True,
            "stop_reason": "complete",
        },
        "schema": GROUP_SEARCH_BENCHMARK_SCHEMA,
        "workload": {
            "action_table_cells": 2,
            "defining_generator_count": 2,
            "discovered_elements": 4,
            "max_elements": 64,
            "max_products": 1_000,
            "max_word_length": 2,
            "num_qubits": 1,
            "probe_generator_count": 2,
            "products_tested": 8,
            "source_size": 1,
        },
    }


def test_benchmark_measures_runtime_memory_and_source_size() -> None:
    sources = GateSet([Gate("I", np.eye(2)), Gate("H", H)])

    benchmark = run_conjugation_group_benchmark(
        sources,
        pauli_generators(1),
        limits=SearchLimits(max_elements=64, max_products=1_000),
    )

    assert benchmark.result.complete
    assert benchmark.record.workload.source_size == 2
    assert benchmark.record.workload.action_table_cells == 4
    assert benchmark.record.measurements.runtime_seconds > 0
    assert benchmark.record.measurements.peak_python_memory_bytes > 0


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"source_size": 0}, "source_size"),
        ({"probe_generator_count": 0}, "probe_generator_count"),
        ({"runtime_seconds": -0.1}, "runtime_seconds"),
        ({"peak_python_memory_bytes": -1}, "peak_python_memory_bytes"),
    ],
)
def test_benchmark_record_rejects_invalid_metadata(changes, message: str) -> None:
    result = generate_conjugation_group(Gate("H", H), pauli_generators(1))
    arguments = {
        "source_size": 1,
        "probe_generator_count": 2,
        "runtime_seconds": 0.1,
        "peak_python_memory_bytes": 1,
    }
    arguments.update(changes)

    with pytest.raises(ValueError, match=message):
        build_group_search_benchmark_record(result, **arguments)


def test_benchmark_record_rejects_mismatched_action_table_shape() -> None:
    result = generate_conjugation_group(Gate("H", H), pauli_generators(1))

    with pytest.raises(ValueError, match="shape"):
        build_group_search_benchmark_record(
            result,
            source_size=2,
            probe_generator_count=2,
            runtime_seconds=0.1,
            peak_python_memory_bytes=1,
        )


def test_checked_in_small_search_baselines_are_reproducible() -> None:
    baseline_path = Path(__file__).parents[1] / "benchmarks" / "small-group-searches.json"
    payload = json.loads(baseline_path.read_text())
    cases = {
        "one-qubit-hadamard": (
            Gate("H", H),
            pauli_generators(1),
            SearchLimits(max_elements=64, max_products=1_000),
        ),
        "one-qubit-two-sources": (
            GateSet([Gate("I", np.eye(2)), Gate("H", H)]),
            pauli_generators(1),
            SearchLimits(max_elements=64, max_products=1_000),
        ),
        "two-qubit-identity": (
            Gate("I", np.eye(4)),
            pauli_generators(2),
            SearchLimits(max_elements=128, max_products=10_000),
        ),
        "one-qubit-limited-prefix": (
            Gate("H", H),
            pauli_generators(1),
            SearchLimits(max_elements=2, max_products=1_000),
        ),
    }

    reproduced = []
    for expected in payload["baselines"]:
        conjugators, probes, limits = cases[expected["name"]]
        benchmark = run_conjugation_group_benchmark(
            conjugators,
            probes,
            limits=limits,
        )
        reproduced.append(
            {
                "name": expected["name"],
                "outcome": benchmark.record.outcome.to_dict(),
                "workload": benchmark.record.workload.to_dict(),
            }
        )

    assert payload["schema"] == "clifford-conjugation/group-search-workloads-v1"
    assert reproduced == payload["baselines"]
