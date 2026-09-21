"""Iterated conjugation groups for small dense-matrix experiments."""

from __future__ import annotations

from dataclasses import dataclass

from .actions import (
    ConjugationActionTable,
    GeneratorSource,
    conjugation_action_table,
    stream_conjugation_generators,
)
from .actions import conjugate as conjugate
from .groups import DEFAULT_SEARCH_LIMITS, GroupClosure, SearchLimits, generate_group
from .operators import Gate, GateSet


@dataclass(frozen=True)
class ConjugationGroup:
    """One level in an iterated conjugation-group construction.

    ``closure.complete`` concerns only closure of the generators that were
    actually supplied.  ``source_complete`` records whether every conjugator
    from the preceding level was available.  ``complete`` requires both, which
    prevents a closed group generated from a truncated prior level from being
    mistaken for the full next conjugation group.
    """

    level: int
    defining_generators: GateSet
    closure: GroupClosure
    source_complete: bool
    action_table: ConjugationActionTable | None = None
    defining_generator_sources: tuple[tuple[GeneratorSource, ...], ...] = ()

    def __post_init__(self) -> None:
        if self.level < 1:
            raise ValueError("conjugation-group level must be at least 1")
        if not self.defining_generator_sources and self.action_table is not None:
            object.__setattr__(
                self,
                "defining_generator_sources",
                self.action_table.unique_image_sources,
            )
        if self.defining_generator_sources:
            if len(self.defining_generator_sources) != len(self.defining_generators):
                raise ValueError("every defining generator must have a provenance entry")
            if any(not sources for sources in self.defining_generator_sources):
                raise ValueError("defining-generator provenance must not be empty")
        if self.action_table is not None:
            if self.action_table.source_complete != self.source_complete:
                raise ValueError("action-table and group source metadata must agree")
            if (
                self.action_table.unique_images.projective_keys
                != self.defining_generators.projective_keys
            ):
                raise ValueError("action-table images must match the defining generators")
            if self.action_table.unique_image_sources != self.defining_generator_sources:
                raise ValueError("action-table and group provenance must agree")

    @property
    def elements(self) -> GateSet:
        """Discovered projective group elements."""

        return self.closure.elements

    @property
    def complete(self) -> bool:
        """Whether this is proven to be the full finite conjugation group."""

        return self.source_complete and self.closure.complete

    @property
    def order(self) -> int | None:
        """Return the proven full order, or ``None`` if either search was partial."""

        return len(self.elements) if self.complete else None


def generate_conjugation_group(
    conjugators: Gate | GateSet,
    probe_generators: GateSet,
    *,
    level: int = 1,
    source_complete: bool = True,
    limits: SearchLimits = DEFAULT_SEARCH_LIMITS,
    retain_action_table: bool = True,
) -> ConjugationGroup:
    r"""Generate one group from conjugated probe generators.

    For a finite set :math:`S` of conjugators and probe generating set
    :math:`P`, this computes

    .. math::

       \langle V P V^\dagger : V \in S,\; P \in P \rangle

    modulo global phase.  Passing a single gate ``U`` therefore constructs the
    first level used in this repository.  ``source_complete`` should be false
    when ``S`` is only a truncated prefix of an earlier group.
    ``retain_action_table=False`` streams cells into projectively unique
    generators and provenance, leaving ``action_table`` unset in the result.
    """

    if level < 1:
        raise ValueError("conjugation-group level must be at least 1")
    if not isinstance(retain_action_table, bool):
        raise TypeError("retain_action_table must be a bool")
    if retain_action_table:
        action_table = conjugation_action_table(
            conjugators,
            probe_generators,
            source_complete=source_complete,
        )
        defining_generators = action_table.unique_images
        defining_generator_sources = action_table.unique_image_sources
    else:
        streamed = stream_conjugation_generators(
            conjugators,
            probe_generators,
            source_complete=source_complete,
        )
        action_table = None
        defining_generators = streamed.unique_images
        defining_generator_sources = streamed.unique_image_sources
    closure = generate_group(defining_generators, limits=limits)
    return ConjugationGroup(
        level=level,
        defining_generators=defining_generators,
        closure=closure,
        source_complete=source_complete,
        defining_generator_sources=defining_generator_sources,
        action_table=action_table,
    )


def generate_next_conjugation_group(
    previous: ConjugationGroup,
    probe_generators: GateSet,
    *,
    limits: SearchLimits = DEFAULT_SEARCH_LIMITS,
    retain_action_table: bool = True,
) -> ConjugationGroup:
    r"""Generate :math:`\Gamma_{j+1}` from discovered elements of ``previous``.

    The convention is

    .. math::

       \Gamma_{j+1}
       = \langle V P V^\dagger : V \in \Gamma_j,\; P \in P \rangle.

    If ``previous`` was truncated, the computation still provides a useful
    partial next level but the returned result cannot be marked complete.
    """

    return generate_conjugation_group(
        previous.elements,
        probe_generators,
        level=previous.level + 1,
        source_complete=previous.complete,
        limits=limits,
        retain_action_table=retain_action_table,
    )


def generate_conjugation_groups(
    seed: Gate | GateSet,
    probe_generators: GateSet,
    *,
    depth: int,
    limits: SearchLimits = DEFAULT_SEARCH_LIMITS,
    retain_action_tables: bool = True,
) -> tuple[ConjugationGroup, ...]:
    r"""Generate :math:`\Gamma_1,\ldots,\Gamma_{depth}` iteratively.

    The same explicit limits apply independently at every level.  Computation
    continues after truncation so users may inspect partial later levels, while
    completeness metadata is propagated. ``retain_action_tables=False`` uses
    streamed generator collection at every level.
    """

    if depth < 1:
        raise ValueError("depth must be at least 1")
    if not isinstance(retain_action_tables, bool):
        raise TypeError("retain_action_tables must be a bool")
    first = generate_conjugation_group(
        seed,
        probe_generators,
        limits=limits,
        retain_action_table=retain_action_tables,
    )
    groups = [first]
    for _ in range(1, depth):
        groups.append(
            generate_next_conjugation_group(
                groups[-1],
                probe_generators,
                limits=limits,
                retain_action_table=retain_action_tables,
            )
        )
    return tuple(groups)
