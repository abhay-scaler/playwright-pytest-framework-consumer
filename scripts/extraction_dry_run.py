"""Prove *this* repository can use the framework as an installed dependency.

`verify_installed_package.py` answers a narrower question: does the wheel
install and work for a *synthetic* consumer it generates itself. This script
asks the question the extraction actually turns on - can the real consumer code
in this repository, `apps/` and `tests/<app>/`, run against the installed
distribution, with no framework source anywhere in sight?

    python scripts/extraction_dry_run.py [--keep]
    python scripts/extraction_dry_run.py --framework dist/pwpf-0.1.0-py3-none-any.whl

By default it installs **the requirement this repository actually depends on**,
read out of `requirements.in` - the framework's own repository at a pinned tag -
so what the dry run exercises is the pin CI installs rather than something
built on the side. `--framework` overrides it with any pip requirement: a local
wheel, an editable checkout, another tag. Before extraction this script built a
wheel from `pwpf/` in this repository; there is no `pwpf/` here to build now,
which is the whole point.

It then copies the consumer-owned half of this repository into a temporary
project and runs it from there. Plugin discovery has to come from the
`pytest11` entry point, and `import pwpf` has to resolve to the environment's
site-packages or the run is a failure, not a pass - checked inside the consumer
process, from its own working directory, because `''` on `sys.path` means a
module can be imported from the current directory and look installed.

Exit status is 0 when every check passes and 1 otherwise; each check prints its
own line. Nothing in the repository is modified: the only writes are to a
temporary directory.

It also tests the *dependency contract*, not just the code: the consumer
environment is built from the distribution's own extras (`[ai,report]`) plus the
one dependency that is genuinely the consumer's (`pytest-xdist`, for `-n auto`),
and a second, base-only environment proves the extras are load-bearing by being
rejected by this repository's `pytest.ini`. The extras are applied to whatever
requirement is in use, so the base-only environment is the same artifact
without them.

What it deliberately does not do: publish anything, create a repository, change
where this project gets its framework from, or run the live-site `production`
tests. The selection expressions are the repository's own, exclusions included.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The consumer-owned half of this repository: application packages, their
# per-application test suites, and the pytest configuration that selects them.
# Everything else - pwpf/, the root conftest.py, tests/test_*.py, scripts/,
# docs/, ai_testing/, pyproject.toml - belongs to the framework or to the
# repository itself and is deliberately left out, so the copy can only work if
# the installed distribution supplies the framework.
CONSUMER_TREES = ("apps",)
CONSUMER_TEST_SUITES = (
    "api",
    "myntra",
    "sample_app",
    "tmp",
    "uitesting_playground",
    "web_search",
)
CONSUMER_FILES = ("pytest.ini",)

# The dependency contract, installed as a consumer would read it off the
# distribution rather than as a hand-written list:
#
#   framework extras   `[ai]` for the catalog validator, `[report]` for the
#                      pytest-html integration this repository's pytest.ini
#                      asks for with `--html`.
#   consumer's own     pytest-xdist. Nothing in pwpf/ requires it, so running
#                      `-n auto` is this project's choice and this project's
#                      dependency - which is exactly why it is listed here and
#                      not pulled from an extra.
FRAMEWORK_EXTRAS = "ai,report"
CONSUMER_OWNED_DEPENDENCIES = ("pytest-xdist",)

# The selections the repository's CI relies on, as a portability check: they
# must come out the same in a project that only has the installed plugin.
EXPECTED_SELECTIONS = {
    "production": 1,
    "quarantined": 0,
    "smoke and not production and not quarantined": 4,
}

ARTIFACT_DIRS = ("reports", "screenshots", "logs", "traces", "videos")

INSTALL_TIMEOUT = 600
CONSUMER_TIMEOUT = 600

results: list[tuple[bool, str]] = []


def check(ok: bool, description: str, detail: str = "") -> bool:
    results.append((ok, description))
    print(f"  [{'PASS' if ok else 'FAIL'}] {description}")
    if detail and not ok:
        for line in detail.strip().splitlines()[:20]:
            print(f"         {line}")
    return ok


def run(
    argv: list[str], cwd: Path, env: dict[str, str], timeout: int = CONSUMER_TIMEOUT
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as expired:
        return subprocess.CompletedProcess(
            argv,
            returncode=124,
            stdout=expired.stdout or "",
            stderr=f"timed out after {timeout}s: {' '.join(str(a) for a in argv)}",
        )


DISTRIBUTION = "playwright-pytest-framework"
REQUIREMENTS_IN = REPO_ROOT / "requirements.in"


def declared_framework_requirement() -> str:
    """The framework requirement as `requirements.in` declares it.

    Read rather than reconstructed: a dry run that installed a requirement
    assembled here would prove something about this script instead of about
    what CI installs. Continuation lines are joined, comments ignored.
    """
    text = REQUIREMENTS_IN.read_text(encoding="utf-8")
    for raw in text.replace("\\\n", " ").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line.lower().startswith(DISTRIBUTION):
            return line
    raise SystemExit(
        f"no {DISTRIBUTION} requirement found in {REQUIREMENTS_IN}. "
        "This project depends on the framework as an installed distribution; "
        "declare it there, or pass --framework."
    )


def with_extras(requirement: str, extras: str) -> str:
    """`requirement` carrying exactly `extras` - none when it is empty.

    Two shapes have to work. A PEP 508 direct reference puts the extras on the
    *name*, before the `@`: `pkg[ai,report] @ git+https://...@v0.1.0`. A plain
    path or wheel takes them appended: `dist/pkg-0.1.0.whl[ai,report]`.
    Whatever extras the requirement already carries are replaced, which is what
    lets one requirement be installed twice - once with the extras and once
    without - to show they are load-bearing.
    """
    suffix = f"[{extras}]" if extras else ""
    if " @ " in requirement:
        name, _, url = requirement.partition(" @ ")
        name = name.split("[", 1)[0].strip()
        return f"{name}{suffix} @ {url.strip()}"
    base = str(requirement)
    if base.endswith("]") and "[" in base:
        base = base[: base.rindex("[")]
    return f"{base}{suffix}"


def make_venv(
    workdir: Path,
    framework: str,
    *,
    name: str = "venv",
    extras: str = FRAMEWORK_EXTRAS,
    consumer_dependencies: tuple[str, ...] = CONSUMER_OWNED_DEPENDENCIES,
) -> Path:
    """A clean environment with the distribution installed exactly as the
    documented contract says to install it. `extras=""` gives the base install,
    which is how the contract gets tested rather than assumed."""
    venv_dir = workdir / name
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)], check=True, timeout=INSTALL_TIMEOUT
    )
    python = venv_dir / "bin" / "python"
    requirement = with_extras(framework, extras)
    proc = subprocess.run(
        [str(python), "-m", "pip", "install", "--quiet", requirement] + list(consumer_dependencies),
        capture_output=True,
        text=True,
        timeout=INSTALL_TIMEOUT,
    )
    if proc.returncode != 0:
        raise SystemExit(f"install failed ({requirement}):\n{proc.stdout}\n{proc.stderr}")
    return venv_dir


def make_consumer(workdir: Path) -> Path:
    """This repository's consumer half, copied - never moved - into a project of
    its own."""
    consumer = workdir / "consumer"
    consumer.mkdir()
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for tree in CONSUMER_TREES:
        shutil.copytree(REPO_ROOT / tree, consumer / tree, ignore=ignore)
    (consumer / "tests").mkdir()
    for suite in CONSUMER_TEST_SUITES:
        source = REPO_ROOT / "tests" / suite
        if source.is_dir():
            shutil.copytree(source, consumer / "tests" / suite, ignore=ignore)
    for name in CONSUMER_FILES:
        shutil.copy2(REPO_ROOT / name, consumer / name)
    return consumer


def consumer_env(venv_dir: Path) -> dict[str, str]:
    """A deliberately bare environment. PYTHONPATH is dropped rather than
    emptied, and PWPF_ROOT and ENVIRONMENT are dropped so a CI run of this
    script cannot hand the consumer the parent's project root or environment
    selection."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONPATH", "PWPF_ROOT", "ENVIRONMENT", "VIRTUAL_ENV"}
    }
    env["PATH"] = f"{venv_dir / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["CI"] = "true"
    env["HEADLESS"] = "true"
    return env


def artifact_dirs(root: Path) -> set[str]:
    return {d for d in ARTIFACT_DIRS if (root / d).is_dir()}


def counts(output: str) -> dict[str, int]:
    """pytest's own tallies, from its summary line."""
    found: dict[str, int] = {}
    for number, label in re.findall(
        r"(\d+) (passed|failed|skipped|error|errors|deselected)", output
    ):
        found[label.rstrip("s")] = int(number)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="keep the temporary workspace")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="skip installing Chromium into the throwaway environment; the smoke selection "
        "then only collects, and the run says so instead of claiming it executed",
    )
    parser.add_argument(
        "--framework",
        metavar="REQUIREMENT",
        default=None,
        help="the framework requirement to install: a pinned reference, a local wheel, an "
        "editable path. Defaults to the one requirements.in declares, which is what CI installs.",
    )
    args = parser.parse_args(argv)

    framework = args.framework or declared_framework_requirement()
    workdir = Path(tempfile.mkdtemp(prefix="pwpf-extraction-dry-run-"))
    print(f"workspace: {workdir}")
    print(f"framework: {framework}")
    try:
        venv_dir = make_venv(workdir, framework)
        python = venv_dir / "bin" / "python"
        consumer = make_consumer(workdir)
        site_packages = next((venv_dir / "lib").glob("python*/site-packages"))
        env = consumer_env(venv_dir)
        print(f"consumer:  {consumer}")

        # The installed Playwright decides its own browser build, and whatever
        # this machine has cached was installed for a different version. Without
        # this the browser fixture skips - honest, but it proves nothing about
        # execution - so Chromium is installed for the version actually
        # resolved. Exactly what a consumer's CI has to do.
        browsers = not args.no_browser
        if browsers:
            proc = run(
                [str(python), "-m", "playwright", "install", "chromium"],
                consumer,
                env,
                timeout=INSTALL_TIMEOUT,
            )
            browsers = proc.returncode == 0
            print(f"browser:   {'chromium installed' if browsers else 'install failed'}")

        print("\nchecks:")

        # 1. The consumer project holds no framework code at all. Since
        #    extraction this project has none to copy, so the check has gone
        #    from "the copy left it out" to "there is none anywhere" - stronger,
        #    and worth keeping for the day someone vendors a copy back in.
        check(
            not (consumer / "pwpf").exists() and not (consumer / "conftest.py").exists(),
            "the consumer project contains no pwpf/ and no root conftest.py",
            str(sorted(p.name for p in consumer.iterdir())),
        )
        check(
            not list(consumer.rglob("test_project_root.py")),
            "the framework's own self-tests were not copied into the consumer",
        )

        # 2. Imports resolve to the installed distribution, and the checkout is
        #    not reachable from the consumer process at all.
        proc = run(
            [
                str(python),
                "-c",
                "import json, sys, pwpf;"
                "print(json.dumps({'file': pwpf.__file__, 'path': sys.path}))",
            ],
            consumer,
            env,
        )
        payload = json.loads(proc.stdout or "{}") if proc.returncode == 0 else {}
        imported_from = payload.get("file", "")
        check(
            proc.returncode == 0 and imported_from.startswith(str(site_packages)),
            "pwpf is imported from the installed distribution, not from this project",
            f"{imported_from}\n{proc.stderr}",
        )
        # `''` on sys.path means the consumer's own working directory can shadow
        # an installed package, so this checks for *this project* on the path -
        # before extraction it held pwpf/ and that was the whole risk; it no
        # longer does, and a copy appearing there would be just as wrong.
        on_path = [p for p in payload.get("path", []) if p and Path(p).resolve() == REPO_ROOT]
        check(
            not on_path and "PYTHONPATH" not in env,
            "this project is on neither sys.path nor PYTHONPATH in the consumer",
            f"sys.path entries matching this project: {on_path}",
        )

        # 3. The plugin arrives through its entry point, markers included.
        proc = run([str(python), "-m", "pytest", "--markers"], consumer, env)
        expected_markers = ("app(name)", "scenario(id)", "production", "quarantined", "smoke")
        missing = [m for m in expected_markers if f"@pytest.mark.{m}" not in proc.stdout]
        check(
            proc.returncode == 0 and not missing,
            "the plugin's markers are registered with no consumer conftest.py",
            f"missing: {missing}\n{proc.stdout[-400:]}{proc.stderr}",
        )
        proc = run([str(python), "-m", "pytest", "--fixtures", "-q"], consumer, env)
        check(
            all(name in proc.stdout for name in ("page", "context", "browser", "app_config")),
            "the plugin's fixture chain is available to the consumer's tests",
            proc.stdout[-400:] + proc.stderr,
        )

        # 4. The selections this repository's CI depends on are unchanged in a
        #    project that only has the installed plugin.
        for expression, expected in EXPECTED_SELECTIONS.items():
            proc = run(
                [str(python), "-m", "pytest", "--collect-only", "-q", "-m", expression],
                consumer,
                env,
            )
            collected = counts(proc.stdout)
            got = (
                0
                if "no tests collected" in proc.stdout
                else int(next(iter(re.findall(r"(\d+)/\d+ tests collected", proc.stdout)), 0))
            )
            check(
                got == expected,
                f'selection -m "{expression}" collects {expected}',
                f"got {got} ({collected})\n{proc.stdout[-300:]}{proc.stderr}",
            )

        # 5. The blocking smoke selection actually runs, against the installed
        #    plugin, with the live-site tests excluded exactly as CI excludes
        #    them.
        #
        #    Through the `pytest` console script, not `python -m pytest`, and
        #    the difference is not cosmetic: `-m` puts the working directory on
        #    sys.path, so a consumer whose own packages are only importable
        #    *because* of that passes here and fails in CI, which runs the
        #    script. This check is the one that has to reproduce CI exactly.
        before_package = artifact_dirs(site_packages / "pwpf") | artifact_dirs(site_packages)
        before_checkout = artifact_dirs(REPO_ROOT)
        proc = run(
            [
                str(venv_dir / "bin" / "pytest"),
                "-m",
                "smoke and not production and not quarantined",
                "-p",
                "no:cacheprovider",
            ],
            consumer,
            env,
        )
        tally = counts(proc.stdout)
        clean = proc.returncode == 0 and not tally.get("failed") and not tally.get("error")
        if browsers:
            check(
                clean and tally.get("passed", 0) >= 1,
                "the consumer's blocking smoke selection runs and passes against the "
                "installed plugin",
                f"{tally}\n{proc.stdout[-1500:]}{proc.stderr}",
            )
        else:
            check(
                clean,
                "the consumer's blocking smoke selection collects cleanly "
                "(not executed: no browser installed)",
                f"{tally}\n{proc.stdout[-1500:]}{proc.stderr}",
            )
        print(f"         (smoke tally: {tally or 'no summary parsed'})")

        # 6. Application configuration comes from the consumer project.
        proc = run(
            [
                str(python),
                "-c",
                "from pwpf.core.app_config import apps_dir, load_app_config;"
                "c = load_app_config('sample_app');"
                "print(apps_dir()); print(c.base_url)",
            ],
            consumer,
            env,
            timeout=120,
        )
        resolved_apps_dir = proc.stdout.splitlines()[0] if proc.stdout else ""
        expected_url = json.loads(
            (consumer / "apps" / "sample_app" / "config" / "local.json").read_text("utf-8")
        )["base_url"]
        check(
            proc.returncode == 0
            and Path(resolved_apps_dir).resolve() == (consumer / "apps").resolve()
            and expected_url in proc.stdout,
            "application config is resolved from the consumer's own apps/",
            f"{proc.stdout}\n{proc.stderr}",
        )

        # 7. Artifacts land in the consumer project, and nowhere else.
        check(
            {"reports", "logs"} <= artifact_dirs(consumer),
            "artifacts are written under the consumer project root",
            str(sorted(artifact_dirs(consumer))),
        )
        allure_results = sorted((consumer / "reports" / "allure-results").glob("*-result.json"))
        check(
            bool(allure_results),
            "Allure results are written to the consumer's reports/allure-results",
            str(consumer / "reports" / "allure-results"),
        )
        check(
            artifact_dirs(site_packages / "pwpf") | artifact_dirs(site_packages) == before_package,
            "no artifacts are written into the installed package",
            str(sorted(artifact_dirs(site_packages / "pwpf"))),
        )
        # Only the half that can still fail. The other half compared
        # `artifact_dirs(REPO_ROOT / "pwpf")` to the empty set, which a missing
        # directory satisfies for free now that the framework lives elsewhere -
        # a check that cannot fail reads like coverage it is not.
        check(
            artifact_dirs(REPO_ROOT) == before_checkout,
            "no artifacts appeared in this project while the consumer ran",
            str(sorted(artifact_dirs(REPO_ROOT) - before_checkout)),
        )

        # 8. The AI toolkit's validator, run as a consumer would run it: over the
        #    consumer's own catalogs, with the consumer's pytest.ini and tests.
        cli = venv_dir / "bin" / "pwpf-validate-catalog"
        proc = run([str(cli)], consumer, env, timeout=120)
        catalogs = sorted((consumer / "apps").glob("*/scenarios/*.yaml"))
        check(
            proc.returncode == 0
            and f"{len(catalogs)} file(s) checked under {consumer.resolve()}" in proc.stdout,
            "scenario-catalog validation passes in the consumer context",
            f"expected {len(catalogs)} catalog file(s)\n{proc.stdout}\n{proc.stderr}",
        )

        # 9. The dependency contract itself: the extras are not decoration. A
        #    base install of the same distribution, running the same consumer
        #    project, must fail on the `--html` its pytest.ini asks for - which
        #    is what makes `[report]` a contract rather than a suggestion.
        check(
            (consumer / "reports" / "pytest_report.html").is_file(),
            "the pytest-html integration engaged under the [report] extra",
            str(sorted(p.name for p in (consumer / "reports").iterdir())),
        )
        base_venv = make_venv(
            workdir, framework, name="venv-base", extras="", consumer_dependencies=()
        )
        proc = run(
            [str(base_venv / "bin" / "python"), "-m", "pytest", "--collect-only", "-q"],
            consumer,
            consumer_env(base_venv),
            timeout=180,
        )
        output = proc.stdout + proc.stderr
        check(
            proc.returncode == 4 and "--html" in output and "unrecognized arguments" in output,
            "a base install (no extras) is rejected by this consumer's pytest.ini, as documented",
            f"returncode {proc.returncode}\n{output[-500:]}",
        )

        failed = [description for ok, description in results if not ok]
        print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
        if failed:
            for description in failed:
                print(f"  failed: {description}")
            return 1
        return 0
    finally:
        if args.keep:
            print(f"\nkept workspace: {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
