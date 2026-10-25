"""The dry run's requirement handling, and the pin it reads.

`scripts/extraction_dry_run.py` installs the framework the way CI does, so two
things have to be right before the script is worth running: the requirement it
reads out of `requirements.in` has to be the one this project really depends
on, and the extras it applies have to end up in the right place for both shapes
of requirement a pip install accepts.

Everything here is offline. The formatting is pure string work, and the one
case that touches the network - installing - is what the dry run itself does.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "extraction_dry_run.py"


def _load() -> Any:
    """scripts/ is not a package, so the script is loaded by path."""
    spec = importlib.util.spec_from_file_location("extraction_dry_run", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dry_run = _load()


# --------------------------------------------------------------------------- #
# with_extras: where the extras go
# --------------------------------------------------------------------------- #


def test_a_direct_reference_carries_its_extras_on_the_name():
    """PEP 508 puts extras before the `@`, not after the URL. A requirement
    built the other way round is rejected by pip, so this is the case the
    pinned dependency depends on."""
    requirement = "playwright-pytest-framework @ git+https://example.test/repo@v0.1.0"

    assert dry_run.with_extras(requirement, "ai,report") == (
        "playwright-pytest-framework[ai,report] @ git+https://example.test/repo@v0.1.0"
    )


def test_existing_extras_are_replaced_rather_than_appended():
    """The dry run installs one requirement twice - with the extras and without -
    to show they are load-bearing, so the declared extras must not accumulate."""
    requirement = "playwright-pytest-framework[ai,report] @ git+https://example.test/repo@v0.1.0"

    assert dry_run.with_extras(requirement, "report") == (
        "playwright-pytest-framework[report] @ git+https://example.test/repo@v0.1.0"
    )


def test_a_direct_reference_can_be_stripped_back_to_a_base_install():
    requirement = "playwright-pytest-framework[ai,report] @ git+https://example.test/repo@v0.1.0"

    assert dry_run.with_extras(requirement, "") == (
        "playwright-pytest-framework @ git+https://example.test/repo@v0.1.0"
    )


def test_a_wheel_path_takes_its_extras_appended():
    assert dry_run.with_extras("dist/pkg-0.1.0-py3-none-any.whl", "ai") == (
        "dist/pkg-0.1.0-py3-none-any.whl[ai]"
    )


def test_a_wheel_paths_extras_are_also_replaced():
    assert dry_run.with_extras("dist/pkg-0.1.0-py3-none-any.whl[ai,report]", "") == (
        "dist/pkg-0.1.0-py3-none-any.whl"
    )


@pytest.mark.parametrize(
    "requirement",
    [
        "playwright-pytest-framework @ git+https://example.test/repo@v0.1.0",
        "dist/pkg-0.1.0-py3-none-any.whl",
        "../playwright-pytest-framework",
    ],
)
def test_applying_no_extras_leaves_a_requirement_alone(requirement):
    assert dry_run.with_extras(requirement, "") == requirement


# --------------------------------------------------------------------------- #
# declared_framework_requirement: the pin itself
# --------------------------------------------------------------------------- #


def test_the_declared_requirement_is_this_projects_own_pin():
    """Read from requirements.in, not reconstructed: the dry run has to install
    what CI installs or it proves nothing about the switchover."""
    requirement = dry_run.declared_framework_requirement()

    assert requirement.startswith("playwright-pytest-framework")
    assert " @ " in requirement, requirement
    assert requirement in REPO_ROOT.joinpath("requirements.in").read_text(encoding="utf-8")


def test_the_framework_is_pinned_to_an_immutable_ref():
    """A branch would make every install a different framework. The pin is a
    tag (or a commit), and this fails if someone points it at a moving target."""
    _, _, url = dry_run.declared_framework_requirement().partition(" @ ")
    assert url.startswith("git+https://"), url
    _, _, ref = url.rpartition("@")
    assert ref, f"no ref in {url!r} - the requirement tracks a default branch"
    assert ref.startswith("v") or (
        len(ref) == 40 and all(c in "0123456789abcdef" for c in ref)
    ), f"{ref!r} is neither a version tag nor a commit sha"


def test_the_declared_extras_are_the_ones_the_project_needs():
    """`report` makes pytest.ini's --html work at all; `ai` brings the catalog
    validator's dependencies, which is what lets the catalog tests run instead
    of skipping."""
    requirement = dry_run.declared_framework_requirement()
    name, _, _ = requirement.partition(" @ ")

    assert "[" in name, f"{name!r} declares no extras"
    extras = set(name[name.index("[") + 1 : name.rindex("]")].split(","))
    assert {"ai", "report"} <= extras, extras


def test_a_missing_requirement_fails_loudly(tmp_path, monkeypatch):
    """Silently installing nothing, or something assembled here, would make the
    dry run a test of itself."""
    empty = tmp_path / "requirements.in"
    empty.write_text("# only comments\npytest-xdist>=3.0.0\n", encoding="utf-8")
    monkeypatch.setattr(dry_run, "REQUIREMENTS_IN", empty)

    with pytest.raises(SystemExit) as exit_info:
        dry_run.declared_framework_requirement()

    assert "playwright-pytest-framework" in str(exit_info.value)
    assert "--framework" in str(exit_info.value)


def test_comments_and_continuations_do_not_confuse_the_parser(tmp_path, monkeypatch):
    source = tmp_path / "requirements.in"
    source.write_text(
        "# playwright-pytest-framework used to be vendored here\n"
        "pytest-xdist>=3.0.0\n"
        "playwright-pytest-framework[ai] @ git+https://example.test/r@v9.9.9  # the pin\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dry_run, "REQUIREMENTS_IN", source)

    assert dry_run.declared_framework_requirement() == (
        "playwright-pytest-framework[ai] @ git+https://example.test/r@v9.9.9"
    )


def test_the_script_is_runnable_as_a_script():
    """It is documented as `python scripts/extraction_dry_run.py`, so it must
    stay executable that way rather than becoming an importable module only."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in source
    assert "main()" in source.rsplit('if __name__ == "__main__":', 1)[1]
