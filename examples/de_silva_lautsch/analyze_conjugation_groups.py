"""Numerically analyze the de Silva--Lautsch counterexample's conjugation groups.

This script preserves the exploratory search used in the research calculation.
It canonicalizes matrices up to global phase using rounded floating-point data;
use ``exact_counterexample_witness.py`` to verify the resulting witness exactly.
"""

from collections import Counter
from itertools import combinations

import numpy as np

NUM_QUBITS = 5
DIMENSION = 32
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)


def kron(operators):
    result = np.array([[1]], dtype=complex)
    for operator in operators:
        result = np.kron(result, operator)
    return result


def one_qubit(operator, qubit, num_qubits=NUM_QUBITS):
    operators = [I2] * num_qubits
    operators[qubit] = operator
    return kron(operators)


def bit(value, qubit, num_qubits=NUM_QUBITS):
    return (value >> (num_qubits - 1 - qubit)) & 1


def permutation_gate(num_qubits, function):
    result = np.zeros((1 << num_qubits, 1 << num_qubits), dtype=complex)
    for column in range(1 << num_qubits):
        result[function(column), column] = 1
    return result


def cx(num_qubits, control, target):
    return permutation_gate(
        num_qubits,
        lambda value: value ^ (bit(value, control, num_qubits) << (num_qubits - 1 - target)),
    )


def cz(num_qubits, qubit_a, qubit_b):
    diagonal = [
        (-1) ** (bit(value, qubit_a, num_qubits) * bit(value, qubit_b, num_qubits))
        for value in range(1 << num_qubits)
    ]
    return np.diag(diagonal).astype(complex)


def controlled(target_gate, control, targets):
    result = np.zeros((DIMENSION, DIMENSION), dtype=complex)
    num_targets = len(targets)
    for column in range(DIMENSION):
        if not bit(column, control):
            result[column, column] = 1
            continue
        target_column = sum(
            bit(column, qubit) << (num_targets - 1 - position)
            for position, qubit in enumerate(targets)
        )
        for target_row in range(1 << num_targets):
            amplitude = target_gate[target_row, target_column]
            if abs(amplitude) < 1e-12:
                continue
            row = column
            for position, qubit in enumerate(targets):
                desired = (target_row >> (num_targets - 1 - position)) & 1
                if bit(row, qubit) != desired:
                    row ^= 1 << (NUM_QUBITS - 1 - qubit)
            result[row, column] = amplitude
    return result


def canonical_key(matrix, decimals=9):
    flattened = matrix.ravel()
    nonzero = np.flatnonzero(abs(flattened) > 1e-7)
    if not len(nonzero):
        return b"zero"
    phase = flattened[nonzero[0]] / abs(flattened[nonzero[0]])
    normalized = np.array(matrix / phase, dtype=complex)
    normalized.real[abs(normalized.real) < 1e-8] = 0
    normalized.imag[abs(normalized.imag) < 1e-8] = 0
    return np.round(normalized.real, decimals).tobytes() + np.round(
        normalized.imag, decimals
    ).tobytes()


def projective_order(matrix, limit=4096):
    product = np.eye(DIMENSION, dtype=complex)
    identity_key = canonical_key(product)
    for exponent in range(1, limit + 1):
        product = product @ matrix
        if canonical_key(product) == identity_key:
            return exponent
    return None


def main():
    target_a = cx(3, 1, 2) @ cz(3, 1, 2)
    target_b = cx(3, 1, 2) @ cx(3, 0, 1) @ one_qubit(H, 0, 3)
    unitary = controlled(target_b, 0, [2, 3, 4]) @ controlled(target_a, 1, [2, 3, 4])
    generators = [one_qubit(X, q) for q in range(5)] + [one_qubit(Z, q) for q in range(5)]
    generator_names = [f"X_{q}" for q in ["c", "d", "1", "2", "3"]] + [
        f"Z_{q}" for q in ["c", "d", "1", "2", "3"]
    ]

    pauli = {}
    pauli_matrices = []
    for mask in range(1024):
        matrix = np.eye(DIMENSION, dtype=complex)
        names = []
        for index, generator in enumerate(generators):
            if mask >> index & 1:
                matrix = matrix @ generator
                names.append(generator_names[index])
        pauli[canonical_key(matrix)] = " ".join(names) or "I"
        pauli_matrices.append(matrix)

    def is_pauli(matrix):
        return canonical_key(matrix) in pauli

    clifford_cache = {}

    def clifford_test(matrix):
        key = canonical_key(matrix)
        if key in clifford_cache:
            return clifford_cache[key]
        for index, pauli_generator in enumerate(generators):
            image = matrix @ pauli_generator @ matrix.conj().T
            if not is_pauli(image):
                answer = False, (index, image)
                clifford_cache[key] = answer
                return answer
        answer = True, None
        clifford_cache[key] = answer
        return answer

    c3_cache = {}

    def c3_test(matrix):
        key = canonical_key(matrix)
        if key in c3_cache:
            return c3_cache[key]
        for index, pauli_generator in enumerate(generators):
            image = matrix @ pauli_generator @ matrix.conj().T
            if not clifford_test(image)[0]:
                answer = False, (index, image)
                c3_cache[key] = answer
                return answer
        answer = True, None
        c3_cache[key] = answer
        return answer

    conjugated_generators = [unitary @ p @ unitary.conj().T for p in generators]
    gamma_1 = []
    for mask in range(1024):
        matrix = np.eye(DIMENSION, dtype=complex)
        for index, generator in enumerate(conjugated_generators):
            if mask >> index & 1:
                matrix = matrix @ generator
        gamma_1.append(matrix)
    assert len({canonical_key(matrix) for matrix in gamma_1}) == 1024

    defining = {}
    for mask, v in enumerate(gamma_1):
        for index, p in enumerate(generators):
            image = v @ p @ v.conj().T
            defining.setdefault(canonical_key(image), (image, mask, index))

    print("Gamma1 order", len(gamma_1))
    gamma_1_pauli = sum(is_pauli(matrix) for matrix in gamma_1)
    gamma_1_clifford = sum(clifford_test(matrix)[0] for matrix in gamma_1)
    gamma_1_c3 = sum(c3_test(matrix)[0] for matrix in gamma_1)
    print(
        "Gamma1 levels: Pauli",
        gamma_1_pauli,
        "Clifford total",
        gamma_1_clifford,
        "C3 total",
        gamma_1_c3,
        "proper C4",
        1024 - gamma_1_c3,
    )
    print("Gamma2 distinct defining generators", len(defining))

    defining_values = list(defining.values())
    clifford = [item for item in defining_values if clifford_test(item[0])[0]]
    non_clifford = [item for item in defining_values if not clifford_test(item[0])[0]]
    print("Gamma2 defining generators: Clifford", len(clifford), "proper C3", len(non_clifford))
    print("Gamma2 defining generators: Pauli", sum(is_pauli(item[0]) for item in defining_values))

    def sparsity(matrix):
        entries = matrix[abs(matrix) > 1e-7]
        return int(np.count_nonzero(abs(matrix) > 1e-7)), tuple(
            sorted(set(np.round(abs(entries), 8)))
        )

    print(
        "Gamma2 defining generator matrix shapes",
        Counter(sparsity(item[0]) for item in defining_values),
    )

    witness_data = None
    for left, right in combinations(range(len(defining_values)), 2):
        product = defining_values[left][0] @ defining_values[right][0]
        is_c3, failed_image = c3_test(product)
        if not is_c3:
            witness_data = defining_values[left], defining_values[right], failed_image, product
            break
    assert witness_data is not None
    (h_1, mask_1, y_1), (h_2, mask_2, y_2), (pauli_index, gamma_3), witness = witness_data
    gamma_3_is_clifford, failed_clifford = clifford_test(gamma_3)
    assert not gamma_3_is_clifford

    def mask_name(mask):
        return " ".join(generator_names[j] for j in range(10) if mask >> j & 1) or "I"

    print("Witness h1: v=", mask_name(mask_1), " y=", generator_names[y_1])
    print("Witness h2: v=", mask_name(mask_2), " y=", generator_names[y_2])
    print("h1 Clifford?", clifford_test(h_1)[0], "h2 Clifford?", clifford_test(h_2)[0])
    print("W=h1 h2 is C3?", c3_test(witness)[0])
    print(
        "W=h1 h2 is C4?",
        all(c3_test(witness @ p @ witness.conj().T)[0] for p in pauli_matrices),
    )
    print(
        "Gamma3 witness K=W",
        generator_names[pauli_index],
        "W^dag is Clifford?",
        gamma_3_is_clifford,
        "is C3?",
        c3_test(gamma_3)[0],
    )

    failed_index, failed_matrix = failed_clifford
    magnitudes = np.abs(failed_matrix[np.abs(failed_matrix) > 1e-7])
    unique, counts = np.unique(np.round(magnitudes, 8), return_counts=True)
    print("K fails Clifford test on", generator_names[failed_index])
    print(
        "nonzero magnitude counts",
        dict(zip(map(float, unique), map(int, counts), strict=True)),
    )

    def signed_permutation_anf(matrix):
        """Return ANFs for a real signed permutation on c,d,x1,x2,x3."""

        if any(np.count_nonzero(abs(matrix[:, column]) > 1e-7) != 1 for column in range(DIMENSION)):
            return None
        outputs = [[0] * DIMENSION for _ in range(5)]
        phases = [0] * DIMENSION
        for mask in range(DIMENSION):
            column = sum(((mask >> q) & 1) << (4 - q) for q in range(5))
            row = int(np.flatnonzero(abs(matrix[:, column]) > 1e-7)[0])
            amplitude = matrix[row, column]
            if abs(abs(amplitude) - 1) > 1e-7 or abs(amplitude.imag) > 1e-7:
                return None
            for q in range(5):
                outputs[q][mask] = bit(row, q)
            phases[mask] = int(amplitude.real < 0)

        def mobius(values):
            coefficients = values[:]
            for q in range(5):
                for mask in range(DIMENSION):
                    if mask >> q & 1:
                        coefficients[mask] ^= coefficients[mask ^ (1 << q)]
            return [mask for mask, value in enumerate(coefficients) if value]

        variable_names = ["c", "d", "x1", "x2", "x3"]

        def format_anf(monomials):
            terms = []
            for monomial in monomials:
                terms.append(
                    "1"
                    if monomial == 0
                    else "*".join(variable_names[q] for q in range(5) if monomial >> q & 1)
                )
            return " + ".join(terms) or "0"

        return [format_anf(mobius(values)) for values in outputs], format_anf(mobius(phases))

    for name, matrix in [
        ("h1", h_1),
        ("h2", h_2),
        ("W", witness),
        ("K", gamma_3),
        ("K_Xc_Kdag", failed_matrix),
    ]:
        print(
            name,
            "projective order",
            projective_order(matrix),
            "signed permutation ANF",
            signed_permutation_anf(matrix),
        )

    orders = {}
    long_pair = None
    for left, right in combinations(range(len(defining_values)), 2):
        order = projective_order(defining_values[left][0] @ defining_values[right][0], 256)
        orders[order] = orders.get(order, 0) + 1
        if order is None:
            long_pair = defining_values[left], defining_values[right]
            break
    print("pair-product orders until first >256:", orders)
    if long_pair:
        print(
            "long-order pair metadata:",
            mask_name(long_pair[0][1]),
            generator_names[long_pair[0][2]],
            ";",
            mask_name(long_pair[1][1]),
            generator_names[long_pair[1][2]],
        )


if __name__ == "__main__":
    main()
