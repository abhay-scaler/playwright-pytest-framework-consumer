"""This repository's catalog, and the policy that keeps a live site out of CI.

The validator's own rule behaviour - 20 cases that build a throwaway
repository under `tmp_path` and assert which rule codes come back - is the
framework's, and moved to its repository with
`pwpf/ai_testing/validate_catalog.py` at extraction. What stays here are the
two assertions that are about *this* project:

- the committed catalog is valid, which the Scenario Catalog CI job also
  covers; and
- no committed scenario lets a live production site gate CI, which the job
  does **not** cover. That one is consumer policy and the reason this file did
  not move wholesale.

Both read the catalog read-only: no browser, no network.
"""

from __future__ import annotations

import pytest
from pwpf.ai_testing.validate_catalog import discover_catalogs, validate_catalog
from pwpf.config.paths import project_root

yaml = pytest.importorskip("yaml", reason="the framework's [ai] extra is not installed")


def _messages(findings) -> str:
    return "\n".join(str(finding) for finding in findings)


def test_the_committed_catalog_is_valid():
    findings = validate_catalog(project_root())
    assert findings == [], _messages(findings)
    assert discover_catalogs(project_root()), "no catalog files were discovered"


def test_no_committed_scenario_lets_a_live_site_gate_ci():
    """The catalog-side half of the production-exclusion policy. The CI half -
    that every pytest invocation carries -m "not production" - is checked by
    tests/test_ci_production_exclusion.py, which this does not duplicate."""
    for path in discover_catalogs(project_root()):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        for scenario in document["scenarios"]:
            environment = scenario["environment"]
            if environment["target"] == "live-production":
                assert environment["ci_eligible"] is False, scenario["id"]
                assert scenario["status"] != "ACTIVE_REGRESSION", scenario["id"]
                assert "production" in scenario["automation"]["markers"], scenario["id"]
