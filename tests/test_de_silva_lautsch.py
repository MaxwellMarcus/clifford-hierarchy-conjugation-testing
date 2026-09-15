from clifford_conjugation import verify_counterexample


def test_exact_counterexample_regression() -> None:
    result = verify_counterexample()

    assert result["target_lagrangians"] == 135
    assert result["A_invariant_lagrangians"] == 15
    assert result["B_invariant_lagrangians"] == 1
    assert result["common_invariant_lagrangians"] == 0
    assert result["B_minus_I_nilpotency_index"] == 6
    assert result["B_fourth_power_is_identity"] is False
    assert result["relative_minus_I_nilpotency_indices"] == {
        "(0, 0)": 1,
        "(0, 1)": 2,
        "(1, 0)": 3,
        "(1, 1)": 3,
    }


def test_all_claim_checks_pass() -> None:
    result = verify_counterexample()
    claim_results = {
        key: value
        for key, value in result.items()
        if key.endswith("obstruction") or key.endswith("hypotheses")
    }

    assert claim_results
    assert set(claim_results.values()) == {"PASS"}
