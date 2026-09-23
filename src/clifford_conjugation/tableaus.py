"""Exact phase-free binary symplectic actions for Clifford operations."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .groups import DEFAULT_SEARCH_LIMITS, SearchLimits, StopReason
from .operators import DEFAULT_PROJECTIVE_CONFIG, Gate, ProjectiveConfig
from .paulis import PauliWord, recognize_pauli_word
from .standard_gates import pauli_generators


@dataclass(frozen=True, eq=False)
class SymplecticTableau:
    """Exact Clifford action on projective Pauli coordinates.

    The ``2n × 2n`` binary matrix acts on column vectors ordered as
    ``(x_0,...,x_(n-1),z_0,...,z_(n-1))``.  Pauli signs and Clifford global
    phases are deliberately omitted, so this represents the induced
    symplectic action rather than a full signed stabilizer tableau.
    """

    num_qubits: int
    matrix: NDArray[np.uint8]

    def __post_init__(self) -> None:
        if not isinstance(self.num_qubits, int) or isinstance(self.num_qubits, bool):
            raise TypeError("num_qubits must be an integer")
        if self.num_qubits < 1:
            raise ValueError("num_qubits must be at least 1")
        matrix = np.asarray(self.matrix, dtype=np.uint8)
        size = 2 * self.num_qubits
        if matrix.shape != (size, size):
            raise ValueError(f"matrix must have shape ({size}, {size})")
        matrix = np.array(matrix % 2, dtype=np.uint8, copy=True)
        form = _symplectic_form(self.num_qubits)
        if not np.array_equal((matrix.T @ form @ matrix) % 2, form):
            raise ValueError("matrix must preserve the binary symplectic form")
        matrix.setflags(write=False)
        object.__setattr__(self, "matrix", matrix)

    @classmethod
    def identity(cls, num_qubits: int) -> SymplecticTableau:
        """Return the identity Pauli action."""

        return cls(num_qubits, np.eye(2 * num_qubits, dtype=np.uint8))

    def apply(self, word: PauliWord) -> PauliWord:
        """Apply this Clifford action to a projective Pauli word."""

        if not isinstance(word, PauliWord):
            raise TypeError("word must be a PauliWord")
        if word.num_qubits != self.num_qubits:
            raise ValueError("Pauli word and tableau must have the same qubit count")
        vector = _word_to_vector(word)
        return _vector_to_word((self.matrix @ vector) % 2)

    def compose(self, other: SymplecticTableau) -> SymplecticTableau:
        """Return the action that applies ``other`` and then ``self``."""

        if not isinstance(other, SymplecticTableau):
            raise TypeError("other must be a SymplecticTableau")
        if self.num_qubits != other.num_qubits:
            raise ValueError("tableaus must have the same qubit count")
        return SymplecticTableau(
            self.num_qubits,
            (self.matrix @ other.matrix) % 2,
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, SymplecticTableau)
            and self.num_qubits == other.num_qubits
            and np.array_equal(self.matrix, other.matrix)
        )

    def __hash__(self) -> int:
        return hash((self.num_qubits, self.matrix.tobytes()))


@dataclass(frozen=True)
class TableauClosure:
    """Bounded exact closure of phase-free symplectic Clifford actions."""

    generator_names: tuple[str, ...]
    generators: tuple[SymplecticTableau, ...]
    elements: tuple[SymplecticTableau, ...]
    words: tuple[tuple[str, ...], ...]
    complete: bool
    stop_reason: StopReason
    products_tested: int
    max_word_length: int
    limits: SearchLimits

    def __post_init__(self) -> None:
        if len(self.generator_names) != len(self.generators):
            raise ValueError("generator names and tableaus must have equal length")
        if len(self.elements) != len(self.words):
            raise ValueError("elements and words must have equal length")
        if self.complete != (self.stop_reason is StopReason.COMPLETE):
            raise ValueError("complete and stop_reason are inconsistent")

    @property
    def order(self) -> int | None:
        """Return the proven symplectic-action order, or ``None`` if truncated."""

        return len(self.elements) if self.complete else None


def tableau_from_dense_clifford(
    gate: Gate,
    config: ProjectiveConfig = DEFAULT_PROJECTIVE_CONFIG,
) -> SymplecticTableau | None:
    """Extract a phase-free exact binary action from a dense Clifford gate.

    Dense conjugation and Pauli recognition are numerical.  Once extraction
    succeeds, the returned action and all subsequent composition are exact
    arithmetic over GF(2).  ``None`` means at least one standard Pauli
    generator did not map to a recognized tensor Pauli.
    """

    if not isinstance(gate, Gate):
        raise TypeError("gate must be a Gate")
    if not isinstance(config, ProjectiveConfig):
        raise TypeError("config must be a ProjectiveConfig")
    probes = pauli_generators(gate.num_qubits, projective_config=config)
    columns: list[NDArray[np.uint8]] = []
    for probe in probes:
        image = gate.matrix @ probe.matrix @ gate.matrix.conj().T
        word = recognize_pauli_word(image, config)
        if word is None:
            return None
        columns.append(_word_to_vector(word))
    try:
        return SymplecticTableau(gate.num_qubits, np.column_stack(columns))
    except ValueError:
        return None


def hadamard_tableau(qubit: int, num_qubits: int) -> SymplecticTableau:
    """Return the exact phase-free action of a Hadamard gate."""

    _validate_qubits(num_qubits, qubit)
    matrix = np.eye(2 * num_qubits, dtype=np.uint8)
    matrix[:, [qubit, num_qubits + qubit]] = matrix[
        :,
        [num_qubits + qubit, qubit],
    ]
    return SymplecticTableau(num_qubits, matrix)


def phase_tableau(qubit: int, num_qubits: int) -> SymplecticTableau:
    """Return the exact phase-free action of ``S = diag(1, i)``."""

    _validate_qubits(num_qubits, qubit)
    matrix = np.eye(2 * num_qubits, dtype=np.uint8)
    matrix[num_qubits + qubit, qubit] = 1
    return SymplecticTableau(num_qubits, matrix)


def cnot_tableau(control: int, target: int, num_qubits: int) -> SymplecticTableau:
    """Return the exact phase-free CNOT action."""

    _validate_qubits(num_qubits, control)
    _validate_qubits(num_qubits, target)
    if control == target:
        raise ValueError("control and target must be different qubits")
    matrix = np.eye(2 * num_qubits, dtype=np.uint8)
    matrix[target, control] = 1
    matrix[num_qubits + control, num_qubits + target] = 1
    return SymplecticTableau(num_qubits, matrix)


def generate_tableau_group(
    generators: Mapping[str, SymplecticTableau],
    *,
    limits: SearchLimits = DEFAULT_SEARCH_LIMITS,
) -> TableauClosure:
    """Close named symplectic actions exactly with deterministic BFS."""

    if not isinstance(generators, Mapping):
        raise TypeError("generators must be a mapping of names to tableaus")
    items = tuple(generators.items())
    if not items:
        raise ValueError("at least one tableau generator is required")
    if any(not isinstance(name, str) or not name for name, _ in items):
        raise ValueError("generator names must be nonempty strings")
    if any(not isinstance(tableau, SymplecticTableau) for _, tableau in items):
        raise TypeError("generator values must be SymplecticTableau instances")
    num_qubits = items[0][1].num_qubits
    if any(tableau.num_qubits != num_qubits for _, tableau in items):
        raise ValueError("all tableau generators must have the same qubit count")

    names = tuple(name for name, _ in items)
    generator_tableaus = tuple(tableau for _, tableau in items)
    identity = SymplecticTableau.identity(num_qubits)
    discovered = [identity]
    words: list[tuple[str, ...]] = [()]
    known = {identity}
    frontier: deque[int] = deque([0])
    products_tested = 0
    max_word_length = 0

    while frontier:
        index = frontier.popleft()
        element = discovered[index]
        word = words[index]
        for name, generator in items:
            if products_tested >= limits.max_products:
                return _closure_result(
                    names,
                    generator_tableaus,
                    discovered,
                    words,
                    False,
                    StopReason.MAX_PRODUCTS,
                    products_tested,
                    max_word_length,
                    limits,
                )
            candidate = element.compose(generator)
            products_tested += 1
            if candidate in known:
                continue
            if len(discovered) >= limits.max_elements:
                return _closure_result(
                    names,
                    generator_tableaus,
                    discovered,
                    words,
                    False,
                    StopReason.MAX_ELEMENTS,
                    products_tested,
                    max_word_length,
                    limits,
                )
            candidate_word = (*word, name)
            discovered.append(candidate)
            words.append(candidate_word)
            known.add(candidate)
            frontier.append(len(discovered) - 1)
            max_word_length = max(max_word_length, len(candidate_word))

    return _closure_result(
        names,
        generator_tableaus,
        discovered,
        words,
        True,
        StopReason.COMPLETE,
        products_tested,
        max_word_length,
        limits,
    )


def _closure_result(
    names: tuple[str, ...],
    generators: tuple[SymplecticTableau, ...],
    elements: list[SymplecticTableau],
    words: list[tuple[str, ...]],
    complete: bool,
    stop_reason: StopReason,
    products_tested: int,
    max_word_length: int,
    limits: SearchLimits,
) -> TableauClosure:
    return TableauClosure(
        generator_names=names,
        generators=generators,
        elements=tuple(elements),
        words=tuple(words),
        complete=complete,
        stop_reason=stop_reason,
        products_tested=products_tested,
        max_word_length=max_word_length,
        limits=limits,
    )


def _symplectic_form(num_qubits: int) -> NDArray[np.uint8]:
    identity = np.eye(num_qubits, dtype=np.uint8)
    zeros = np.zeros_like(identity)
    return np.block([[zeros, identity], [identity, zeros]])


def _word_to_vector(word: PauliWord) -> NDArray[np.uint8]:
    num_qubits = word.num_qubits
    vector = np.zeros(2 * num_qubits, dtype=np.uint8)
    for qubit in range(num_qubits):
        bit = 1 << (num_qubits - 1 - qubit)
        vector[qubit] = bool(word.x_mask & bit)
        vector[num_qubits + qubit] = bool(word.z_mask & bit)
    return vector


def _vector_to_word(vector: ArrayLike) -> PauliWord:
    array = np.asarray(vector, dtype=np.uint8)
    if array.ndim != 1 or len(array) % 2 or len(array) < 2:
        raise ValueError("Pauli vector must have positive even length")
    num_qubits = len(array) // 2
    x_mask = 0
    z_mask = 0
    for qubit in range(num_qubits):
        bit = 1 << (num_qubits - 1 - qubit)
        if array[qubit] % 2:
            x_mask |= bit
        if array[num_qubits + qubit] % 2:
            z_mask |= bit
    return PauliWord(num_qubits, x_mask, z_mask)


def _validate_qubits(num_qubits: int, qubit: int) -> None:
    if not isinstance(num_qubits, int) or isinstance(num_qubits, bool):
        raise TypeError("num_qubits must be an integer")
    if num_qubits < 1:
        raise ValueError("num_qubits must be at least 1")
    if not isinstance(qubit, int) or isinstance(qubit, bool):
        raise TypeError("qubit indices must be integers")
    if not 0 <= qubit < num_qubits:
        raise IndexError(f"qubit {qubit} is outside a {num_qubits}-qubit system")
