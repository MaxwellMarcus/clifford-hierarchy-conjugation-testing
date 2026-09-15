"""Dense quantum operators and projective comparison utilities.

The abstractions in this module are intentionally small.  They are designed for
exactly the kind of low-qubit, dense-matrix experiments in this repository, not
for simulating large circuits.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import TypeAlias, overload

import numpy as np
from numpy.typing import ArrayLike, NDArray

ComplexMatrix: TypeAlias = NDArray[np.complex128]
ProjectiveKey: TypeAlias = tuple[tuple[int, int], bytes, bytes]


@dataclass(frozen=True)
class ProjectiveConfig:
    """Numerical settings for equality modulo a scalar phase.

    ``atol`` decides which entries are treated as zero.  After fixing the phase
    of the first nonzero entry, real and imaginary parts are rounded to
    ``decimals`` places to obtain a stable hash key.  This is a numerical
    heuristic: proof-critical results should be reproduced in exact arithmetic.
    """

    atol: float = 1e-9
    decimals: int = 10

    def __post_init__(self) -> None:
        if not np.isfinite(self.atol) or self.atol <= 0:
            raise ValueError("atol must be a positive finite number")
        if self.decimals < 0:
            raise ValueError("decimals must be nonnegative")


DEFAULT_PROJECTIVE_CONFIG = ProjectiveConfig()


def canonicalize_projective(
    matrix: ArrayLike,
    config: ProjectiveConfig = DEFAULT_PROJECTIVE_CONFIG,
) -> ComplexMatrix:
    """Return a copy with global phase fixed and numerical noise rounded away.

    The phase is chosen so that the first entry larger than ``config.atol`` is
    positive real.  The zero matrix has no projective representative and is
    rejected.
    """

    array = _as_square_matrix(matrix)
    flattened = array.ravel()
    nonzero = np.flatnonzero(np.abs(flattened) > config.atol)
    if not len(nonzero):
        raise ValueError("the zero matrix has no projective representative")

    pivot = flattened[nonzero[0]]
    normalized = np.array(array / (pivot / abs(pivot)), dtype=np.complex128)
    real = normalized.real
    imaginary = normalized.imag
    real[np.abs(real) <= config.atol] = 0.0
    imaginary[np.abs(imaginary) <= config.atol] = 0.0
    normalized = np.round(real, config.decimals) + 1j * np.round(
        imaginary, config.decimals
    )
    # Rounding can create IEEE negative zero, whose bytes differ from positive
    # zero even though the values compare equal. Canonical keys must erase it.
    normalized.real[normalized.real == 0] = 0.0
    normalized.imag[normalized.imag == 0] = 0.0
    return np.asarray(normalized, dtype=np.complex128)


def projective_key(
    matrix: ArrayLike,
    config: ProjectiveConfig = DEFAULT_PROJECTIVE_CONFIG,
) -> ProjectiveKey:
    """Return a hashable numerical key for a matrix modulo global phase."""

    normalized = canonicalize_projective(matrix, config)
    # Force a platform-independent representation for reproducible keys.
    real = np.ascontiguousarray(normalized.real, dtype="<f8")
    imaginary = np.ascontiguousarray(normalized.imag, dtype="<f8")
    return normalized.shape, real.tobytes(), imaginary.tobytes()


def projectively_equal(
    left: ArrayLike,
    right: ArrayLike,
    config: ProjectiveConfig = DEFAULT_PROJECTIVE_CONFIG,
) -> bool:
    """Return whether two matrices have the same numerical projective key."""

    left_array = _as_square_matrix(left)
    right_array = _as_square_matrix(right)
    return left_array.shape == right_array.shape and projective_key(
        left_array, config
    ) == projective_key(right_array, config)


@dataclass(frozen=True, eq=False)
class Gate:
    """A named, immutable, dense unitary operator on one or more qubits."""

    name: str
    matrix: ComplexMatrix
    validation_atol: float = 1e-9

    def __init__(
        self,
        name: str,
        matrix: ArrayLike,
        *,
        validation_atol: float = 1e-9,
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("a gate name must be a nonempty string")
        if not np.isfinite(validation_atol) or validation_atol <= 0:
            raise ValueError("validation_atol must be a positive finite number")

        array = _as_square_matrix(matrix)
        dimension = array.shape[0]
        if dimension < 2 or dimension & (dimension - 1):
            raise ValueError("gate dimension must be a power of two of at least 2")
        if not np.all(np.isfinite(array)):
            raise ValueError("gate entries must be finite")
        identity = np.eye(dimension, dtype=np.complex128)
        if not np.allclose(
            array.conj().T @ array,
            identity,
            atol=validation_atol,
            rtol=0,
        ):
            raise ValueError("gate matrix must be unitary")

        immutable = np.array(array, dtype=np.complex128, copy=True)
        immutable.flags.writeable = False
        object.__setattr__(self, "name", name.strip())
        object.__setattr__(self, "matrix", immutable)
        object.__setattr__(self, "validation_atol", float(validation_atol))

    @property
    def dimension(self) -> int:
        """Hilbert-space dimension of this operator."""

        return self.matrix.shape[0]

    @property
    def num_qubits(self) -> int:
        """Number of qubits on which this operator acts."""

        return self.dimension.bit_length() - 1

    def dagger(self, *, name: str | None = None) -> Gate:
        """Return the adjoint gate."""

        return Gate(
            name or f"{self.name}†",
            self.matrix.conj().T,
            validation_atol=self.validation_atol,
        )

    def then(self, other: Gate, *, name: str | None = None) -> Gate:
        """Return ``other`` after ``self``, whose matrix is ``other @ self``."""

        _require_same_dimension(self, other)
        return Gate(
            name or f"{other.name}·{self.name}",
            other.matrix @ self.matrix,
            validation_atol=max(self.validation_atol, other.validation_atol),
        )

    @classmethod
    def identity(cls, num_qubits: int, *, name: str = "I") -> Gate:
        """Construct the identity gate on ``num_qubits`` qubits."""

        if num_qubits < 1:
            raise ValueError("num_qubits must be at least 1")
        return cls(name, np.eye(1 << num_qubits, dtype=np.complex128))


class GateSet(Sequence[Gate]):
    """An immutable finite set of same-size gates modulo global phase.

    Input order is preserved and the first representative of each projective
    equivalence class is retained.  Reusing a name for a different operator is
    rejected because it makes generated words ambiguous.
    """

    def __init__(
        self,
        gates: Iterable[Gate],
        *,
        projective_config: ProjectiveConfig = DEFAULT_PROJECTIVE_CONFIG,
    ) -> None:
        retained: list[Gate] = []
        retained_keys: list[ProjectiveKey] = []
        key_set: set[ProjectiveKey] = set()
        name_to_key: dict[str, ProjectiveKey] = {}
        dimension: int | None = None

        for gate in gates:
            if not isinstance(gate, Gate):
                raise TypeError("GateSet entries must be Gate instances")
            if dimension is None:
                dimension = gate.dimension
            elif gate.dimension != dimension:
                raise ValueError("all gates in a GateSet must have the same dimension")

            key = projective_key(gate.matrix, projective_config)
            old_key = name_to_key.get(gate.name)
            if old_key is not None and old_key != key:
                raise ValueError(f"gate name {gate.name!r} refers to different operators")
            name_to_key[gate.name] = key
            if key not in key_set:
                retained.append(gate)
                retained_keys.append(key)
                key_set.add(key)

        if dimension is None:
            raise ValueError("GateSet must contain at least one gate")

        self._gates = tuple(retained)
        self._keys = tuple(retained_keys)
        self._key_to_index = {key: index for index, key in enumerate(retained_keys)}
        self._dimension = dimension
        self._projective_config = projective_config

    @overload
    def __getitem__(self, index: int) -> Gate: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[Gate, ...]: ...

    def __getitem__(self, index: int | slice) -> Gate | tuple[Gate, ...]:
        return self._gates[index]

    def __iter__(self) -> Iterator[Gate]:
        return iter(self._gates)

    def __len__(self) -> int:
        return len(self._gates)

    def __repr__(self) -> str:
        names = ", ".join(repr(gate.name) for gate in self)
        return f"GateSet([{names}])"

    @property
    def dimension(self) -> int:
        """Common Hilbert-space dimension of the gates."""

        return self._dimension

    @property
    def num_qubits(self) -> int:
        """Number of qubits on which the gates act."""

        return self.dimension.bit_length() - 1

    @property
    def projective_config(self) -> ProjectiveConfig:
        """Settings used to eliminate projective duplicates."""

        return self._projective_config

    @property
    def projective_keys(self) -> tuple[ProjectiveKey, ...]:
        """Projective keys in iteration order."""

        return self._keys

    def contains_matrix(self, matrix: ArrayLike) -> bool:
        """Test projective membership using this set's numerical settings."""

        return self.match_matrix(matrix) is not None

    def match_matrix(self, matrix: ArrayLike) -> Gate | None:
        """Return the retained projective representative, if one exists."""

        array = _as_square_matrix(matrix)
        if array.shape != (self.dimension, self.dimension):
            return None
        try:
            key = projective_key(array, self.projective_config)
        except ValueError:
            return None
        index = self._key_to_index.get(key)
        return None if index is None else self._gates[index]


def _as_square_matrix(matrix: ArrayLike) -> ComplexMatrix:
    array = np.asarray(matrix, dtype=np.complex128)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise ValueError("matrix must be square")
    return array


def _require_same_dimension(left: Gate, right: Gate) -> None:
    if left.dimension != right.dimension:
        raise ValueError("gates must act on the same Hilbert space")
