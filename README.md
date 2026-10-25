# Playwright + Pytest Test Automation Framework

A multi-application UI and API test automation framework built with **Playwright** and
**Pytest**. It supports several independent applications under test from one shared codebase —
each application owns its own configuration, page objects, and locators, while a common framework
layer handles browser lifecycle, failure diagnostics, logging, and reporting without knowing
anything about any specific application.

The project currently automates three sample applications end-to-end (a static local HTML form,
a real documentation-search widget, and a multi-page public demo site) plus one API test against
a public REST API, as a working demonstration of the architecture — not because the framework is
limited to three apps. Onboarding a new application is an additive process (see
[Adding a New Application](DESIGN.md#adding-a-new-application)) that requires no changes to
existing application code or to the framework layer; this was proven in practice when the third
sample app was added with zero edits to the other two.

The framework layer itself is no longer in this repository. It is a separate, installable
distribution — [playwright-pytest-framework](https://github.com/abhay-scaler/playwright-pytest-framework) — pinned to an immutable tag in
`requirements.in` and installed like any other dependency. What lives here is everything that is
about *these* applications: their configuration, page objects, locators, tests, scenario catalog
and CI policy.

## Table of Contents

- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [Reporting and Failure Diagnostics](#reporting-and-failure-diagnostics)
- [Architecture and Fixture Strategy](#architecture-and-fixture-strategy)
- [Code Quality](#code-quality)
- [Continuous Integration](#continuous-integration)
- [Local-Only Overrides](#local-only-overrides)
- [Troubleshooting](#troubleshooting)
- [Known Limitations](#known-limitations)

## Key Features

What this project is, and where each piece comes from. Items marked *framework* arrive with the
installed distribution and are documented in [its README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md); the rest is this
repository's.

- **Multi-application architecture** — `apps/<app_name>/` owns its own configuration, page
  objects, and locators, and a matching `tests/<app_name>/` owns its tests. The framework infers
  which application a test belongs to from that pairing and never holds a list of names.
- **Page Object Model** with a thin shared `BasePage` (*framework*) — page objects expose actions
  and locators only; assertions stay in the tests.
- **API testing with no second HTTP client** (*framework*) — `pwpf.core.api_client` wraps
  Playwright's own `APIRequestContext`, so API tests share the UI tests' driver instead of adding
  `requests`. No browser is launched for them.
- **Automatic failure diagnostics** (*framework*) — a screenshot, the full Playwright trace and a
  video on UI-test failure, namespaced per application, all discarded on success.
- **Passive browser error capture** (*framework*) — console errors and uncaught page exceptions
  are logged and never change a test's outcome.
- **Worker-aware logging** (*framework*) — one log file per `pytest-xdist` worker.
- **Allure reporting** (*framework*) — `application`, `browser` and `environment` labels on every
  test, plus `scenario(id)` labels from the catalog, with the previous run's stale results
  cleared at session start.
- **No hard waits and no fragile selectors** — zero `time.sleep()` anywhere; all waits are
  Playwright's own auto-retrying locators. Locator strategy is chosen deliberately per
  application rather than one default applied everywhere.
- **An approved scenario catalog** — `apps/*/scenarios/*.yaml`, validated in CI against the
  framework's JSON Schema, with traceability from scenario to test enforced by the validator.
- **Policy enforced by tests, not by convention** — `tests/test_ci_production_exclusion.py` fails
  if any CI invocation loses `-m "not production"`, and `tests/test_quarantine_policy.py` pins
  which tests are quarantined. A marker is a label; what the command selects is what runs.
- **A pinned framework** — the dependency names a tag, not a branch, so every install of this
  project gets the same framework. `tests/test_extraction_dry_run.py` fails if that stops being
  true.
- **Dependency locking** — `requirements.in` (loose, human-maintained) compiles to a
  fully-pinned `requirements.txt`.
- **Static analysis and secret scanning** — Ruff, Black and mypy in pre-commit and CI;
  `detect-secrets` as a pre-commit guardrail behind the framework's secrets-by-reference
  convention (see [Configuration](#configuration)).
- **CI/CD** — a six-job GitHub Actions pipeline with pip and the Playwright browser binary cached.

## Technology Stack

The **Owner** column says who declares each tool: the framework distribution, in its own
`pyproject.toml`, or this project, in `requirements.in`, `pytest.ini` and
`.pre-commit-config.yaml`. That boundary is now a repository boundary — everything marked
*framework* arrives through one pinned dependency and is not declared here at all.

| Category | Tool | Owner |
|---|---|---|
| Browser automation | [Playwright](https://playwright.dev/python/) (sync API) — Chromium, Firefox, WebKit | framework |
| Test runner | [Pytest](https://docs.pytest.org/) | framework |
| Retries | [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures) | framework — the plugin applies `flaky` when an app sets `retry_count` |
| Test reporting | [Allure](https://allurereport.org/) (`allure-pytest`) | framework |
| HTML reporting | [pytest-html](https://pytest-html.readthedocs.io/) | framework, optional — the `[report]` extra, for the failure-screenshot embedding |
| API testing | Playwright's own `APIRequestContext` (no separate HTTP client) | framework |
| Parallel execution | [pytest-xdist](https://pytest-xdist.readthedocs.io/) | **consumer** — nothing in `pwpf/` needs it; `-n auto` is a choice about how a suite is run |
| Linting | [Ruff](https://docs.astral.sh/ruff/) | both — each repository lints its own code |
| Formatting | [Black](https://black.readthedocs.io/) | both |
| Static typing | [mypy](https://mypy-lang.org/) (incremental, non-strict) | both |
| Secret scanning | [detect-secrets](https://github.com/Yelp/detect-secrets) | consumer — this repository's pre-commit hook |
| CI/CD | GitHub Actions | both — [the six jobs here](#continuous-integration), three more in the framework's own repository |
| Language / runtime | Python 3.12 | this project pins one interpreter; the framework declares `requires-python = ">=3.12"` and tests 3.12 and 3.13 |

## Project Structure

One tree now: this project. The framework is a dependency, and its source lives in
[its own repository](https://github.com/abhay-scaler/playwright-pytest-framework).

```
apps/<app_name>/            # everything specific to one application
  config/{local,ci}.json     #   base_url, timeouts, retry policy, secret references
  pages/                     #   page objects — actions and state queries only, no assertions
  locators/                  #   selectors as plain data, isolated from page-object logic
  testdata/                  #   static fixtures, where an app needs one
  scenarios/                 #   approved scenario catalog (YAML), validated in CI

tests/
  <app_name>/{smoke,ui}/      # tests owned by one application
    conftest.py                #   binds the app_config fixture to this app's name
  api/                         # application-agnostic API tests
  tmp/                         # a deliberately skipped manual-only diagnostic check
  test_ci_production_exclusion.py   # the production-exclusion policy guard
  test_quarantine_policy.py         # which tests are quarantined, and that they gate nothing
  test_scenario_catalog.py          # this repository's catalog, and the live-site policy
  test_doc_links.py                 # the documentation link and fragment gate
  test_extraction_dry_run.py        # the framework pin, and the dry run's requirement handling

pytest.ini                    # test discovery, markers, default CLI options
pyproject.toml                # Ruff / Black / mypy configuration only — no packaging here
requirements.in / .txt        # loose source and fully-pinned lock, including the framework pin
requirements-ai.in / .txt     # the framework's `ai` extra, for the catalog job alone
.github/workflows/ci.yml      # the six CI jobs
DESIGN.md                     # this project's architecture, CI policy and onboarding walkthrough
docs/                         # this repository's documentation, incl. the AI-testing workflow
ai_testing/                   # its prompt library and templates (no code, no dependencies)
scripts/extraction_dry_run.py # proves this project runs against the pinned framework
scripts/check_doc_links.py    # the documentation link and fragment gate
```

There is **no `conftest.py` at the root**, and that is the point: pytest discovers the framework's
plugin through its `pytest11` entry point, so the fixtures, markers and artifact handling arrive
from the installed distribution with nothing to wire up here.

Generated at runtime (all git-ignored): `reports/` (HTML + Allure results), `screenshots/`,
`traces/`, `videos/` (failure artifacts, namespaced per application), `logs/` (per-worker log
files). They are created when something is actually written, under the **project root** — not
under the installed package's directory, and never as a side effect of importing a module. Under
pytest the root is pytest's own `rootdir`; elsewhere set `PWPF_ROOT`, pass `--root` where a
command supports it, or run from a directory at or below the one holding `pytest.ini`. The full
precedence is in [the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md).

## Prerequisites

- **Python 3.12** — what this project pins, in CI and locally. The framework declares
  `requires-python = ">=3.12"` and its own CI exercises 3.12 and 3.13.
- pip, and **git**: `requirements.txt` resolves the framework from its repository.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python -m playwright install chromium
```

`requirements.txt` is a generated, fully-pinned lock file — install from it, don't hand-edit it.
It carries the framework as a pinned reference to its own repository, so this step needs git and
network access, and everything the framework itself needs (pytest, Playwright, allure-pytest,
pytest-rerunfailures) arrives with it.

To change a dependency, or to move to a new framework release, edit `requirements.in` (the loose,
human-maintained source) and regenerate both locks — the second is constrained to the first so the
two cannot disagree about the framework's dependencies:

```bash
pip install pip-tools
pip-compile --output-file=requirements.txt --strip-extras requirements.in
pip-compile -c requirements.txt --output-file=requirements-ai.txt --strip-extras requirements-ai.in
```

Commit the files together so installs stay reproducible. **Rolling the framework back** is a
one-line change of the ref in `requirements.in` followed by that regeneration.

For developing the framework itself, clone [its repository](https://github.com/abhay-scaler/playwright-pytest-framework) and install it editable
alongside this one (`pip install -e ../playwright-pytest-framework`); that is a local override and
must never be committed here.

To install other browser engines (used by the nightly cross-browser CI job, or on demand
locally):

```bash
python -m playwright install firefox webkit
```

## Configuration

The authoritative reference for both layers is [the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md): it defines
the environment variables it reads and the `AppConfig` keys it accepts, and keeping a second copy
of that table here is how a framework and its consumer start disagreeing about what
`action_timeout` means. What follows is this project's side of it — one example, and the one key
that is *ours*.

A per-application file, `apps/<app_name>/config/<environment>.json`, selected by `ENVIRONMENT`
(default `local`):

```json
{
  "base_url": "https://example.test",
  "action_timeout": 15000,
  "retry_count": 1,
  "ignore_https_errors": false,
  "secrets": {
    "api_key": "MY_APP_API_KEY"
  },
  "production_target": false
}
```

- `base_url`, `action_timeout`, `retry_count`, `ignore_https_errors`, `secrets` — framework keys;
  see the reference above. **Never put an actual secret value in `secrets`**: map a logical name
  to the *name* of an environment variable, and the value is read at runtime through
  `AppConfig.secret("api_key")`. No application here declares any secrets — none of the sample
  applications require credentials.
- `production_target` — **this project's own key, not an `AppConfig` field.** `true` declares that
  an application drives a live third-party production site: every test under it must carry
  `@pytest.mark.production`, and a production-marked test that no declared application owns is
  equally an error. `tests/test_ci_production_exclusion.py` reads it straight from the JSON —
  every environment file, so a `true` anywhere counts — and fails on a malformed file or a
  non-boolean value rather than quietly dropping the application from the check. Nothing in the
  framework names an application; a new production app becomes visible to the guard by declaring
  itself.
- Any other key lands in `AppConfig.extra` for app-specific use (for example a
  `consent_selector` for a cookie banner). **Unknown keys are accepted silently, not rejected** —
  a misspelling such as `timeout_ms` for `action_timeout` lands in `extra` and simply never takes
  effect.

Example combining both layers:

```bash
BROWSER=firefox HEADLESS=true ENVIRONMENT=ci pytest tests/web_search
```

## Running Tests

```bash
# Full suite
pytest -q

# Headed / headless explicitly
HEADLESS=false pytest -q
HEADLESS=true pytest -q

# One application, any environment
pytest tests/sample_app -q
ENVIRONMENT=ci pytest tests/web_search -q

# One specific test file or test case
pytest tests/sample_app/ui/test_sample_app_form.py -q
pytest tests/api/test_json_placeholder.py::test_json_placeholder_nonexistent_post_returns_404 -q

# By marker
pytest -m smoke -q
pytest -m ui -q
pytest -m api -q

# Known-unstable tests: excluded from the blocking gates, still runnable
pytest -m quarantined -q                        # currently empty; DESIGN.md section 8 keeps the record

# Production-site tests (opt-in, local only - excluded from every CI job)
HEADLESS=false pytest -m production -q          # headed and supervised: the intended way
pytest tests/myntra -m production -q            # one production application
pytest -m "not production" -q                   # what CI runs: everything else

# In parallel
pytest -n auto -q

# Re-run only what failed last time
pytest --lf

# This project's own policy and documentation tests (fast, no browser)
pytest tests/test_*.py -q
```

Registered markers (`pytest.ini`): `smoke`, `ui`, `api`, `regression` (reserved for future use —
currently no test carries it), `production` (drives a live third-party site; excluded from every
CI job, opt in locally as above), `scenario(id)` (the catalog scenario a test implements, also
attached as an Allure label), `quarantined` (known-unstable; excluded from the blocking CI
gates, run in a non-blocking job), and an auto-applied `app(name)` marker the installed plugin
assigns based on each test's file path. The plugin registers all of them itself, so
`--strict-markers` holds even though this project declares them in `pytest.ini` too.

## Reporting and Failure Diagnostics

| Artifact | Location | When |
|---|---|---|
| HTML report | `reports/pytest_report.html` | every run; failure screenshots embedded automatically |
| Allure results | `reports/allure-results/` | every run; `application`/`browser`/`environment` labels on every test; Allure's own stale results from previous runs cleared automatically, other files in that directory left alone |
| Screenshot | `screenshots/<app_name>/<test_name>.png` | UI test failure only |
| Trace | `traces/<app_name>/<test_name>.zip` | UI test failure only |
| Video | `videos/<app_name>/<test_name>.webm` | UI test failure only |
| Logs | `logs/<worker>/framework.log` (`logs/main/` when serial) | every run |

View the Allure report locally:

```bash
pip install allure-commandline    # or: brew install allure
allure serve reports/allure-results
```

Open a saved trace:

```bash
playwright show-trace traces/<app_name>/<test_name>.zip
```

Debugging a failure: start with the HTML report (embedded screenshot), open the trace for full
DOM/network/console detail, check the video for the visual sequence, and grep
`logs/<worker>/framework.log` for the test or application name — including any browser console
error / page error lines captured passively during the run.

## Architecture and Fixture Strategy

The fixture chain, the artifact lifecycle and the xdist guards are the framework's, and are
documented in [its README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md). What matters here is the one end of the chain this
project owns:

| Fixture | Scope | Owner | Purpose |
|---|---|---|---|
| `playwright_context`, `browser` | session | framework | one driver and one browser per worker process |
| `context`, `page` | function | framework | a fresh context and page per test; `page` owns the whole trace/screenshot/video capture lifecycle in its teardown |
| `app_config` | session | **this project** | `tests/<app>/conftest.py` binds it to an application name — the one fixture a new application must define |

One browser launch per worker, a fresh context per test, and each `pytest-xdist` worker is a
separate process with its own browser: there is no shared browser, context or global mutable
state between workers. Artifact paths are namespaced `<application>/<test_name>` and Allure
results are UUID-named per test, so two tests cannot collide on a path even across workers.

This project's own architecture — the application layout, the CI policy and the onboarding
walkthrough — is in [DESIGN.md](DESIGN.md).

## Code Quality

```bash
ruff check .
black --check .
mypy .
pre-commit install          # once per clone
pre-commit run --all-files
```

`detect-secrets` runs as part of the pre-commit hooks, checked against the baseline at
`.secrets.baseline`. If it flags something new, verify it's genuinely not a secret, then update
the baseline:

```bash
detect-secrets scan --baseline .secrets.baseline
```

## Continuous Integration

`.github/workflows/ci.yml` runs as six jobs rather than one, so a pull request gets fast feedback
without giving up full-suite and cross-browser coverage. The framework's own three jobs — lint and
type check, its self-tests on 3.12 and 3.13, and the installed-package verification — run in
[its repository](https://github.com/abhay-scaler/playwright-pytest-framework); this project gates the framework by pinning a tag, not by re-testing it.

1. **Lint & Type Check** — Ruff, Black, mypy, and the documentation link checker. Every trigger,
   before any job installs a browser.
2. **Scenario Catalog** — `python -m pwpf.ai_testing.validate_catalog`, from the framework's `ai`
   extra. Every trigger; static analysis, no pytest and no browser.
3. **PR Smoke** — this project's policy and documentation tests plus
   `-m "smoke and not production and not quarantined"`, Chromium only. Pull requests only, kept
   deliberately fast.
4. **Regression** — the full suite, Chromium, `-n auto`. Push to `main`/`dev`, nightly schedule,
   and manual dispatch.
5. **Cross-Browser** — the full suite against Firefox and WebKit. Nightly, or on demand via
   `workflow_dispatch` — not on every PR, since it roughly triples runtime.
6. **Quarantined (non-blocking)** — `-m "quarantined and not production"` with
   `continue-on-error: true`: known-unstable tests still run and report, but gate nothing.

Every pytest invocation in the workflow carries `-m "not production"`, so tests that drive a live
third-party site are never collected in CI; `tests/test_ci_production_exclusion.py` fails if any
invocation loses the exclusion. Every **blocking** invocation also excludes `quarantined`, which
the non-blocking job runs instead; `tests/test_quarantine_policy.py` pins which tests those are.
See [DESIGN.md](DESIGN.md) §8.

Both pip and the Playwright browser binary are cached. The browser cache is keyed on the
Playwright version **the installed environment actually reports**, not on a line in a
requirements file: Playwright now arrives transitively through the framework, and reading the
version from the environment is the only way the key cannot silently disagree with what is
installed. Every job uploads its `reports/`, `screenshots/`, `traces/` and `videos/`
unconditionally (`if: always()`), and emits a JUnit XML report alongside the HTML/Allure output.

## Local-Only Overrides

A contributor's machine may need a tweak the rest of the team doesn't — an unsupported browser
build for their OS version, a different local port, an editable checkout of the framework. The
supported way is to make the change locally and simply **not commit** it — `git status`/`git diff`
will show it as an uncommitted local change.

- Prefer an environment variable or a per-app `config/*.json` entry over editing a shared file,
  whenever the override can be expressed that way.
- Keep a genuinely necessary tracked-file edit (`pytest.ini`, `requirements.txt`) small and easy
  to spot in a diff.
- `pip install -e ../playwright-pytest-framework` is the override for working on the framework and
  this project together. It belongs in your environment, never in `requirements.in`: CI must
  install the pinned reference, and `tests/test_extraction_dry_run.py` fails if that stops being
  what the file declares.
- Never commit an override, and don't let it change default behaviour for anyone who hasn't made
  the same local edit.
- If more than one contributor needs the same workaround, that's a signal it should become a real,
  documented, opt-in feature — in this project or in the framework, depending on where it belongs.

## Troubleshooting

Each entry is tagged with where the behaviour lives — **framework** if it is the installed
plugin's doing and would follow the distribution into any project that uses it, **consumer** if it
is about this repository's own configuration.

**"Playwright browser could not be launched" (test skipped, not failed)** — *framework* — the
browser binary isn't installed yet:

```bash
python -m playwright install chromium
```

**Browser launch fails even after installing** — *framework* — check the exact error Playwright
prints. A
common cause is an unsupported host OS/browser-build combination (for example, an older macOS
version than Playwright's currently-pinned Chromium build supports). See
[Local-Only Overrides](#local-only-overrides) for how to work around this on your own machine
without changing the framework's shared, default behavior.

**A test fails only in CI, not locally (or vice versa)** — *both* — check `ENVIRONMENT` first
(the framework reads it; which files it selects, `apps/<app>/config/*.json`, is the consumer's),
then `HEADLESS`/`BROWSER`. Confirm your installed versions match `requirements.txt` exactly
(`pip install -r requirements.txt` from a clean virtualenv) rather than whatever was already
installed — that lock file is this repository's, and it is also what pins the framework, so an
editable checkout left over from local work is worth ruling out first.

**A parallel-only failure (`pytest -n auto` fails, `pytest` alone passes)** — *both* — running
in parallel is this repository's choice (xdist is the consumer's dependency), while the per-worker
log it leaves behind is the framework's: check `logs/gw*/framework.log` for that worker's output.

## Known Limitations

Honestly documented rather than hidden — these are deliberate absences, not oversights, and each
has a clear extension path.

**Inherited from the framework.** Its own absences — no authentication or session infrastructure,
no test-data factories, one browser engine per run — are documented in
[its README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md) and are that repository's to close. Two are worth naming here because
they shape this project:

- **The framework is not published to a package index.** It is consumed as a pinned Git
  reference. That needs no index, no credentials and no release automation, and `pip` records the
  commit the tag resolved to; the trade-off is that a consumer needs git at install time. The
  options and the recommendation are in
  [docs/framework-extraction-readiness.md](docs/framework-extraction-readiness.md) §4.
- **The framework ships no `py.typed` marker at `v0.1.0`**, so mypy will not analyse it. This
  project silences the resulting `import-untyped` reports with one override in `pyproject.toml`
  rather than leaving 20 errors in the lint gate; the real fix is a marker in a framework release,
  and the override comes out when one carries it.

**This project's**

- **Allure results are generated and uploaded, but not rendered or published in CI.** Viewing a
  report requires `allure serve`/`allure generate` run locally against the downloaded results.
- **Ruff's rule set is intentionally narrow** (`E`, `F`, `I` — style and import order), not
  `B`/`UP`/security-oriented rules.
- **No accessibility testing** (no `axe`-style integration) and **no containerized CI** — neither
  has been a concrete requirement for the current applications.
- **Two locator modules share the same class name** (`HomePageLocators`, in two different
  applications) — harmless since imports are fully qualified, but worth knowing if you're
  searching the codebase by class name.
- **One live-site test still gates pull requests.** `tests/web_search` drives `playwright.dev`,
  a third party's production site, in the smoke gate. Its hydration race is fixed and the
  interaction contract is covered locally by `tests/web_search/ui/test_search_hydration.py`, but
  whether a docs search on someone else's site belongs in a blocking gate at all is still an open
  decision — see [DESIGN.md](DESIGN.md) §8.

None of the above are correctness bugs in what's implemented — they're scope boundaries, each with
a known, documented path forward if a real requirement arrives.
