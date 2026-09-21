"""Conjugation actions on named generating sets.

These representations expose generator images without attempting group
closure.  Their cost is linear in the number of table cells, which makes them a
useful inspection step before an iterative group search.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import TypeAlias, overload

import numpy as np

from .operators import Gate, GateSet, ProjectiveKey, projective_key, projectively_equal
from .paulis import PauliWord, recognize_pauli_word

GeneratorReference: TypeAlias = str | int


@dataclass(frozen=True)
class GeneratorSource:
    """One action-table coordinate that produced a defining generator."""

    row_index: int
    column_index: int
    conjugator: str
    probe: str

    def __post_init__(self) -> None:
        if self.row_index < 0 or self.column_index < 0:
            raise ValueError("source indices must be nonnegative")
        if not self.conjugator or not self.probe:
            raise ValueError("source names must be nonempty")

    @property
    def label(self) -> str:
        """Stable human-readable description of the source action."""

        return f"{self.conjugator} conjugates {self.probe}"


@dataclass(frozen=True)
class StreamedConjugationGenerators:
    """Projectively unique action images collected without retaining a table.

    Every dense cell is constructed once and immediately deduplicated. Only a
    representative of each projective image and its lightweight provenance are
    retained.
    """

    conjugators: GateSet
    probe_generators: GateSet
    unique_images: GateSet
    unique_image_sources: tuple[tuple[GeneratorSource, ...], ...]
    source_complete: bool
    cells_processed: int

    def __post_init__(self) -> None:
        if not isinstance(self.source_complete, bool):
            raise TypeError("source_complete must be a bool")
        expected_cells = len(self.conjugators) * len(self.probe_generators)
        if self.cells_processed != expected_cells:
            raise ValueError("cells_processed must match the source dimensions")
        if len(self.unique_images) != len(self.unique_image_sources):
            raise ValueError("every unique image must have a provenance entry")
        if any(not sources for sources in self.unique_image_sources):
            raise ValueError("unique-image provenance must not be empty")

    @property
    def shape(self) -> tuple[int, int]:
        """Return the logical action-table shape without retaining its cells."""

        return len(self.conjugators), len(self.probe_generators)


def conjugate(conjugator: Gate, target: Gate, *, name: str | None = None) -> Gate:
    """Return ``conjugator @ target @ conjugator†``."""

    if conjugator.dimension != target.dimension:
        raise ValueError("conjugator and target must have the same dimension")
    label = name or f"{conjugator.name} {target.name} {conjugator.name}†"
    return Gate(
        label,
        conjugator.matrix @ target.matrix @ conjugator.matrix.conj().T,
        validation_atol=max(conjugator.validation_atol, target.validation_atol),
    )


@dataclass(frozen=True)
class ConjugationAction:
    r"""Images of named generators under :math:`P\mapsto UPU^\dagger`."""

    conjugator: Gate
    domain_generators: GateSet
    images: tuple[Gate, ...]

    def __post_init__(self) -> None:
        if self.conjugator.dimension != self.domain_generators.dimension:
            raise ValueError("conjugator and domain generators must have the same dimension")
        if len(self.images) != len(self.domain_generators):
            raise ValueError("there must be exactly one image per domain generator")
        for generator, image in zip(self.domain_generators, self.images, strict=True):
            if image.dimension != self.conjugator.dimension:
                raise ValueError("action images must have the same dimension as the conjugator")
            expected = (
                self.conjugator.matrix
                @ generator.matrix
                @ self.conjugator.matrix.conj().T
            )
            if not projectively_equal(
                image.matrix,
                expected,
                self.domain_generators.projective_config,
            ):
                raise ValueError(f"image for {generator.name!r} is not its conjugate")

    def image(self, generator: GeneratorReference) -> Gate:
        """Return an image by zero-based index or generator name."""

        return self.images[self._generator_index(generator)]

    def as_dict(self) -> dict[str, Gate]:
        """Return a new name-to-image dictionary in generator order."""

        return {
            generator.name: image
            for generator, image in zip(self.domain_generators, self.images, strict=True)
        }

    def apply_word(self, word: Iterable[GeneratorReference], *, name: str | None = None) -> Gate:
        r"""Apply the action to a product of domain generators.

        For ``word=["X", "Z"]``, multiplication order is ``X @ Z`` and the
        returned matrix is ``image("X") @ image("Z")``.  This uses the
        homomorphism property of conjugation and does not enumerate either the
        domain group or the image group.
        """

        if isinstance(word, (str, bytes)):
            raise TypeError("word must be an iterable of names or indices, not a string")
        references = tuple(word)
        matrix = np.eye(self.conjugator.dimension, dtype=np.complex128)
        labels: list[str] = []
        for reference in references:
            index = self._generator_index(reference)
            matrix = matrix @ self.images[index].matrix
            labels.append(self.domain_generators[index].name)
        label = name or (
            f"{self.conjugator.name}({' '.join(labels) or 'I'}){self.conjugator.name}†"
        )
        validation_atol = max(
            self.conjugator.validation_atol,
            *(generator.validation_atol for generator in self.domain_generators),
        )
        return Gate(label, matrix, validation_atol=validation_atol)

    def _generator_index(self, generator: GeneratorReference) -> int:
        if isinstance(generator, bool):
            raise TypeError("generator reference must be a name or integer index")
        if isinstance(generator, int):
            if 0 <= generator < len(self.domain_generators):
                return generator
            raise IndexError(f"generator index {generator} is out of range")
        if isinstance(generator, str):
            for index, candidate in enumerate(self.domain_generators):
                if candidate.name == generator:
                    return index
            raise KeyError(f"unknown generator name {generator!r}")
        raise TypeError("generator reference must be a name or integer index")


class ConjugationActionTable(Sequence[ConjugationAction]):
    """Rows of conjugation actions for a finite set of conjugators.

    ``source_complete`` says whether the rows exhaust the intended source set.
    It does not affect table construction: every supplied cell is always
    computed.  The flag is metadata for callers using a truncated prior group.
    """

    def __init__(
        self,
        conjugators: GateSet,
        probe_generators: GateSet,
        actions: Iterable[ConjugationAction],
        *,
        source_complete: bool = True,
    ) -> None:
        if not isinstance(source_complete, bool):
            raise TypeError("source_complete must be a bool")
        if conjugators.dimension != probe_generators.dimension:
            raise ValueError("conjugators and probes must have the same dimension")
        if conjugators.projective_config != probe_generators.projective_config:
            raise ValueError("conjugators and probes must use the same projective settings")
        rows = tuple(actions)
        if len(rows) != len(conjugators):
            raise ValueError("there must be exactly one action row per conjugator")
        for conjugator, action in zip(conjugators, rows, strict=True):
            if not isinstance(action, ConjugationAction):
                raise TypeError("action rows must be ConjugationAction instances")
            if action.conjugator.name != conjugator.name or not projectively_equal(
                action.conjugator.matrix,
                conjugator.matrix,
                probe_generators.projective_config,
            ):
                raise ValueError("action rows must follow conjugator order")
            if (
                action.domain_generators.projective_config
                != probe_generators.projective_config
            ):
                raise ValueError("action rows and table must use the same projective settings")
            if _gate_set_signature(action.domain_generators) != _gate_set_signature(
                probe_generators
            ):
                raise ValueError("every action row must use the table's probe generators")

        self._conjugators = conjugators
        self._probe_generators = probe_generators
        self._actions = rows
        self._source_complete = source_complete
        self._unique_images = GateSet(
            (image for action in rows for image in action.images),
            projective_config=probe_generators.projective_config,
        )
        sources_by_key = {
            key: [] for key in self._unique_images.projective_keys
        }
        for row_index, action in enumerate(rows):
            for column_index, (probe, image) in enumerate(
                zip(probe_generators, action.images, strict=True)
            ):
                key = projective_key(image.matrix, probe_generators.projective_config)
                sources_by_key[key].append(
                    GeneratorSource(
                        row_index=row_index,
                        column_index=column_index,
                        conjugator=action.conjugator.name,
                        probe=probe.name,
                    )
                )
        self._unique_image_sources = tuple(
            tuple(sources_by_key[key]) for key in self._unique_images.projective_keys
        )

    @overload
    def __getitem__(self, index: int) -> ConjugationAction: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[ConjugationAction, ...]: ...

    def __getitem__(
        self, index: int | slice
    ) -> ConjugationAction | tuple[ConjugationAction, ...]:
        return self._actions[index]

    def __iter__(self) -> Iterator[ConjugationAction]:
        return iter(self._actions)

    def __len__(self) -> int:
        return len(self._actions)

    @property
    def conjugators(self) -> GateSet:
        """Conjugators represented by the table rows."""

        return self._conjugators

    @property
    def probe_generators(self) -> GateSet:
        """Domain generators represented by the table columns."""

        return self._probe_generators

    @property
    def shape(self) -> tuple[int, int]:
        """Return ``(number of conjugators, number of probes)``."""

        return len(self.conjugators), len(self.probe_generators)

    @property
    def source_complete(self) -> bool:
        """Whether the table rows exhaust the intended conjugator source."""

        return self._source_complete

    @property
    def unique_images(self) -> GateSet:
        """All table cells, deduplicated modulo global phase."""

        return self._unique_images

    @property
    def unique_image_sources(self) -> tuple[tuple[GeneratorSource, ...], ...]:
        """Every source coordinate for each projectively unique image.

        The outer tuple follows ``unique_images`` order. Each inner tuple is in
        stable row-major action-table order and is nonempty.
        """

        return self._unique_image_sources

    def row(self, conjugator: GeneratorReference) -> ConjugationAction:
        """Return an action row by zero-based index or conjugator name."""

        return self._actions[_named_index(self.conjugators, conjugator, "conjugator")]

    def image(
        self,
        conjugator: GeneratorReference,
        probe: GeneratorReference,
    ) -> Gate:
        """Return one table cell by row and column references."""

        return self.row(conjugator).image(probe)

    def classify(self, reference_gates: GateSet) -> ActionImageClassification:
        """Recognize every image against a named projective reference set."""

        return classify_action_images(self, reference_gates)

    def classify_paulis(self) -> PauliActionClassification:
        """Recognize every image directly as a projective tensor Pauli.

        Unlike classification against ``projective_pauli_group(n)``, this does
        not construct a dense catalog with ``4**n`` entries.
        """

        return classify_pauli_images(self)


@dataclass(frozen=True)
class ActionImageClassification:
    """Projective reference matches for every cell of an action table."""

    action_table: ConjugationActionTable
    reference_gates: GateSet
    matches: tuple[tuple[Gate | None, ...], ...]

    def __post_init__(self) -> None:
        if len(self.matches) != self.action_table.shape[0] or any(
            len(row) != self.action_table.shape[1] for row in self.matches
        ):
            raise ValueError("classification shape must match the action table")

    @property
    def recognized_count(self) -> int:
        """Number of table cells matched to the reference set."""

        return sum(match is not None for row in self.matches for match in row)

    @property
    def total_count(self) -> int:
        """Number of table cells classified."""

        rows, columns = self.action_table.shape
        return rows * columns

    @property
    def coverage(self) -> float:
        """Fraction of cells matched to the reference set."""

        return self.recognized_count / self.total_count

    @property
    def all_recognized(self) -> bool:
        """Whether every action image has a known projective label."""

        return self.recognized_count == self.total_count

    @property
    def unrecognized(self) -> tuple[tuple[str, str], ...]:
        """Return ``(conjugator, probe)`` coordinates without a match."""

        return tuple(
            (conjugator.name, probe.name)
            for row, conjugator in zip(
                self.matches,
                self.action_table.conjugators,
                strict=True,
            )
            for match, probe in zip(
                row,
                self.action_table.probe_generators,
                strict=True,
            )
            if match is None
        )

    def match(
        self,
        conjugator: GeneratorReference,
        probe: GeneratorReference,
    ) -> Gate | None:
        """Return the matched reference gate at one table coordinate."""

        row = _named_index(self.action_table.conjugators, conjugator, "conjugator")
        column = _named_index(self.action_table.probe_generators, probe, "probe")
        return self.matches[row][column]

    def label(
        self,
        conjugator: GeneratorReference,
        probe: GeneratorReference,
        *,
        unknown: str | None = None,
    ) -> str | None:
        """Return the matched gate name, or ``unknown`` when unmatched."""

        match = self.match(conjugator, probe)
        return unknown if match is None else match.name

    def as_rows(self, *, unknown: str | None = None) -> tuple[tuple[str | None, ...], ...]:
        """Return a rectangular table of algebraic labels."""

        return tuple(
            tuple(unknown if match is None else match.name for match in row)
            for row in self.matches
        )


@dataclass(frozen=True)
class PauliActionClassification:
    """Direct tensor-Pauli recognition for every cell of an action table."""

    action_table: ConjugationActionTable
    matches: tuple[tuple[PauliWord | None, ...], ...]

    def __post_init__(self) -> None:
        if len(self.matches) != self.action_table.shape[0] or any(
            len(row) != self.action_table.shape[1] for row in self.matches
        ):
            raise ValueError("classification shape must match the action table")

    @property
    def recognized_count(self) -> int:
        """Number of table cells recognized as projective tensor Paulis."""

        return sum(match is not None for row in self.matches for match in row)

    @property
    def total_count(self) -> int:
        """Number of table cells classified."""

        rows, columns = self.action_table.shape
        return rows * columns

    @property
    def coverage(self) -> float:
        """Fraction of cells recognized as projective tensor Paulis."""

        return self.recognized_count / self.total_count

    @property
    def all_recognized(self) -> bool:
        """Whether every action image is a projective tensor Pauli."""

        return self.recognized_count == self.total_count

    @property
    def preserves_paulis(self) -> bool:
        """Whether the supplied Pauli-generator table maps entirely to Paulis.

        When the table columns are a complete generating set for the Pauli
        group, this is the standard normalizer test for each table row's
        conjugator to be Clifford (up to global phase).
        """

        return self.all_recognized

    def row_preserves_paulis(self, conjugator: GeneratorReference) -> bool:
        """Whether every probe image in one conjugator row is a Pauli."""

        row = _named_index(self.action_table.conjugators, conjugator, "conjugator")
        return all(match is not None for match in self.matches[row])

    @property
    def unrecognized(self) -> tuple[tuple[str, str], ...]:
        """Return ``(conjugator, probe)`` coordinates that are not Paulis."""

        return tuple(
            (conjugator.name, probe.name)
            for row, conjugator in zip(
                self.matches,
                self.action_table.conjugators,
                strict=True,
            )
            for match, probe in zip(
                row,
                self.action_table.probe_generators,
                strict=True,
            )
            if match is None
        )

    def match(
        self,
        conjugator: GeneratorReference,
        probe: GeneratorReference,
    ) -> PauliWord | None:
        """Return the recognized Pauli word at one table coordinate."""

        row = _named_index(self.action_table.conjugators, conjugator, "conjugator")
        column = _named_index(self.action_table.probe_generators, probe, "probe")
        return self.matches[row][column]

    def label(
        self,
        conjugator: GeneratorReference,
        probe: GeneratorReference,
        *,
        unknown: str | None = None,
    ) -> str | None:
        """Return a conventional Pauli label, or ``unknown`` when unmatched."""

        match = self.match(conjugator, probe)
        return unknown if match is None else match.label

    def as_rows(self, *, unknown: str | None = None) -> tuple[tuple[str | None, ...], ...]:
        """Return a rectangular table of conventional Pauli labels."""

        return tuple(
            tuple(unknown if match is None else match.label for match in row)
            for row in self.matches
        )

    def symplectic_matrix(self, conjugator: GeneratorReference) -> np.ndarray:
        """Return the induced binary symplectic matrix for one table row.

        Columns and coordinates use the order ``X_0,...,X_(n-1),Z_0,...,Z_(n-1)``.
        The table probes must be those standard Pauli generators in that order,
        and every image in the selected row must be recognized as a Pauli.
        """

        num_qubits = self.action_table.probe_generators.num_qubits
        expected_count = 2 * num_qubits
        if len(self.action_table.probe_generators) != expected_count:
            raise ValueError("symplectic action requires all 2n standard Pauli generators")

        # Import locally so the lightweight standard-gate constructors remain
        # independent of action-table definitions.
        from .standard_gates import pauli_generators

        probes = self.action_table.probe_generators
        expected = pauli_generators(
            num_qubits,
            projective_config=probes.projective_config,
        )
        if probes.projective_keys != expected.projective_keys:
            raise ValueError(
                "symplectic action requires standard Pauli generators in X-then-Z order"
            )

        row = _named_index(self.action_table.conjugators, conjugator, "conjugator")
        words = self.matches[row]
        if any(word is None for word in words):
            raise ValueError("the selected conjugator does not map every probe to a Pauli")

        matrix = np.zeros((expected_count, expected_count), dtype=np.uint8)
        for column, word in enumerate(words):
            assert word is not None
            for qubit in range(num_qubits):
                bit = 1 << (num_qubits - 1 - qubit)
                matrix[qubit, column] = bool(word.x_mask & bit)
                matrix[num_qubits + qubit, column] = bool(word.z_mask & bit)

        identity = np.eye(num_qubits, dtype=np.uint8)
        zero = np.zeros_like(identity)
        form = np.block([[zero, identity], [identity, zero]])
        if not np.array_equal((matrix.T @ form @ matrix) % 2, form):
            raise ValueError("recognized images do not preserve the binary symplectic form")
        matrix.flags.writeable = False
        return matrix


def conjugation_action(conjugator: Gate, probe_generators: GateSet) -> ConjugationAction:
    r"""Compute :math:`P\mapsto UPU^\dagger` on the supplied generators only."""

    if conjugator.dimension != probe_generators.dimension:
        raise ValueError("conjugator and probes must have the same dimension")
    return ConjugationAction(
        conjugator=conjugator,
        domain_generators=probe_generators,
        images=tuple(conjugate(conjugator, probe) for probe in probe_generators),
    )


def conjugation_action_table(
    conjugators: Gate | GateSet,
    probe_generators: GateSet,
    *,
    source_complete: bool = True,
) -> ConjugationActionTable:
    """Compute an action table without closing the generated image group."""

    conjugator_set = _coerce_conjugators(conjugators, probe_generators)
    return ConjugationActionTable(
        conjugator_set,
        probe_generators,
        (conjugation_action(conjugator, probe_generators) for conjugator in conjugator_set),
        source_complete=source_complete,
    )


def stream_conjugation_generators(
    conjugators: Gate | GateSet,
    probe_generators: GateSet,
    *,
    source_complete: bool = True,
) -> StreamedConjugationGenerators:
    """Deduplicate conjugated probes while retaining no dense action table.

    This computes the same row-major cells and provenance as
    :func:`conjugation_action_table`, but duplicate dense images become
    unreachable as soon as their projective key and source record are saved.
    """

    if not isinstance(source_complete, bool):
        raise TypeError("source_complete must be a bool")
    conjugator_set = _coerce_conjugators(conjugators, probe_generators)
    config = probe_generators.projective_config
    unique_images: list[Gate] = []
    sources_by_key: dict[ProjectiveKey, list[GeneratorSource]] = {}
    key_order: list[ProjectiveKey] = []
    cells_processed = 0
    for row_index, conjugator in enumerate(conjugator_set):
        for column_index, probe in enumerate(probe_generators):
            image = conjugate(conjugator, probe)
            key = projective_key(image.matrix, config)
            if key not in sources_by_key:
                unique_images.append(image)
                sources_by_key[key] = []
                key_order.append(key)
            sources_by_key[key].append(
                GeneratorSource(
                    row_index=row_index,
                    column_index=column_index,
                    conjugator=conjugator.name,
                    probe=probe.name,
                )
            )
            cells_processed += 1

    retained = GateSet(unique_images, projective_config=config)
    if retained.projective_keys != tuple(key_order):
        raise AssertionError("streamed projective keys changed during retention")
    return StreamedConjugationGenerators(
        conjugators=conjugator_set,
        probe_generators=probe_generators,
        unique_images=retained,
        unique_image_sources=tuple(tuple(sources_by_key[key]) for key in key_order),
        source_complete=source_complete,
        cells_processed=cells_processed,
    )


def classify_action_images(
    action_table: ConjugationActionTable,
    reference_gates: GateSet,
) -> ActionImageClassification:
    """Match table images to named references modulo global phase."""

    if action_table.probe_generators.dimension != reference_gates.dimension:
        raise ValueError("action images and references must have the same dimension")
    matches = tuple(
        tuple(reference_gates.match_matrix(image.matrix) for image in action.images)
        for action in action_table
    )
    return ActionImageClassification(action_table, reference_gates, matches)


def classify_pauli_images(
    action_table: ConjugationActionTable,
) -> PauliActionClassification:
    """Recognize table images as tensor Paulis without building a catalog."""

    config = action_table.probe_generators.projective_config
    matches = tuple(
        tuple(recognize_pauli_word(image.matrix, config) for image in action.images)
        for action in action_table
    )
    return PauliActionClassification(action_table, matches)


def _coerce_conjugators(conjugators: Gate | GateSet, probes: GateSet) -> GateSet:
    if isinstance(conjugators, Gate):
        return GateSet([conjugators], projective_config=probes.projective_config)
    if not isinstance(conjugators, GateSet):
        raise TypeError("conjugators must be a Gate or GateSet")
    if conjugators.dimension != probes.dimension:
        raise ValueError("conjugators and probes must have the same dimension")
    if conjugators.projective_config != probes.projective_config:
        raise ValueError("conjugators and probes must use the same projective settings")
    return conjugators


def _named_index(gates: GateSet, reference: GeneratorReference, kind: str) -> int:
    if isinstance(reference, bool):
        raise TypeError(f"{kind} reference must be a name or integer index")
    if isinstance(reference, int):
        if 0 <= reference < len(gates):
            return reference
        raise IndexError(f"{kind} index {reference} is out of range")
    if isinstance(reference, str):
        for index, gate in enumerate(gates):
            if gate.name == reference:
                return index
        raise KeyError(f"unknown {kind} name {reference!r}")
    raise TypeError(f"{kind} reference must be a name or integer index")


def _gate_set_signature(gates: GateSet) -> tuple[tuple[str, object], ...]:
    return tuple(
        (gate.name, key)
        for gate, key in zip(gates, gates.projective_keys, strict=True)
    )
