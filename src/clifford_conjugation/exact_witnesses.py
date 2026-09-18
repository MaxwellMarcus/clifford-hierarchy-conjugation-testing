"""Exact binary-Pauli verification for exported numerical witnesses."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .paulis import PauliWord
from .witnesses import WITNESS_SCHEMA


def _parse_pauli_label(label: str, num_qubits: int) -> PauliWord:
    if label == "I":
        return PauliWord(num_qubits, 0, 0)
    if not isinstance(label, str) or not label:
        raise ValueError("Pauli labels must be nonempty strings")
    x_mask = 0
    z_mask = 0
    occupied: set[int] = set()
    for factor in label.split():
        try:
            letter, index_text = factor.split("_", maxsplit=1)
            qubit = int(index_text)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid Pauli factor {factor!r}") from error
        if letter not in {"X", "Y", "Z"} or not 0 <= qubit < num_qubits:
            raise ValueError(f"invalid Pauli factor {factor!r}")
        if qubit in occupied:
            raise ValueError(f"Pauli label repeats qubit {qubit}")
        occupied.add(qubit)
        bit = 1 << (num_qubits - 1 - qubit)
        if letter in {"X", "Y"}:
            x_mask |= bit
        if letter in {"Y", "Z"}:
            z_mask |= bit
    return PauliWord(num_qubits, x_mask, z_mask)


def _multiply_paulis(left: PauliWord, right: PauliWord) -> PauliWord:
    if left.num_qubits != right.num_qubits:
        raise ValueError("Pauli words use different qubit counts")
    return PauliWord(
        left.num_qubits,
        left.x_mask ^ right.x_mask,
        left.z_mask ^ right.z_mask,
    )


@dataclass(frozen=True)
class ExactPauliAction:
    """A named exact action on exported probes, modulo scalar Pauli phase.

    This is the version-one exact gate domain: callers supply each conjugator's
    probe images as binary tensor-Pauli words. The verifier therefore never
    consults the dense matrices or their numerical classification tolerance.
    """

    name: str
    num_qubits: int
    images: tuple[tuple[str, PauliWord], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("action name must be a nonempty string")
        if not isinstance(self.num_qubits, int) or isinstance(self.num_qubits, bool):
            raise TypeError("num_qubits must be an integer")
        if self.num_qubits < 1:
            raise ValueError("num_qubits must be at least 1")
        names: set[str] = set()
        for probe, image in self.images:
            if not isinstance(probe, str) or not probe:
                raise ValueError("probe names must be nonempty strings")
            if probe in names:
                raise ValueError(f"duplicate probe name {probe!r}")
            if image.num_qubits != self.num_qubits:
                raise ValueError("action images must use the action qubit count")
            names.add(probe)

    @classmethod
    def from_labels(
        cls,
        name: str,
        num_qubits: int,
        images: Mapping[str, str],
    ) -> ExactPauliAction:
        """Construct an exact action from conventional tensor-Pauli labels."""

        return cls(
            name=name,
            num_qubits=num_qubits,
            images=tuple(
                (probe, _parse_pauli_label(label, num_qubits))
                for probe, label in images.items()
            ),
        )

    def image(self, probe: str) -> PauliWord:
        """Return the exact image of one named exported probe."""

        for candidate, image in self.images:
            if candidate == probe:
                return image
        raise KeyError(probe)


@dataclass(frozen=True)
class ExactWitnessVerification:
    """Outcome of exact version-one witness validation."""

    valid: bool
    classification_cells_verified: int
    closure_elements_verified: int
    closure_complete_verified: bool
    errors: tuple[str, ...]
    arithmetic: str = "exact binary Pauli arithmetic modulo scalar phase"


def verify_numerical_witness_exact(
    witness: Mapping[str, Any] | str,
    actions: Mapping[str, ExactPauliAction],
) -> ExactWitnessVerification:
    """Verify a version-one witness without using dense numerical results.

    The supplied exact actions are the independent trust boundary. Every
    exported classification is checked against them. Provenance is checked
    against exact action-table coordinates, and a claimed complete closure is
    independently regenerated in the finite projective Pauli group.
    """

    errors: list[str] = []
    cells_verified = 0
    closure_elements_verified = 0
    closure_complete_verified = False
    if isinstance(witness, str):
        try:
            data = json.loads(witness)
        except json.JSONDecodeError as error:
            return ExactWitnessVerification(False, 0, 0, False, (str(error),))
    else:
        data = witness
    if not isinstance(data, Mapping):
        return ExactWitnessVerification(False, 0, 0, False, ("witness must be an object",))

    if data.get("schema") != WITNESS_SCHEMA:
        errors.append(f"schema must equal {WITNESS_SCHEMA!r}")
    num_qubits = data.get("num_qubits")
    if not isinstance(num_qubits, int) or isinstance(num_qubits, bool) or num_qubits < 1:
        errors.append("num_qubits must be a positive integer")
        return ExactWitnessVerification(False, 0, 0, False, tuple(errors))
    level = data.get("level")
    if not isinstance(level, int) or isinstance(level, bool) or level < 1:
        errors.append("level must be a positive integer")
    projective_config = data.get("projective_config")
    if not isinstance(projective_config, Mapping):
        errors.append("projective_config must be an object")
    else:
        atol = projective_config.get("atol")
        decimals = projective_config.get("decimals")
        if (
            not isinstance(atol, (int, float))
            or isinstance(atol, bool)
            or not math.isfinite(atol)
            or atol <= 0
        ):
            errors.append("projective_config.atol must be positive and finite")
        if not isinstance(decimals, int) or isinstance(decimals, bool) or decimals < 0:
            errors.append("projective_config.decimals must be a nonnegative integer")
    search = data.get("search")
    if not isinstance(search, Mapping):
        errors.append("search must be an object")
    else:
        for field in ("products_tested", "max_word_length"):
            value = search.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"search.{field} must be a nonnegative integer")
        limits = search.get("limits")
        if not isinstance(limits, Mapping):
            errors.append("search.limits must be an object")
        else:
            for field in ("max_elements", "max_products"):
                value = limits.get(field)
                if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                    errors.append(f"search.limits.{field} must be a positive integer")
    for name, action in actions.items():
        if name != action.name:
            errors.append(f"action mapping key {name!r} does not match its action name")
        if action.num_qubits != num_qubits:
            errors.append(f"action {name!r} uses the wrong qubit count")

    classification = data.get("classification")
    rows = classification.get("rows") if isinstance(classification, Mapping) else None
    if not isinstance(rows, list):
        errors.append("classification.rows must be a list")
        rows = []
    if isinstance(classification, Mapping) and classification.get("kind") != "tensor_pauli":
        errors.append("classification.kind must be 'tensor_pauli'")

    cell_values: dict[tuple[int, int], PauliWord] = {}
    cell_names: dict[tuple[int, int], tuple[str, str]] = {}
    seen_conjugators: set[str] = set()
    for row_index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"classification row {row_index} must be an object")
            continue
        conjugator = row.get("conjugator")
        images = row.get("images")
        if not isinstance(conjugator, str) or not conjugator:
            errors.append(f"classification row {row_index} has an invalid conjugator")
            continue
        if conjugator in seen_conjugators:
            errors.append(f"classification repeats conjugator {conjugator!r}")
        seen_conjugators.add(conjugator)
        action = actions.get(conjugator)
        if action is None:
            errors.append(f"no exact action supplied for conjugator {conjugator!r}")
        if not isinstance(images, list):
            errors.append(f"classification row {row_index}.images must be a list")
            continue
        for column_index, image_entry in enumerate(images):
            if not isinstance(image_entry, Mapping):
                errors.append(
                    f"classification cell ({row_index}, {column_index}) must be an object"
                )
                continue
            probe = image_entry.get("probe")
            label = image_entry.get("pauli")
            if not isinstance(probe, str) or not isinstance(label, str):
                errors.append(
                    f"classification cell ({row_index}, {column_index}) needs string labels"
                )
                continue
            try:
                claimed = _parse_pauli_label(label, num_qubits)
            except ValueError as error:
                errors.append(f"classification cell ({row_index}, {column_index}): {error}")
                continue
            cell_names[(row_index, column_index)] = (conjugator, probe)
            if action is None:
                continue
            try:
                expected = action.image(probe)
            except KeyError:
                errors.append(f"exact action {conjugator!r} has no probe {probe!r}")
                continue
            if claimed != expected:
                errors.append(
                    f"classification cell ({row_index}, {column_index}) claims {label!r}; "
                    f"exact action gives {expected.label!r}"
                )
                continue
            cell_values[(row_index, column_index)] = expected
            cells_verified += 1

    total_cells = sum(
        len(row.get("images", []))
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("images"), list)
    )
    if isinstance(classification, Mapping):
        expected_summary = {
            "recognized": total_cells,
            "total": total_cells,
            "all_recognized": True,
        }
        for key, expected in expected_summary.items():
            if classification.get(key) != expected:
                errors.append(f"classification.{key} must equal {expected!r} in the exact domain")

    generator_values: dict[str, PauliWord] = {}
    defining_generators = data.get("defining_generators")
    if not isinstance(defining_generators, list):
        errors.append("defining_generators must be a list")
        defining_generators = []
    for generator_index, generator in enumerate(defining_generators):
        if not isinstance(generator, Mapping):
            errors.append(f"defining generator {generator_index} must be an object")
            continue
        name = generator.get("name")
        sources = generator.get("sources")
        if not isinstance(name, str) or not name:
            errors.append(f"defining generator {generator_index} has an invalid name")
            continue
        if name in generator_values:
            errors.append(f"duplicate defining generator name {name!r}")
        if not isinstance(sources, list) or not sources:
            errors.append(f"defining generator {name!r} must have sources")
            continue
        values: list[PauliWord] = []
        for source in sources:
            if not isinstance(source, Mapping):
                errors.append(f"defining generator {name!r} has a non-object source")
                continue
            row_index = source.get("row")
            column_index = source.get("column")
            coordinate = (row_index, column_index)
            if not isinstance(row_index, int) or not isinstance(column_index, int):
                errors.append(f"defining generator {name!r} has invalid source coordinates")
                continue
            expected_names = cell_names.get(coordinate)
            value = cell_values.get(coordinate)
            if expected_names is None or value is None:
                errors.append(f"defining generator {name!r} references missing cell {coordinate}")
                continue
            if (source.get("conjugator"), source.get("probe")) != expected_names:
                errors.append(f"defining generator {name!r} has inconsistent source names")
            values.append(value)
        if values and any(value != values[0] for value in values[1:]):
            errors.append(f"defining generator {name!r} combines unequal exact Pauli sources")
        elif values:
            generator_values[name] = values[0]

    closure = data.get("closure")
    completeness = data.get("completeness")
    words = closure.get("generator_words") if isinstance(closure, Mapping) else None
    evaluated: list[PauliWord] = []
    if not isinstance(words, list):
        errors.append("closure.generator_words must be a list")
        words = []
    for word_index, word in enumerate(words):
        if not isinstance(word, list) or not all(isinstance(name, str) for name in word):
            errors.append(f"closure word {word_index} must be a list of strings")
            continue
        value = PauliWord(num_qubits, 0, 0)
        for name in word:
            generator = generator_values.get(name)
            if generator is None:
                errors.append(f"closure word {word_index} uses unknown generator {name!r}")
                break
            value = _multiply_paulis(value, generator)
        else:
            evaluated.append(value)
    closure_elements_verified = len(evaluated)
    if len(set(evaluated)) != len(evaluated):
        errors.append("closure.generator_words contains duplicate exact Pauli elements")
    if isinstance(closure, Mapping):
        if closure.get("discovered_elements") != len(words):
            errors.append("closure.discovered_elements does not match generator_words")
    else:
        errors.append("closure must be an object")

    closure_complete = (
        isinstance(completeness, Mapping) and completeness.get("closure_complete") is True
    )
    if not isinstance(completeness, Mapping):
        errors.append("completeness must be an object")
    else:
        source_complete = completeness.get("source_complete")
        stop_reason = completeness.get("stop_reason")
        if not isinstance(source_complete, bool):
            errors.append("completeness.source_complete must be Boolean")
        if stop_reason not in {"complete", "max_elements", "max_products"}:
            errors.append("completeness.stop_reason is invalid")
        if completeness.get("complete") is not (source_complete is True and closure_complete):
            errors.append("completeness.complete must combine source and closure completeness")
        if closure_complete and stop_reason != "complete":
            errors.append("a complete closure must use stop_reason='complete'")

    if closure_complete and generator_values and len(evaluated) == len(words):
        discovered = set(evaluated)
        frontier = {PauliWord(num_qubits, 0, 0)}
        exact_closure = set(frontier)
        while frontier:
            next_frontier: set[PauliWord] = set()
            for element in frontier:
                for generator in generator_values.values():
                    product = _multiply_paulis(element, generator)
                    if product not in exact_closure:
                        exact_closure.add(product)
                        next_frontier.add(product)
            frontier = next_frontier
        if discovered != exact_closure:
            errors.append("claimed complete closure does not equal the exact generated Pauli group")
        elif isinstance(closure, Mapping) and closure.get("order") != len(exact_closure):
            errors.append("closure.order does not equal the exact generated group order")
        else:
            closure_complete_verified = True
    elif isinstance(closure, Mapping) and closure.get("order") is not None:
        errors.append("incomplete closure must not claim an order")

    return ExactWitnessVerification(
        valid=not errors,
        classification_cells_verified=cells_verified,
        closure_elements_verified=closure_elements_verified,
        closure_complete_verified=closure_complete_verified,
        errors=tuple(errors),
    )
