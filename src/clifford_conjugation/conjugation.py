"""Iterated conjugation groups for small dense-matrix experiments."""

from __future__ import annotations

from dataclasses import dataclass

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

    def __post_init__(self) -> None:
        if self.level < 1:
            raise ValueError("conjugation-group level must be at least 1")

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


def generate_conjugation_group(
    conjugators: Gate | GateSet,
    probe_generators: GateSet,
    *,
    level: int = 1,
    source_complete: bool = True,
    limits: SearchLimits = DEFAULT_SEARCH_LIMITS,
) -> ConjugationGroup:
    r"""Generate one group from conjugated probe generators.

    For a finite set :math:`S` of conjugators and probe generating set
    :math:`P`, this computes

    .. math::

       \langle V P V^\dagger : V \in S,\; P \in P \rangle

    modulo global phase.  Passing a single gate ``U`` therefore constructs the
    first level used in this repository.  ``source_complete`` should be false
    when ``S`` is only a truncated prefix of an earlier group.
    """

    if level < 1:
        raise ValueError("conjugation-group level must be at least 1")
    if not isinstance(source_complete, bool):
        raise TypeError("source_complete must be a bool")
    if isinstance(conjugators, Gate):
        conjugator_set = GateSet(
            [conjugators],
            projective_config=probe_generators.projective_config,
        )
    elif isinstance(conjugators, GateSet):
        conjugator_set = conjugators
    else:
        raise TypeError("conjugators must be a Gate or GateSet")
    if conjugator_set.dimension != probe_generators.dimension:
        raise ValueError("conjugators and probes must have the same dimension")
    if conjugator_set.projective_config != probe_generators.projective_config:
        raise ValueError("conjugators and probes must use the same projective settings")

    generated = [
        conjugate(conjugator, probe)
        for conjugator in conjugator_set
        for probe in probe_generators
    ]
    defining_generators = GateSet(
        generated,
        projective_config=probe_generators.projective_config,
    )
    closure = generate_group(defining_generators, limits=limits)
    return ConjugationGroup(
        level=level,
        defining_generators=defining_generators,
        closure=closure,
        source_complete=source_complete,
    )


def generate_next_conjugation_group(
    previous: ConjugationGroup,
    probe_generators: GateSet,
    *,
    limits: SearchLimits = DEFAULT_SEARCH_LIMITS,
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
    )


def generate_conjugation_groups(
    seed: Gate | GateSet,
    probe_generators: GateSet,
    *,
    depth: int,
    limits: SearchLimits = DEFAULT_SEARCH_LIMITS,
) -> tuple[ConjugationGroup, ...]:
    r"""Generate :math:`\Gamma_1,\ldots,\Gamma_{depth}` iteratively.

    The same explicit limits apply independently at every level.  Computation
    continues after truncation so users may inspect partial later levels, while
    completeness metadata is propagated.
    """

    if depth < 1:
        raise ValueError("depth must be at least 1")
    first = generate_conjugation_group(seed, probe_generators, limits=limits)
    groups = [first]
    for _ in range(1, depth):
        groups.append(
            generate_next_conjugation_group(groups[-1], probe_generators, limits=limits)
        )
    return tuple(groups)
