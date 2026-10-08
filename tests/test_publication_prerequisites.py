from __future__ import annotations

import runpy
from pathlib import Path

module = runpy.run_path(
    str(Path(__file__).parents[1] / "tools" / "check_publication_prerequisites.py")
)
audit_publication_prerequisites = module["audit_publication_prerequisites"]


def _protected_environment() -> dict[str, object]:
    return {
        "name": "pypi",
        "protection_rules": [
            {
                "type": "required_reviewers",
                "reviewers": [{"type": "User", "reviewer": {"login": "MaxwellMarcus"}}],
            },
            {"type": "branch_policy"},
        ],
        "deployment_branch_policy": {
            "protected_branches": False,
            "custom_branch_policies": True,
        },
    }


def _v_tag_policy() -> dict[str, object]:
    return {
        "branch_policies": [
            {"id": 1, "name": "v*", "type": "tag"},
        ]
    }


def _immutable_tag_ruleset() -> dict[str, object]:
    return {
        "target": "tag",
        "enforcement": "active",
        "conditions": {
            "ref_name": {"include": ["refs/tags/v*"], "exclude": []},
        },
        "rules": [{"type": "deletion"}, {"type": "update"}],
    }


def test_complete_external_configuration_is_ready() -> None:
    audit = audit_publication_prerequisites(
        environment=_protected_environment(),
        deployment_policies=_v_tag_policy(),
        rulesets=[_immutable_tag_ruleset()],
        pypi_publisher_confirmed=True,
    )

    assert audit.ready
    assert audit.failures == ()
    assert audit.to_dict()["schema_version"] == 1


def test_missing_external_configuration_fails_closed() -> None:
    audit = audit_publication_prerequisites(
        environment=None,
        deployment_policies=None,
        rulesets=[],
        pypi_publisher_confirmed=False,
    )

    assert not audit.ready
    assert len(audit.failures) == 5


def test_environment_requires_reviewers_and_exact_v_tag_policy() -> None:
    environment = _protected_environment()
    environment["protection_rules"] = [{"type": "branch_policy"}]
    deployment_policies = _v_tag_policy()
    deployment_policies["branch_policies"] = [
        {"id": 1, "name": "release/*", "type": "branch"}
    ]

    audit = audit_publication_prerequisites(
        environment=environment,
        deployment_policies=deployment_policies,
        rulesets=[_immutable_tag_ruleset()],
        pypi_publisher_confirmed=True,
    )

    assert not audit.required_reviewers_configured
    assert not audit.v_tag_deployment_policy_configured
    assert audit.immutable_v_tag_ruleset_configured


def test_environment_requires_the_expected_reviewer_identity() -> None:
    environment = _protected_environment()
    environment["protection_rules"][0]["reviewers"] = [
        {"type": "User", "reviewer": {"login": "different-maintainer"}}
    ]

    audit = audit_publication_prerequisites(
        environment=environment,
        deployment_policies=_v_tag_policy(),
        rulesets=[_immutable_tag_ruleset()],
        pypi_publisher_confirmed=True,
    )

    assert not audit.required_reviewers_configured
    assert not audit.ready
    assert "MaxwellMarcus" in audit.failures[0]


def test_tag_ruleset_must_be_active_and_immutable() -> None:
    ruleset = _immutable_tag_ruleset()
    ruleset["enforcement"] = "evaluate"
    ruleset["rules"] = [{"type": "deletion"}]

    audit = audit_publication_prerequisites(
        environment=_protected_environment(),
        deployment_policies=_v_tag_policy(),
        rulesets=[ruleset],
        pypi_publisher_confirmed=True,
    )

    assert not audit.immutable_v_tag_ruleset_configured
    assert not audit.ready
