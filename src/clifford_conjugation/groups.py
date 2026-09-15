"""Finite projective group closure for small dense matrices."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum

from .operators import Gate, GateSet, ProjectiveConfig, projective_key


class StopReason(str, Enum):
    """Why a group-closure search stopped."""

    COMPLETE = "complete"
    MAX_ELEMENTS = "max_elements"
    MAX_PRODUCTS = "max_products"


@dataclass(frozen=True)
class SearchLimits:
    """Hard resource limits for a finite group search."""

    max_elements: int = 4096
    max_products: int = 1_000_000

    def __post_init__(self) -> None:
        if self.max_elements < 1:
            raise ValueError("max_elements must be at least 1")
        if self.max_products < 1:
            raise ValueError("max_products must be at least 1")


DEFAULT_SEARCH_LIMITS = SearchLimits()


@dataclass(frozen=True)
class GroupClosure:
    """Result of closing a generating set under multiplication.

    ``complete`` is true only when the breadth-first search exhausted its queue,
    thereby proving that the discovered finite set is closed under right
    multiplication by every generator.  A false value means ``elements`` is
    only the discovered prefix and must not be reported as the group order.
    ``words[i]`` records a generator-name word for ``elements[i]``.
    """

    generators: GateSet
    elements: GateSet
    words: tuple[tuple[str, ...], ...]
    complete: bool
    stop_reason: StopReason
    products_tested: int
    max_word_length: int
    limits: SearchLimits

    def __post_init__(self) -> None:
        if len(self.elements) != len(self.words):
            raise ValueError("elements and words must have equal length")
        if self.complete != (self.stop_reason is StopReason.COMPLETE):
            raise ValueError("complete and stop_reason are inconsistent")

    @property
    def order(self) -> int | None:
        """Return the proven group order, or ``None`` for a truncated search."""

        return len(self.elements) if self.complete else None


def generate_group(
    generators: GateSet,
    *,
    limits: SearchLimits = DEFAULT_SEARCH_LIMITS,
) -> GroupClosure:
    """Close ``generators`` under multiplication modulo global phase.

    The search starts at the identity and performs a deterministic breadth-first
    traversal using right multiplication.  If it terminates naturally, the
    resulting finite semigroup of unitaries is a group.  Infinite groups and
    large finite groups are returned as explicitly truncated results.
    """

    config = generators.projective_config
    identity = Gate.identity(generators.num_qubits)
    identity_key = projective_key(identity.matrix, config)
    discovered = [identity]
    words: list[tuple[str, ...]] = [()]
    keys = {identity_key}
    frontier: deque[int] = deque([0])
    products_tested = 0
    max_word_length = 0

    while frontier:
        element_index = frontier.popleft()
        element = discovered[element_index]
        word = words[element_index]
        for generator in generators:
            if products_tested >= limits.max_products:
                return _result(
                    generators,
                    discovered,
                    words,
                    False,
                    StopReason.MAX_PRODUCTS,
                    products_tested,
                    max_word_length,
                    limits,
                    config,
                )

            candidate_matrix = element.matrix @ generator.matrix
            products_tested += 1
            key = projective_key(candidate_matrix, config)
            if key in keys:
                continue
            if len(discovered) >= limits.max_elements:
                return _result(
                    generators,
                    discovered,
                    words,
                    False,
                    StopReason.MAX_ELEMENTS,
                    products_tested,
                    max_word_length,
                    limits,
                    config,
                )

            candidate_word = (*word, generator.name)
            discovered.append(Gate(f"g{len(discovered)}", candidate_matrix))
            words.append(candidate_word)
            keys.add(key)
            frontier.append(len(discovered) - 1)
            max_word_length = max(max_word_length, len(candidate_word))

    return _result(
        generators,
        discovered,
        words,
        True,
        StopReason.COMPLETE,
        products_tested,
        max_word_length,
        limits,
        config,
    )


def _result(
    generators: GateSet,
    elements: list[Gate],
    words: list[tuple[str, ...]],
    complete: bool,
    stop_reason: StopReason,
    products_tested: int,
    max_word_length: int,
    limits: SearchLimits,
    config: ProjectiveConfig,
) -> GroupClosure:
    # Elements are already unique, but GateSet gives callers a consistent
    # immutable container and projective membership operation.
    return GroupClosure(
        generators=generators,
        elements=GateSet(elements, projective_config=config),
        words=tuple(words),
        complete=complete,
        stop_reason=stop_reason,
        products_tested=products_tested,
        max_word_length=max_word_length,
        limits=limits,
    )
