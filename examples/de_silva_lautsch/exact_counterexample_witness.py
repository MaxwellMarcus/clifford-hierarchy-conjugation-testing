"""Exactly verify the non-Clifford witness found by the numerical search.

This is a cleaned, reproducible version of the original research script. It
uses SymPy matrices so the final identity is symbolic rather than tolerance
based. Install the optional dependency with ``pip install -e '.[exact]'``.
"""

import sympy as sym

NUM_QUBITS = 5
DIMENSION = 32
I2 = sym.eye(2)
X = sym.Matrix([[0, 1], [1, 0]])
H = sym.Matrix([[1, 1], [1, -1]]) / sym.sqrt(2)


def kron(operators: list[sym.Matrix]) -> sym.Matrix:
    result = sym.Matrix([[1]])
    for operator in operators:
        result = sym.kronecker_product(result, operator)
    return result


def one_qubit(operator: sym.Matrix, qubit: int, num_qubits: int = NUM_QUBITS) -> sym.Matrix:
    operators = [I2] * num_qubits
    operators[qubit] = operator
    return kron(operators)


def bit(value: int, qubit: int, num_qubits: int) -> int:
    return (value >> (num_qubits - 1 - qubit)) & 1


def permutation_gate(num_qubits: int, function) -> sym.Matrix:
    result = sym.zeros(1 << num_qubits)
    for column in range(1 << num_qubits):
        result[function(column), column] = 1
    return result


def cx(num_qubits: int, control: int, target: int) -> sym.Matrix:
    return permutation_gate(
        num_qubits,
        lambda value: value ^ (bit(value, control, num_qubits) << (num_qubits - 1 - target)),
    )


def cz(num_qubits: int, qubit_a: int, qubit_b: int) -> sym.Matrix:
    entries = [
        (-1) ** (bit(value, qubit_a, num_qubits) * bit(value, qubit_b, num_qubits))
        for value in range(1 << num_qubits)
    ]
    return sym.diag(*entries)


def controlled(target_gate: sym.Matrix, control: int, targets: list[int]) -> sym.Matrix:
    result = sym.zeros(DIMENSION)
    num_targets = len(targets)
    for column in range(DIMENSION):
        if not bit(column, control, NUM_QUBITS):
            result[column, column] = 1
            continue
        target_column = sum(
            bit(column, qubit, NUM_QUBITS) << (num_targets - 1 - position)
            for position, qubit in enumerate(targets)
        )
        for target_row in range(1 << num_targets):
            amplitude = target_gate[target_row, target_column]
            if amplitude == 0:
                continue
            row = column
            for position, qubit in enumerate(targets):
                desired = (target_row >> (num_targets - 1 - position)) & 1
                if bit(row, qubit, NUM_QUBITS) != desired:
                    row ^= 1 << (NUM_QUBITS - 1 - qubit)
            result[row, column] = amplitude
    return result


def main() -> None:
    target_a = cx(3, 1, 2) * cz(3, 1, 2)
    target_b = cx(3, 1, 2) * cx(3, 0, 1) * one_qubit(H, 0, 3)
    unitary = controlled(target_b, 0, [2, 3, 4]) * controlled(target_a, 1, [2, 3, 4])
    x_c = one_qubit(X, 0)
    x_d = one_qubit(X, 1)
    x_2 = one_qubit(X, 3)

    def conjugate_by_u(pauli: sym.Matrix) -> sym.Matrix:
        return unitary * pauli * unitary.H

    def second_conjugation(v: sym.Matrix, y: sym.Matrix) -> sym.Matrix:
        q_v = conjugate_by_u(v)
        return q_v * y * q_v.H

    h_1 = second_conjugation(x_c, x_c)
    h_2 = second_conjugation(x_c * x_d * x_2, x_c)
    witness = h_1 * h_2
    gamma_3_element = witness * x_c * witness.H
    observed = gamma_3_element * x_c * gamma_3_element.H
    expected = x_c * cx(5, 1, 3) * cx(5, 1, 4)

    assert sym.simplify(observed - expected) == sym.zeros(DIMENSION)
    print("EXACT PASS: K X_c K^dag = X_c CX_(d->2) CX_(d->3)")


if __name__ == "__main__":
    main()
