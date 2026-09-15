"""Tools for conjugation-group calculations in the Clifford hierarchy."""

from .actions import (
    ActionImageClassification,
    ConjugationAction,
    ConjugationActionTable,
    PauliActionClassification,
    classify_action_images,
    classify_pauli_images,
    conjugation_action,
    conjugation_action_table,
)
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
from .paulis import PauliWord, recognize_pauli_word
from .standard_gates import (
    DEFAULT_PAULI_CATALOG_LIMIT,
    embed_one_qubit_gate,
    pauli_generators,
    projective_pauli_group,
)

__all__ = [
    "DEFAULT_PROJECTIVE_CONFIG",
    "DEFAULT_SEARCH_LIMITS",
    "DEFAULT_PAULI_CATALOG_LIMIT",
    "ActionImageClassification",
    "ConjugationAction",
    "ConjugationActionTable",
    "ConjugationGroup",
    "Gate",
    "GateSet",
    "GroupClosure",
    "PauliActionClassification",
    "PauliWord",
    "ProjectiveConfig",
    "SearchLimits",
    "StopReason",
    "canonicalize_projective",
    "classify_action_images",
    "classify_pauli_images",
    "conjugate",
    "conjugation_action",
    "conjugation_action_table",
    "embed_one_qubit_gate",
    "generate_conjugation_group",
    "generate_conjugation_groups",
    "generate_group",
    "generate_next_conjugation_group",
    "pauli_generators",
    "projective_key",
    "projective_pauli_group",
    "projectively_equal",
    "recognize_pauli_word",
    "verify_counterexample",
]
__version__ = "0.3.0"
