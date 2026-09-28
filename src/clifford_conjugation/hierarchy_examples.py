"""Exact small examples for the third level of the Clifford hierarchy.

The exact analysis in this module is deliberately narrow: diagonal gates whose
entries are eighth roots of unity.  Integer phase exponents modulo eight avoid
using floating-point conjugation as a proof of hierarchy membership.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from .operators import Gate

EIGHTH_ROOT_MODULUS = 8


@dataclass(frozen=True)
class DiagonalC3Analysis:
    """Exact third-level analysis for an eighth-root diagonal gate.

    ``phase_polynomial_coefficients`` is the multilinear Boolean polynomial
    for the gate's phase function, indexed by computational-basis bit mask.
    Each row of ``x_image_phase_coefficients`` describes the diagonal factor in
    ``U X_i U† = X_i D_i``.  A row is a diagonal Clifford exactly when its
    linear coefficients are even, its quadratic coefficients are divisible by
    four, and all higher-degree coefficients vanish modulo eight.
    """

    phase_exponents: tuple[int, ...]
    phase_polynomial_coefficients: tuple[int, ...]
    x_image_phase_coefficients: tuple[tuple[int, ...], ...]
    is_clifford: bool
    x_images_are_clifford: tuple[bool, ...]

    @property
    def num_qubits(self) -> int:
        """Number of qubits represented by the phase table."""

        return len(self.phase_exponents).bit_length() - 1

    @property
    def is_in_third_level(self) -> bool:
        """Whether every Pauli generator is mapped to a Clifford."""

        return all(self.x_images_are_clifford)

    @property
    def is_proper_third_level(self) -> bool:
        """Whether the gate is in C3 but not already Clifford (C2)."""

        return self.is_in_third_level and not self.is_clifford


def eighth_root_diagonal_gate(name: str, phase_exponents: Iterable[int]) -> Gate:
    """Construct ``diag(exp(i*pi*k/4))`` from exact exponents modulo eight."""

    exponents = _normalize_phase_exponents(phase_exponents)
    phases = np.exp(1j * np.pi * np.asarray(exponents, dtype=np.float64) / 4.0)
    return Gate(name, np.diag(phases))


def analyze_diagonal_c3(phase_exponents: Iterable[int]) -> DiagonalC3Analysis:
    """Decide exact C3 membership within the eighth-root diagonal domain.

    For a phase function ``f``, conjugating ``X_i`` gives ``X_i D_i`` with
    diagonal exponent ``f(x xor e_i) - f(x)`` modulo eight.  The gate belongs
    to C3 exactly when each ``D_i`` is a diagonal Clifford.  Conjugated Z
    generators need no test because every diagonal gate commutes with them.
    """

    exponents = _normalize_phase_exponents(phase_exponents)
    num_qubits = len(exponents).bit_length() - 1
    phase_coefficients = _multilinear_coefficients(exponents)
    x_coefficients = []
    x_images_are_clifford = []
    for qubit in range(num_qubits):
        bit = 1 << (num_qubits - 1 - qubit)
        difference = tuple(
            (exponents[basis_index ^ bit] - exponents[basis_index])
            % EIGHTH_ROOT_MODULUS
            for basis_index in range(len(exponents))
        )
        coefficients = _multilinear_coefficients(difference)
        x_coefficients.append(coefficients)
        x_images_are_clifford.append(_is_diagonal_clifford(coefficients))
    return DiagonalC3Analysis(
        phase_exponents=exponents,
        phase_polynomial_coefficients=phase_coefficients,
        x_image_phase_coefficients=tuple(x_coefficients),
        is_clifford=_is_diagonal_clifford(phase_coefficients),
        x_images_are_clifford=tuple(x_images_are_clifford),
    )


def ccz_gate() -> Gate:
    """Return CCZ, whose only nontrivial phase is ``-1`` on ``|111>``."""

    return eighth_root_diagonal_gate("CCZ", (0, 0, 0, 0, 0, 0, 0, 4))


def controlled_t_gate() -> Gate:
    """Return controlled-T with an eighth-root phase on ``|11>``."""

    return eighth_root_diagonal_gate("controlled-T", (0, 0, 0, 1))


def _normalize_phase_exponents(phase_exponents: Iterable[int]) -> tuple[int, ...]:
    if isinstance(phase_exponents, (str, bytes)):
        raise TypeError("phase_exponents must be an iterable of integers")
    exponents = tuple(phase_exponents)
    if len(exponents) < 2 or len(exponents) & (len(exponents) - 1):
        raise ValueError("phase_exponents length must be a power of two of at least 2")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in exponents):
        raise TypeError("phase exponents must be integers")
    return tuple(value % EIGHTH_ROOT_MODULUS for value in exponents)


def _multilinear_coefficients(values: tuple[int, ...]) -> tuple[int, ...]:
    coefficients = list(values)
    num_qubits = len(values).bit_length() - 1
    for bit_index in range(num_qubits):
        bit = 1 << bit_index
        for mask in range(len(coefficients)):
            if mask & bit:
                coefficients[mask] = (
                    coefficients[mask] - coefficients[mask ^ bit]
                ) % EIGHTH_ROOT_MODULUS
    return tuple(coefficients)


def _is_diagonal_clifford(coefficients: tuple[int, ...]) -> bool:
    for mask, coefficient in enumerate(coefficients):
        degree = mask.bit_count()
        if degree == 0:
            continue
        if degree == 1 and coefficient % 2 == 0:
            continue
        if degree == 2 and coefficient % 4 == 0:
            continue
        if coefficient == 0:
            continue
        return False
    return True
