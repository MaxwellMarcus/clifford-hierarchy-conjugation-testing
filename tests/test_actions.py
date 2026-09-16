import numpy as np
import pytest

from clifford_conjugation import (
    ConjugationAction,
    ConjugationActionTable,
    Gate,
    GateSet,
    ProjectiveConfig,
    classify_action_images,
    classify_pauli_images,
    conjugation_action,
    conjugation_action_table,
    pauli_generators,
    projective_pauli_group,
    projectively_equal,
)

IDENTITY = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.diag([1, -1]).astype(complex)
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
S = np.diag([1, 1j]).astype(complex)


def pauli_probes() -> GateSet:
    return GateSet([Gate("X", X), Gate("Z", Z)])


def test_action_exposes_named_generator_images() -> None:
    action = conjugation_action(Gate("S", S), pauli_probes())

    assert projectively_equal(action.image("X").matrix, Y)
    assert projectively_equal(action.image(1).matrix, Z)
    assert tuple(action.as_dict()) == ("X", "Z")


def test_action_applies_to_words_without_enumerating_the_group() -> None:
    action = conjugation_action(Gate("H", H), pauli_probes())

    image = action.apply_word(["X", "Z"])
    direct = H @ (X @ Z) @ H.conj().T
    identity_image = action.apply_word([])

    assert projectively_equal(image.matrix, direct)
    assert projectively_equal(image.matrix, Z @ X)
    assert projectively_equal(identity_image.matrix, IDENTITY)


def test_action_reference_errors_are_explicit() -> None:
    action = conjugation_action(Gate("H", H), pauli_probes())

    with pytest.raises(KeyError, match="unknown generator"):
        action.image("Y")
    with pytest.raises(IndexError, match="out of range"):
        action.image(2)
    with pytest.raises(TypeError, match="not a string"):
        action.apply_word("XZ")
    with pytest.raises(TypeError, match="name or integer"):
        action.image(True)


def test_multi_conjugator_table_has_addressable_rows_and_cells() -> None:
    conjugators = GateSet([Gate("I", IDENTITY), Gate("H", H)])
    table = conjugation_action_table(conjugators, pauli_probes())

    assert table.shape == (2, 2)
    assert table.source_complete
    assert table.row("H").conjugator.name == "H"
    assert projectively_equal(table.image("I", "X").matrix, X)
    assert projectively_equal(table.image(1, 0).matrix, Z)
    assert len(table.unique_images) == 2
    assert tuple(
        tuple(source.label for source in sources)
        for sources in table.unique_image_sources
    ) == (
        ("I conjugates X", "H conjugates Z"),
        ("I conjugates Z", "H conjugates X"),
    )
    assert table[:1] == (table[0],)

    with pytest.raises(KeyError, match="unknown conjugator"):
        table.row("S")
    with pytest.raises(IndexError, match="out of range"):
        table.row(2)
    with pytest.raises(TypeError, match="name or integer"):
        table.row(False)


def test_table_records_incomplete_source_without_skipping_cells() -> None:
    table = conjugation_action_table(
        Gate("H", H),
        pauli_probes(),
        source_complete=False,
    )

    assert table.shape == (1, 2)
    assert not table.source_complete
    assert len(table[0].images) == 2
    assert tuple(source.label for sources in table.unique_image_sources for source in sources) == (
        "H conjugates X",
        "H conjugates Z",
    )


def test_provenance_retains_multiple_rows_for_duplicate_images() -> None:
    conjugators = GateSet([Gate("I", IDENTITY), Gate("H", H), Gate("S", S)])
    table = conjugation_action_table(conjugators, pauli_probes())

    assert len(table.unique_images) == 3
    assert tuple(len(sources) for sources in table.unique_image_sources) == (2, 3, 1)
    assert tuple(source.label for source in table.unique_image_sources[1]) == (
        "I conjugates Z",
        "H conjugates X",
        "S conjugates Z",
    )
    assert tuple(
        (source.row_index, source.column_index)
        for source in table.unique_image_sources[1]
    ) == ((0, 1), (1, 0), (2, 1))


def test_action_images_are_classified_with_projective_pauli_labels() -> None:
    conjugators = GateSet([Gate("I", IDENTITY), Gate("H", H), Gate("S", S)])
    table = conjugation_action_table(conjugators, pauli_probes())
    classification = table.classify(projective_pauli_group(1))

    assert classification.all_recognized
    assert classification.recognized_count == classification.total_count == 6
    assert classification.coverage == 1.0
    assert classification.label("I", "X") == "X_0"
    assert classification.label("H", "X") == "Z_0"
    assert classification.label("S", "X") == "Y_0"
    assert classification.as_rows() == (
        ("X_0", "Z_0"),
        ("Z_0", "X_0"),
        ("Y_0", "Z_0"),
    )


def test_classification_reports_unknown_non_pauli_images() -> None:
    t_gate = Gate("T", np.diag([1, np.exp(1j * np.pi / 4)]))
    table = conjugation_action_table(t_gate, pauli_probes())
    classification = classify_action_images(table, projective_pauli_group(1))

    assert not classification.all_recognized
    assert classification.coverage == 0.5
    assert classification.label("T", "X") is None
    assert classification.label("T", "X", unknown="?") == "?"
    assert classification.label("T", "Z") == "Z_0"
    assert classification.unrecognized == (("T", "X"),)
    assert classification.as_rows(unknown="unknown") == (("unknown", "Z_0"),)


def test_classification_requires_same_dimension() -> None:
    table = conjugation_action_table(Gate("H", H), pauli_probes())

    with pytest.raises(ValueError, match="same dimension"):
        table.classify(projective_pauli_group(2))


def test_direct_pauli_classification_matches_catalog_classification() -> None:
    conjugators = GateSet([Gate("I", IDENTITY), Gate("H", H), Gate("S", S)])
    table = conjugation_action_table(conjugators, pauli_probes())
    direct = table.classify_paulis()
    catalog = table.classify(projective_pauli_group(1))

    assert direct.preserves_paulis
    assert direct.all_recognized
    assert direct.recognized_count == direct.total_count == 6
    assert direct.coverage == 1.0
    assert direct.as_rows() == catalog.as_rows()
    assert direct.label("S", "X") == "Y_0"
    assert direct.match("H", "X").label == "Z_0"
    assert direct.unrecognized == ()


def test_direct_pauli_classification_reports_non_clifford_image() -> None:
    t_gate = Gate("T", np.diag([1, np.exp(1j * np.pi / 4)]))
    table = conjugation_action_table(t_gate, pauli_probes())
    classification = classify_pauli_images(table)

    assert not classification.preserves_paulis
    assert classification.coverage == 0.5
    assert classification.label("T", "X", unknown="not Pauli") == "not Pauli"
    assert classification.label("T", "Z") == "Z_0"
    assert classification.unrecognized == (("T", "X"),)


def test_direct_pauli_classification_does_not_need_exponential_catalog() -> None:
    probes = pauli_generators(6)
    table = conjugation_action_table(Gate.identity(6), probes)
    classification = table.classify_paulis()

    assert classification.preserves_paulis
    assert classification.total_count == 12
    assert classification.as_rows()[0] == tuple(gate.name for gate in probes)


def test_direct_classification_exposes_induced_symplectic_action() -> None:
    conjugators = GateSet([Gate("H", H), Gate("S", S)])
    table = conjugation_action_table(conjugators, pauli_generators(1))
    classification = table.classify_paulis()

    assert classification.row_preserves_paulis("H")
    assert np.array_equal(
        classification.symplectic_matrix("H"),
        np.array([[0, 1], [1, 0]], dtype=np.uint8),
    )
    assert np.array_equal(
        classification.symplectic_matrix("S"),
        np.array([[1, 0], [1, 1]], dtype=np.uint8),
    )
    assert not classification.symplectic_matrix("H").flags.writeable


def test_symplectic_action_requires_complete_standard_probes_and_pauli_images() -> None:
    t_gate = Gate("T", np.diag([1, np.exp(1j * np.pi / 4)]))
    non_clifford = conjugation_action_table(t_gate, pauli_generators(1)).classify_paulis()
    incomplete_probes = GateSet([Gate("X", X)])
    incomplete = conjugation_action_table(Gate("H", H), incomplete_probes).classify_paulis()

    assert not non_clifford.row_preserves_paulis("T")
    with pytest.raises(ValueError, match="does not map every probe"):
        non_clifford.symplectic_matrix("T")
    with pytest.raises(ValueError, match="standard Pauli generators"):
        incomplete.symplectic_matrix("H")


def test_action_rejects_incorrect_image_data() -> None:
    probes = pauli_probes()
    with pytest.raises(ValueError, match="not its conjugate"):
        ConjugationAction(
            conjugator=Gate("H", H),
            domain_generators=probes,
            images=(Gate("wrong-X", X), Gate("wrong-Z", Z)),
        )
    with pytest.raises(ValueError, match="exactly one image"):
        ConjugationAction(
            conjugator=Gate("H", H),
            domain_generators=probes,
            images=(Gate("only-one", Z),),
        )
    with pytest.raises(ValueError, match="same dimension"):
        conjugation_action(Gate.identity(2), probes)


def test_table_rejects_wrong_row_and_source_metadata() -> None:
    probes = pauli_probes()
    h_action = conjugation_action(Gate("H", H), probes)

    with pytest.raises(ValueError, match="conjugator order"):
        ConjugationActionTable(
            GateSet([Gate("I", IDENTITY)]),
            probes,
            [h_action],
        )
    with pytest.raises(TypeError, match="source_complete"):
        conjugation_action_table(Gate("H", H), probes, source_complete=1)
    with pytest.raises(ValueError, match="one action row"):
        ConjugationActionTable(
            GateSet([Gate("H", H)]),
            probes,
            [],
        )
    with pytest.raises(TypeError, match="ConjugationAction"):
        ConjugationActionTable(
            GateSet([Gate("H", H)]),
            probes,
            [object()],
        )

    other_config = ProjectiveConfig(decimals=8)
    mismatched_conjugators = GateSet(
        [Gate("H", H)],
        projective_config=other_config,
    )
    with pytest.raises(ValueError, match="projective settings"):
        ConjugationActionTable(mismatched_conjugators, probes, [h_action])


def test_action_table_rejects_non_gate_collections() -> None:
    with pytest.raises(TypeError, match="Gate or GateSet"):
        conjugation_action_table([Gate("H", H)], pauli_probes())
