"""Exact binary checks for the de Silva--Lautsch five-qubit counterexample.

Target coordinates are ``x1,x2,x3,z1,z2,z3``, encoded as six bits. Products act
right to left. The target maps are

``A = CX(2,3) CZ(2,3)`` and ``B = CX(2,3) CX(1,2) H(1)``.

The computation uses exact arithmetic over :math:`F_2`; no floating point is
involved. It checks the symplectic hypotheses used in Theorem 3.6 and exhausts
the target Lagrangians used in Theorem 2.5. It is not an independent recursive
five-qubit hierarchy-membership implementation.
"""

from __future__ import annotations

import json
from itertools import combinations
from typing import TypeAlias

LinearMap: TypeAlias = tuple[int, ...]
VECTOR_SPACE = tuple(range(64))
IDENTITY: LinearMap = VECTOR_SPACE
ZERO: LinearMap = (0,) * 64


def _hadamard(vector: int, qubit: int) -> int:
    swap = ((vector >> qubit) ^ (vector >> (qubit + 3))) & 1
    return vector ^ swap * ((1 << qubit) | (1 << (qubit + 3)))


def _cx(vector: int, control: int, target: int) -> int:
    return vector ^ (((vector >> control) & 1) << target) ^ (
        ((vector >> (target + 3)) & 1) << (control + 3)
    )


def _cz(vector: int, qubit_a: int, qubit_b: int) -> int:
    return vector ^ (((vector >> qubit_a) & 1) << (qubit_b + 3)) ^ (
        ((vector >> qubit_b) & 1) << (qubit_a + 3)
    )


def _compose(left: LinearMap, right: LinearMap) -> LinearMap:
    """Return ``left`` after ``right``."""

    return tuple(left[right[vector]] for vector in VECTOR_SPACE)


def _inverse(mapping: LinearMap) -> LinearMap:
    result = [0] * 64
    for vector, image in enumerate(mapping):
        result[image] = vector
    return tuple(result)


def _power(mapping: LinearMap, exponent: int) -> LinearMap:
    result = IDENTITY
    for _ in range(exponent):
        result = _compose(mapping, result)
    return result


def _parity(value: int) -> int:
    """Return population-count parity without requiring ``int.bit_count``."""

    return bin(value).count("1") % 2


def _pairing(left: int, right: int) -> int:
    return (_parity((left & 7) & (right >> 3)) + _parity((right & 7) & (left >> 3))) % 2


def _target_maps() -> tuple[LinearMap, LinearMap]:
    map_a = tuple(_cx(_cz(vector, 1, 2), 1, 2) for vector in VECTOR_SPACE)
    map_b = tuple(_cx(_cx(_hadamard(vector, 0), 0, 1), 1, 2) for vector in VECTOR_SPACE)
    return map_a, map_b


def _lagrangians() -> set[frozenset[int]]:
    result: set[frozenset[int]] = set()
    for left, middle, right in combinations(range(1, 64), 3):
        if _pairing(left, middle) or _pairing(left, right) or _pairing(middle, right):
            continue
        subspace = frozenset(
            (
                0,
                left,
                middle,
                right,
                left ^ middle,
                left ^ right,
                middle ^ right,
                left ^ middle ^ right,
            )
        )
        if len(subspace) == 8:
            result.add(subspace)
    return result


def _nilpotency_index(mapping: LinearMap, limit: int) -> int:
    for exponent in range(1, limit + 1):
        if _power(mapping, exponent) == ZERO:
            return exponent
    raise ValueError(f"map was not nilpotent within exponent {limit}")


def verify_counterexample() -> dict[str, object]:
    """Run the exact finite-field verification and return JSON-safe results."""

    map_a, map_b = _target_maps()
    symplectic = all(
        _pairing(mapping[left], mapping[right]) == _pairing(left, right)
        for mapping in (map_a, map_b)
        for left in VECTOR_SPACE
        for right in VECTOR_SPACE
    )
    if not symplectic:
        raise AssertionError("A and B must preserve the symplectic pairing")
    if _power(map_a, 2) != IDENTITY:
        raise AssertionError("A must be an involution")

    b_minus_identity = tuple(map_b[vector] ^ vector for vector in VECTOR_SPACE)
    b_nilpotency_index = _nilpotency_index(b_minus_identity, 6)

    comparison = {
        (control_c, control_d): _compose(_power(map_b, control_c), _power(map_a, control_d))
        for control_c in (0, 1)
        for control_d in (0, 1)
    }
    relative_indices: dict[str, int] = {}
    for base in comparison:
        differences = {
            offset: _compose(
                comparison[(offset[0] ^ base[0], offset[1] ^ base[1])],
                _inverse(comparison[offset]),
            )
            for offset in comparison
        }
        if any(differences[(control, 0)] != differences[(control, 1)] for control in (0, 1)):
            raise AssertionError("comparison maps unexpectedly depend on the second control")
        relative = _compose(differences[(1, 0)], _inverse(differences[(0, 0)]))
        relative_minus_identity = tuple(relative[vector] ^ vector for vector in VECTOR_SPACE)
        relative_indices[str(base)] = _nilpotency_index(relative_minus_identity, 3)

    lagrangians = _lagrangians()
    if len(lagrangians) != 135:
        raise AssertionError("expected exactly 135 target Lagrangians")
    fixed_a = [space for space in lagrangians if frozenset(map_a[v] for v in space) == space]
    fixed_b = [space for space in lagrangians if frozenset(map_b[v] for v in space) == space]
    common = [space for space in fixed_b if frozenset(map_a[v] for v in space) == space]
    if common:
        raise AssertionError("A and B must have no common invariant Lagrangian")

    return {
        "arithmetic": "exact over F_2; no floating point",
        "target_lagrangians": len(lagrangians),
        "A_invariant_lagrangians": len(fixed_a),
        "B_invariant_lagrangians": len(fixed_b),
        "common_invariant_lagrangians": len(common),
        "B_minus_I_nilpotency_index": b_nilpotency_index,
        "B_fourth_power_is_identity": _power(map_b, 4) == IDENTITY,
        "relative_minus_I_nilpotency_indices": relative_indices,
        "Theorem_3_6_m_equals_2_hypotheses": "PASS",
        "Theorem_2_5_non_GSC_obstruction": "PASS",
        "Lemma_5_7_non_C4_obstruction": "PASS",
    }


def main() -> None:
    """Print exact verification results as JSON."""

    print(json.dumps(verify_counterexample(), indent=2))


if __name__ == "__main__":
    main()
