"""Reproducible records for bounded dense conjugation-group searches."""

from __future__ import annotations

import json
import math
import time
import tracemalloc
from dataclasses import asdict, dataclass

from .conjugation import ConjugationGroup, generate_conjugation_group
from .groups import DEFAULT_SEARCH_LIMITS, SearchLimits
from .operators import Gate, GateSet

GROUP_SEARCH_BENCHMARK_SCHEMA = "clifford-conjugation/group-search-benchmark-v1"


@dataclass(frozen=True)
class GroupSearchWorkload:
    """Exact dimensions and counters for a bounded group search."""

    num_qubits: int
    source_size: int
    probe_generator_count: int
    action_table_cells: int
    defining_generator_count: int
    max_elements: int
    max_products: int
    products_tested: int
    discovered_elements: int
    max_word_length: int

    def to_dict(self) -> dict[str, int]:
        """Return a JSON-compatible exact-workload payload."""

        return asdict(self)


@dataclass(frozen=True)
class GroupSearchOutcome:
    """Completeness-aware mathematical outcome of a group search."""

    source_complete: bool
    closure_complete: bool
    complete: bool
    stop_reason: str
    group_order: int | None

    def to_dict(self) -> dict[str, bool | int | str | None]:
        """Return a JSON-compatible outcome payload."""

        return asdict(self)


@dataclass(frozen=True)
class GroupSearchMeasurements:
    """Machine-dependent measurements for one benchmark run."""

    runtime_seconds: float
    peak_python_memory_bytes: int


@dataclass(frozen=True)
class GroupSearchBenchmarkRecord:
    """Versioned benchmark data with exact and host-dependent fields split."""

    schema: str
    workload: GroupSearchWorkload
    outcome: GroupSearchOutcome
    measurements: GroupSearchMeasurements

    def to_dict(self) -> dict[str, object]:
        """Return the versioned JSON-compatible record."""

        return {
            "measurements": asdict(self.measurements),
            "outcome": self.outcome.to_dict(),
            "schema": self.schema,
            "workload": self.workload.to_dict(),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize the record deterministically."""

        return json.dumps(self.to_dict(), allow_nan=False, indent=indent, sort_keys=True)


@dataclass(frozen=True)
class GroupSearchBenchmarkRun:
    """Pair a conjugation-group result with its benchmark record."""

    result: ConjugationGroup
    record: GroupSearchBenchmarkRecord


def build_group_search_benchmark_record(
    result: ConjugationGroup,
    *,
    source_size: int,
    probe_generator_count: int,
    runtime_seconds: float,
    peak_python_memory_bytes: int,
) -> GroupSearchBenchmarkRecord:
    """Build a validated record from an existing conjugation-group result."""

    if not isinstance(source_size, int) or isinstance(source_size, bool) or source_size < 1:
        raise ValueError("source_size must be a positive integer")
    if (
        not isinstance(probe_generator_count, int)
        or isinstance(probe_generator_count, bool)
        or probe_generator_count < 1
    ):
        raise ValueError("probe_generator_count must be a positive integer")
    if not math.isfinite(runtime_seconds) or runtime_seconds < 0:
        raise ValueError("runtime_seconds must be finite and nonnegative")
    if (
        not isinstance(peak_python_memory_bytes, int)
        or isinstance(peak_python_memory_bytes, bool)
        or peak_python_memory_bytes < 0
    ):
        raise ValueError("peak_python_memory_bytes must be a nonnegative integer")
    if result.action_table is None:
        raise ValueError("result must retain its conjugation action table")
    expected_shape = (source_size, probe_generator_count)
    if result.action_table.shape != expected_shape:
        raise ValueError(
            f"source and probe counts imply action-table shape {expected_shape}, "
            f"not {result.action_table.shape}"
        )

    closure = result.closure
    workload = GroupSearchWorkload(
        num_qubits=result.defining_generators.num_qubits,
        source_size=source_size,
        probe_generator_count=probe_generator_count,
        action_table_cells=source_size * probe_generator_count,
        defining_generator_count=len(result.defining_generators),
        max_elements=closure.limits.max_elements,
        max_products=closure.limits.max_products,
        products_tested=closure.products_tested,
        discovered_elements=len(closure.elements),
        max_word_length=closure.max_word_length,
    )
    outcome = GroupSearchOutcome(
        source_complete=result.source_complete,
        closure_complete=closure.complete,
        complete=result.complete,
        stop_reason=closure.stop_reason.value,
        group_order=result.order,
    )
    return GroupSearchBenchmarkRecord(
        schema=GROUP_SEARCH_BENCHMARK_SCHEMA,
        workload=workload,
        outcome=outcome,
        measurements=GroupSearchMeasurements(
            runtime_seconds=float(runtime_seconds),
            peak_python_memory_bytes=peak_python_memory_bytes,
        ),
    )


def run_conjugation_group_benchmark(
    conjugators: Gate | GateSet,
    probe_generators: GateSet,
    *,
    level: int = 1,
    source_complete: bool = True,
    limits: SearchLimits = DEFAULT_SEARCH_LIMITS,
) -> GroupSearchBenchmarkRun:
    """Run a bounded search while measuring wall time and Python peak memory.

    Runtime covers action-table construction, projective deduplication, and
    group closure. Peak memory comes from :mod:`tracemalloc`, so it excludes
    allocations made only inside NumPy's native code. The process-global
    tracer must be idle before a benchmark starts.
    """

    if tracemalloc.is_tracing():
        raise RuntimeError("cannot benchmark while tracemalloc is already active")
    source_size = 1 if isinstance(conjugators, Gate) else len(conjugators)
    probe_generator_count = len(probe_generators)
    tracemalloc.start()
    started = time.perf_counter()
    try:
        result = generate_conjugation_group(
            conjugators,
            probe_generators,
            level=level,
            source_complete=source_complete,
            limits=limits,
        )
        elapsed = time.perf_counter() - started
        _, peak_python_memory_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    record = build_group_search_benchmark_record(
        result,
        source_size=source_size,
        probe_generator_count=probe_generator_count,
        runtime_seconds=elapsed,
        peak_python_memory_bytes=peak_python_memory_bytes,
    )
    return GroupSearchBenchmarkRun(result=result, record=record)
