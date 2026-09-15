"""Tools for conjugation-group calculations in the Clifford hierarchy."""

from .conjugation import (
    ConjugationGroup,
    conjugate,
    generate_conjugation_group,
    generate_conjugation_groups,
    generate_next_conjugation_group,
)
from .de_silva_lautsch import verify_counterexample
from .groups import (
    DEFAULT_SEARCH_LIMITS,
    GroupClosure,
    SearchLimits,
    StopReason,
    generate_group,
)
from .operators import (
    DEFAULT_PROJECTIVE_CONFIG,
    Gate,
    GateSet,
    ProjectiveConfig,
    canonicalize_projective,
    projective_key,
    projectively_equal,
)

__all__ = [
    "DEFAULT_PROJECTIVE_CONFIG",
    "DEFAULT_SEARCH_LIMITS",
    "ConjugationGroup",
    "Gate",
    "GateSet",
    "GroupClosure",
    "ProjectiveConfig",
    "SearchLimits",
    "StopReason",
    "canonicalize_projective",
    "conjugate",
    "generate_conjugation_group",
    "generate_conjugation_groups",
    "generate_group",
    "generate_next_conjugation_group",
    "projective_key",
    "projectively_equal",
    "verify_counterexample",
]
__version__ = "0.2.0"
