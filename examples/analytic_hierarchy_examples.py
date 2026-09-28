"""Verify one positive and one negative C3 example exactly."""

from clifford_conjugation import analyze_diagonal_c3


def report(name: str, exponents: tuple[int, ...]) -> None:
    analysis = analyze_diagonal_c3(exponents)
    print(
        f"{name}: C2={analysis.is_clifford}, "
        f"C3={analysis.is_in_third_level}, "
        f"X-image Clifford flags={analysis.x_images_are_clifford}"
    )


report("CCZ", (0, 0, 0, 0, 0, 0, 0, 4))
report("controlled-T", (0, 0, 0, 1))
