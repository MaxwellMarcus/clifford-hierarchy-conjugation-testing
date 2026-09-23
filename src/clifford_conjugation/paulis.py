"""Direct recognition of projective tensor-Pauli operators."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from .operators import DEFAULT_PROJECTIVE_CONFIG, ProjectiveConfig


@dataclass(frozen=True)
class PauliWord:
    """Binary symplectic description of a projective tensor-Pauli operator.

    Bit ``num_qubits - 1 - q`` of each mask corresponds to named qubit ``q``;
    this matches the repository's qubit-zero-most-significant matrix ordering.
    A position with both X and Z bits is labeled Y, since global phase is
    intentionally discarded.
    """

    num_qubits: int
    x_mask: int
    z_mask: int

    def __post_init__(self) -> None:
        if not isinstance(self.num_qubits, int) or isinstance(self.num_qubits, bool):
            raise TypeError("num_qubits must be an integer")
        if self.num_qubits < 1:
            raise ValueError("num_qubits must be at least 1")
        limit = 1 << self.num_qubits
        for name, mask in (("x_mask", self.x_mask), ("z_mask", self.z_mask)):
            if not isinstance(mask, int) or isinstance(mask, bool):
                raise TypeError(f"{name} must be an integer")
            if not 0 <= mask < limit:
                raise ValueError(f"{name} does not fit in {self.num_qubits} qubits")

    @property
    def label(self) -> str:
        """Conventional indexed tensor-word label, with identity factors omitted."""

        factors: list[str] = []
        for qubit in range(self.num_qubits):
            bit = 1 << (self.num_qubits - 1 - qubit)
            has_x = bool(self.x_mask & bit)
            has_z = bool(self.z_mask & bit)
            if has_x or has_z:
                letter = "Y" if has_x and has_z else "X" if has_x else "Z"
                factors.append(f"{letter}_{qubit}")
        return " ".join(factors) or "I"

    def __str__(self) -> str:
        return self.label

    def multiply(self, other: PauliWord) -> PauliWord:
        """Multiply projective Pauli words, intentionally discarding phase."""

        if not isinstance(other, PauliWord):
            raise TypeError("other must be a PauliWord")
        if self.num_qubits != other.num_qubits:
            raise ValueError("Pauli words must have the same qubit count")
        return PauliWord(
            self.num_qubits,
            self.x_mask ^ other.x_mask,
            self.z_mask ^ other.z_mask,
        )

    def commutes_with(self, other: PauliWord) -> bool:
        """Return whether two Pauli representatives commute."""

        if not isinstance(other, PauliWord):
            raise TypeError("other must be a PauliWord")
        if self.num_qubits != other.num_qubits:
            raise ValueError("Pauli words must have the same qubit count")
        pairing = (self.x_mask & other.z_mask).bit_count()
        pairing += (self.z_mask & other.x_mask).bit_count()
        return pairing % 2 == 0


def recognize_pauli_word(
    matrix: ArrayLike,
    config: ProjectiveConfig = DEFAULT_PROJECTIVE_CONFIG,
) -> PauliWord | None:
    """Recognize a dense unitary as a tensor Pauli modulo global phase.

    A tensor Pauli has one nonzero entry per computational-basis column.  Its
    row displacement is a constant XOR mask and its relative signs are a linear
    parity function.  Exploiting this structure avoids constructing or scanning
    a ``4**n`` reference catalog.  Small entries up to ``config.atol`` are
    treated as numerical noise.
    """

    array = np.asarray(matrix, dtype=np.complex128)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise ValueError("matrix must be square")
    dimension = array.shape[0]
    if dimension < 2 or dimension & (dimension - 1):
        raise ValueError("matrix dimension must be a power of two of at least 2")
    if not np.all(np.isfinite(array)):
        return None

    rows = np.empty(dimension, dtype=np.int64)
    amplitudes = np.empty(dimension, dtype=np.complex128)
    for column in range(dimension):
        nonzero = np.flatnonzero(np.abs(array[:, column]) > config.atol)
        if len(nonzero) != 1:
            return None
        row = int(nonzero[0])
        rows[column] = row
        amplitudes[column] = array[row, column]

    x_mask = int(rows[0])
    expected_rows = np.arange(dimension, dtype=np.int64) ^ x_mask
    if not np.array_equal(rows, expected_rows):
        return None

    global_phase = amplitudes[0]
    if not np.isclose(abs(global_phase), 1.0, atol=config.atol, rtol=0):
        return None
    z_mask = 0
    for bit in range(dimension.bit_length() - 1):
        relative_phase = amplitudes[1 << bit] / global_phase
        if np.isclose(relative_phase, -1.0, atol=config.atol, rtol=0):
            z_mask |= 1 << bit
        elif not np.isclose(relative_phase, 1.0, atol=config.atol, rtol=0):
            return None

    signs = np.fromiter(
        (-1.0 if (z_mask & column).bit_count() % 2 else 1.0 for column in range(dimension)),
        dtype=np.float64,
        count=dimension,
    )
    if not np.allclose(amplitudes, global_phase * signs, atol=config.atol, rtol=0):
        return None
    return PauliWord(
        num_qubits=dimension.bit_length() - 1,
        x_mask=x_mask,
        z_mask=z_mask,
    )
