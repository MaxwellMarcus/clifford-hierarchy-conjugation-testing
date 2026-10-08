"""Audit external controls required before trusted PyPI publication is enabled."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_REPOSITORY = "MaxwellMarcus/clifford-hierarchy-conjugation-testing"
EXPECTED_REVIEWER = "MaxwellMarcus"
EXPECTED_PUBLISHER = {
    "owner": "MaxwellMarcus",
    "repository": "clifford-hierarchy-conjugation-testing",
    "workflow": "release.yml",
    "environment": "pypi",
}


@dataclass(frozen=True)
class PublicationPrerequisiteAudit:
    """Fail-closed result for the GitHub and PyPI publication boundary."""

    environment_exists: bool
    required_reviewers_configured: bool
    v_tag_deployment_policy_configured: bool
    immutable_v_tag_ruleset_configured: bool
    pypi_publisher_confirmed: bool

    @property
    def ready(self) -> bool:
        return all(
            (
                self.environment_exists,
                self.required_reviewers_configured,
                self.v_tag_deployment_policy_configured,
                self.immutable_v_tag_ruleset_configured,
                self.pypi_publisher_confirmed,
            )
        )

    @property
    def failures(self) -> tuple[str, ...]:
        checks = (
            (self.environment_exists, "GitHub environment 'pypi' is missing"),
            (
                self.required_reviewers_configured,
                f"GitHub environment 'pypi' does not require reviewer {EXPECTED_REVIEWER!r}",
            ),
            (
                self.v_tag_deployment_policy_configured,
                "GitHub environment 'pypi' is not restricted to a custom v* tag policy",
            ),
            (
                self.immutable_v_tag_ruleset_configured,
                "no active v* tag ruleset restricts updates and deletions",
            ),
            (
                self.pypi_publisher_confirmed,
                "matching PyPI trusted publisher was not manually confirmed",
            ),
        )
        return tuple(message for passed, message in checks if not passed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "ready": self.ready,
            "checks": asdict(self),
            "failures": list(self.failures),
            "expected_github_reviewer": EXPECTED_REVIEWER,
            "expected_pypi_publisher": EXPECTED_PUBLISHER,
        }


def _has_expected_required_reviewer(environment: dict[str, Any] | None) -> bool:
    if environment is None:
        return False
    for rule in environment.get("protection_rules", []):
        if rule.get("type") != "required_reviewers":
            continue
        for entry in rule.get("reviewers", []):
            reviewer = entry.get("reviewer") or {}
            if entry.get("type") == "User" and reviewer.get("login") == EXPECTED_REVIEWER:
                return True
    return False


def _has_v_tag_deployment_policy(
    environment: dict[str, Any] | None,
    deployment_policies: dict[str, Any] | None,
) -> bool:
    if environment is None or deployment_policies is None:
        return False
    policy = environment.get("deployment_branch_policy") or {}
    if policy.get("protected_branches") or not policy.get("custom_branch_policies"):
        return False
    return any(
        item.get("type") == "tag" and item.get("name") == "v*"
        for item in deployment_policies.get("branch_policies", [])
    )


def _has_immutable_v_tag_ruleset(rulesets: list[dict[str, Any]]) -> bool:
    for ruleset in rulesets:
        if ruleset.get("target") != "tag" or ruleset.get("enforcement") != "active":
            continue
        ref_names = (ruleset.get("conditions") or {}).get("ref_name") or {}
        includes = set(ref_names.get("include", []))
        excludes = set(ref_names.get("exclude", []))
        if not ({"refs/tags/v*", "~ALL"} & includes) or {
            "refs/tags/v*",
            "~ALL",
        } & excludes:
            continue
        rule_types = {rule.get("type") for rule in ruleset.get("rules", [])}
        if {"deletion", "update"} <= rule_types:
            return True
    return False


def audit_publication_prerequisites(
    *,
    environment: dict[str, Any] | None,
    deployment_policies: dict[str, Any] | None,
    rulesets: list[dict[str, Any]],
    pypi_publisher_confirmed: bool,
) -> PublicationPrerequisiteAudit:
    """Return a pure, testable audit of the required external controls."""

    return PublicationPrerequisiteAudit(
        environment_exists=environment is not None,
        required_reviewers_configured=_has_expected_required_reviewer(environment),
        v_tag_deployment_policy_configured=_has_v_tag_deployment_policy(
            environment, deployment_policies
        ),
        immutable_v_tag_ruleset_configured=_has_immutable_v_tag_ruleset(rulesets),
        pypi_publisher_confirmed=pypi_publisher_confirmed,
    )


def _gh_api(endpoint: str, *, allow_not_found: bool = False) -> Any:
    result = subprocess.run(
        ("gh", "api", endpoint),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        if allow_not_found and "HTTP 404" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or f"gh api failed for {endpoint}")
    return json.loads(result.stdout)


def audit_live_repository(
    repository: str,
    *,
    pypi_publisher_confirmed: bool,
) -> PublicationPrerequisiteAudit:
    """Read the current GitHub controls and combine them with PyPI confirmation."""

    base = f"repos/{repository}"
    environment = _gh_api(f"{base}/environments/pypi", allow_not_found=True)
    deployment_policies = None
    if environment is not None:
        deployment_policies = _gh_api(
            f"{base}/environments/pypi/deployment-branch-policies"
        )
    summaries = _gh_api(f"{base}/rulesets")
    rulesets = [_gh_api(f"{base}/rulesets/{item['id']}") for item in summaries]
    return audit_publication_prerequisites(
        environment=environment,
        deployment_policies=deployment_policies,
        rulesets=rulesets,
        pypi_publisher_confirmed=pypi_publisher_confirmed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPOSITORY),
    )
    parser.add_argument(
        "--pypi-publisher-confirmed",
        action="store_true",
        help="assert that an administrator verified the exact publisher tuple on PyPI",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    arguments = parser.parse_args()
    audit = audit_live_repository(
        arguments.repository,
        pypi_publisher_confirmed=arguments.pypi_publisher_confirmed,
    )
    if arguments.as_json:
        print(json.dumps(audit.to_dict(), indent=2, sort_keys=True))
    elif audit.ready:
        print("publication prerequisites verified")
    else:
        print("publication remains blocked:")
        for failure in audit.failures:
            print(f"- {failure}")
        print(f"expected PyPI publisher: {json.dumps(EXPECTED_PUBLISHER, sort_keys=True)}")
    return 0 if audit.ready else 1


if __name__ == "__main__":
    sys.exit(main())
