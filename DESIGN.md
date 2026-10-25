# Framework Design

This document describes the architecture, CI policy and design decisions of **this project** —
the applications under test, their tests and the governance around them. The framework they run on
is a separate, installable distribution,
[playwright-pytest-framework](https://github.com/abhay-scaler/playwright-pytest-framework), pinned in `requirements.in`;
its internals are documented in [its own README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md).

The section numbering is unchanged across the extraction, because other documents cite it by
number. Sections that described the framework now say so and point at it, in one place, rather
than keeping a second copy of a contract that would drift from the code implementing it.

## 1. Architecture Overview

**Moved to the framework.** The framework's layering - the plugin, its configuration resolution, its core and utils - left this repository with the package. It is documented in
[the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md), which is the single authoritative copy — a second one here would
drift from the code that implements it.

What is left here is the shape of the consumer side, which the framework deliberately knows
nothing about:

- **`apps/<app_name>/`** — one directory per application under test: its configuration, page
  objects, locators, test data and scenario catalog.
- **`tests/<app_name>/`** — that application's tests, plus the one `app_config` fixture that
  binds them to it. The framework infers the application from this pairing; it holds no list of
  names (§6 of its README).
- **This repository's own policy** — the production-exclusion and quarantine guards, the catalog
  governance, and the CI jobs in §8.

## 2. Directory Structure

One tree: this project. The framework is an installed distribution, and its own tree -
`pwpf/`, its packaging, its self-tests and the installed-package verification - is in
[its repository](https://github.com/abhay-scaler/playwright-pytest-framework) (§12).

```
apps/
  sample_app/                  # a static local HTML app (demonstrates a file-based app)
    config/
      local.json
      ci.json
    pages/
      sample_app_page.py
    locators/
      sample_app_locators.py
    testdata/
      sample_app.html
  web_search/                  # a real network app (demonstrates a base_url-driven app)
    config/
      local.json
      ci.json
    pages/
      home_page.py
    locators/
      home_page_locators.py
    testdata/
      hydration_fixture.html   #   local stand-in for a late-hydrating page (see §8)
  uitesting_playground/        # a multi-page app (demonstrates >1 page object per app)
    config/
      local.json
      ci.json
    pages/
      home_page.py
      dynamic_id_page.py
    locators/
      home_page_locators.py
      dynamic_id_page_locators.py
  myntra/                      # live production site - exploration target, never a CI gate
    config/
      local.json               #   local only: deliberately no ci.json (see §8)
    pages/
      home_page.py
    locators/
      home_page_locators.py
    scenarios/
      shopping_journey.yaml    #   scenario catalog, schema-validated in CI (§11)

tests/
  sample_app/, web_search/, uitesting_playground/
    conftest.py                # binds the generic app_config fixture to this app's name
    smoke/, ui/
  api/, tmp/                   # suites not owned by one application
  test_ci_production_exclusion.py   # policy: this repository's CI never collects a live-site test
  test_quarantine_policy.py    # policy: what is quarantined, and why, stays on the record

pytest.ini                     # test discovery, markers, default CLI options
requirements.in                # loose, human-maintained dependency source
requirements.txt               # generated, fully-pinned lock file - install from this
requirements-ai.in / .txt      # scenario-validator deps only, outside the test runtime (§11)
.pre-commit-config.yaml        # ruff, black, mypy, detect-secrets
.secrets.baseline              # detect-secrets baseline (known-safe matches, e.g. docs examples)
.github/workflows/ci.yml       # the six CI jobs (§8)
docs/                          # this repository's documentation, including the AI-testing workflow
ai_testing/                    # the prompt library and templates (no code, no dependencies)
scripts/extraction_dry_run.py  # proves this project runs against the installed framework
scripts/check_doc_links.py     # the documentation link and fragment gate (§8)
```

Generated at runtime and git-ignored, under the **consumer's** project root rather than the
framework's own directory (§6): `reports/`, `screenshots/`, `traces/`, `videos/`, `logs/`.

## 3. Execution Flow

**Moved to the framework.** The fixture chain, the artifact capture lifecycle, the hooks and the xdist guards are the plugin's. It is documented in
[the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md), which is the single authoritative copy — a second one here would
drift from the code that implements it.

## 4. Major Components

**Moved to the framework.** `BasePage`, `AppConfig`, the API client, the logger, the report embedder and the Allure cleanup are all framework modules. It is documented in
[the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md), which is the single authoritative copy — a second one here would
drift from the code that implements it.

This repository's components are its applications (`apps/<app>/pages`, `locators`, `testdata`),
their scenario catalogs, and the policy tests under `tests/`.

## 5. Fixture Strategy

**Moved to the framework.** One driver and one browser per worker, a fresh context and page per test: the framework's chain. It is documented in
[the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md), which is the single authoritative copy — a second one here would
drift from the code that implements it.

The one fixture this repository owns is `app_config`, declared session-scoped in each
`tests/<app>/conftest.py` and bound to that application's name. It is the only thing a new
application must define — see **Adding a New Application** below.

## 6. Test Data & Configuration Approach

**Moved to the framework.** The `AppConfig` key contract, the environment variables, the secrets-by-reference convention and the project-root resolution order are the framework's. It is documented in
[the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md), which is the single authoritative copy — a second one here would
drift from the code that implements it.

What stays with this repository is the data and one key of its own:

- `apps/<app>/config/<environment>.json` per application and environment, selected by
  `ENVIRONMENT`. One example is in [README.md](README.md#configuration).
- `production_target` — **this repository's key, not an `AppConfig` field.** It declares that an
  application drives a live third-party production site, and
  `tests/test_ci_production_exclusion.py` reads it straight from the JSON. See §8.
- `apps/<app>/testdata/` — static fixtures, where an application needs one.

## 7. Reporting

**Moved to the framework.** The HTML-report embedding, the Allure labels and the stale-result cleanup are the plugin's, and run the same way in any project that installs it. It is documented in
[the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md), which is the single authoritative copy — a second one here would
drift from the code that implements it.

Where the artifacts land in *this* repository, and how to open them, is in
[README.md](README.md#reporting-and-failure-diagnostics).

## 8. CI/CD Flow

GitHub Actions (`.github/workflows/ci.yml`) runs as six jobs rather than one, so a PR gets fast
feedback without giving up full-suite and cross-browser coverage. All six are this project's; the
framework's own three - lint and type check, its self-tests on 3.12 and 3.13, and the
installed-package verification - run in its repository, and this project gates it by pinning a tag
rather than by re-testing it:

1. **Lint & Type Check** — `ruff check .`, `black --check .`, `mypy .`, and
   `python scripts/check_doc_links.py`. Runs on every trigger (push, PR, schedule, manual
   dispatch), before any job installs a browser, so a lint/type error fails in seconds rather
   than after a multi-minute Playwright install. Both repositories will want the first three on
   their own code; the documentation gate is this repository's.
2. **Scenario Catalog** — `python -m pwpf.ai_testing.validate_catalog`, installing only
   `requirements-ai.txt`, which is the framework's `ai` extra at the same pinned tag. Every
   trigger. No pytest, no browser, no
   network, so it needs no Playwright install and finishes in seconds; it is also the only job
   that installs anything outside the test-runtime lock (§11).
3. **PR Smoke** (`pull_request` only) — this project's own policy and documentation tests
   (`tests/test_*.py`, fast, no browser) plus `-m "smoke and not production"`, Chromium only. Deliberately narrow: full
   regression coverage belongs to the jobs below, not to every PR.
4. **Regression** (push to `main`/`dev`, nightly, manual dispatch) — the full suite, Chromium,
   `pytest -m "not production" -n auto`.
5. **Cross-Browser** (nightly, or manual dispatch with the `cross_browser` input) — the full suite
   against Firefox and WebKit, as a matrix. Not run on every PR — it roughly triples runtime for
   coverage most changes don't need.
6. **Quarantined (non-blocking)** — `pytest -m "quarantined and not production"`, with
   `continue-on-error: true`, so known-unstable tests still run and still report without
   gating anything. See "Quarantined tests" below.

Each browser-driving job:
- Installs Python dependencies from the pinned `requirements.txt` (cached via
  `actions/setup-python`'s `cache: pip`, keyed on the file's hash).
- Reads the Playwright version from the installed environment
  (`importlib.metadata.version("playwright")`) and uses it as the cache key for
  `~/.cache/ms-playwright`. Playwright arrives transitively through the framework now, so the
  environment is the only source that cannot disagree with what is installed; a version change
  always misses the cache and installs fresh, so a stale cache can never serve an incompatible
  browser binary.
- Emits a JUnit XML report alongside the HTML/Allure output.
- Uploads `reports/`, `screenshots/`, `traces/`, `videos/` unconditionally (`if: always()`), under
  a job-specific artifact name (required since `upload-artifact@v4` needs unique names across a
  workflow run when multiple jobs upload).

Because `testpaths = tests` in `pytest.ini` is recursive and application membership is inferred
from the path, **onboarding a new application requires no CI changes** for its tests to run — they
are auto-discovered the moment `tests/<new_app>/` exists. That convenience cuts both ways, and
the subsection below is the counterweight. The `apps/<app>/` boundary this
framework already uses is also what a future CI matrix would shard on (one job per app) if the
suite ever grows large enough to need it — no new tooling required to get there, just a matrix
entry keyed on `tests/<app>` when that day comes. Not done today because three demo applications
don't justify the added CI complexity.

### Production-site applications and the CI exclusion

Auto-discovery means a new `tests/<app>/` folder joins the regression suite and the nightly
cross-browser sweep by itself, with nobody deciding that it should. For an application that
drives someone else's live production site, that default is wrong: §6 already records why this
framework moved `web_search` off `google.com` — a third party's production site that actively
defends against automated traffic is a poor foundation for a blocking CI gate, because the
failure has nothing to do with the code under test.

So such tests are labelled and excluded:

- **`@pytest.mark.production`** (registered in `pytest.ini`) marks every test that drives a
  live third-party site. `myntra` is the only such application today.
- **An application declares itself** with `"production_target": true` in its own
  `apps/<app>/config/<environment>.json`. The guard below discovers production applications
  from that declaration rather than from a list of names, so the framework layer never has to
  know which application happens to be the pilot — a step towards an application-neutral
  framework (§11). A declaration that cannot be read, or that is not a JSON boolean, fails
  the check instead of quietly dropping the application from it.
- **Every pytest invocation in `.github/workflows/ci.yml` carries `-m "not production"`** — all
  four of them: framework self-tests, PR smoke (`"smoke and not production"`), regression, and
  each cross-browser matrix leg. The marker is a label; these four commands are the control.
- **`tests/test_ci_production_exclusion.py`** fails if any pytest invocation in the workflow
  loses the exclusion, if the marker stops being registered, if a test under a declared
  production application forgets the marker, or if a production-marked test turns up under an
  application that never declared itself. It is static analysis — it reads the workflow as
  text, the configs as JSON and the tests as an AST, so it needs no browser, no network, and
  no YAML dependency.
- **Running them is a deliberate, local act**: `HEADLESS=false pytest -m production`, supervised,
  on a machine where that is authorized. Checkout, payment, order placement and account
  creation are out of scope for this phase, so no page object or test for them exists.

A CI-gated end-to-end pilot therefore needs a *sanctioned* target — a local fixture app in the
shape of `sample_app`, or a site published for automation practice. That choice is still open
and is tracked as an open item for the AI test-engineering work; until it is made, no
live-site test is a CI gate.

One policy note, since it is easy to get backwards: a safety control like this exclusion **is**
an authorized change to the shared framework layer, and an AI-assisted workflow that forbade
shared-framework edits outright would have blocked the one change that makes production
exploration safe. The bar is justification, not prohibition — unrelated framework changes still
need a reason, and a configuration flag that no code reads (`allow_order_placement: false` in a
YAML file, say) is documentation, never enforcement.

### Quarantined tests

A `quarantined` test is known-unstable and excluded from every blocking gate, while still
running in the non-blocking `Quarantined` job so its outcome stays visible. The marker is
additive: the test keeps its `smoke`/`ui` markers and `pytest -m quarantined` (or naming the
file) still runs it locally. `tests/test_quarantine_policy.py` pins the exact set, requires
each entry to explain itself and to be recorded here, and fails if a blocking job stops
excluding the marker or if the non-blocking job stops running it.

Quarantine is a holding state with an exit criterion, not a bin. It is never the fix for a
failure, and a fixed sleep, a longer timeout or an extra rerun is never the fix either — those
change the report, not the behaviour.

**Currently quarantined: nothing.** The list below is the record of what has been through
quarantine and how it left.

**`tests/web_search/smoke/test_web_search.py::test_web_search` — quarantined 2026-10-24,
repaired and restored to the blocking smoke gate the same day.**

- **Symptom**: `Locator.wait_for: Timeout 15000ms exceeded` waiting for
  `.DocSearch-Modal input[type='search']` to be visible, after `HomePage.search` clicks the
  header search button. Intermittent: it passed at 11:01 and failed on every run afterwards.
- **Cause (evidence-based, not assumed)**: a hydration race in the test, not a site outage and
  not a stale selector. `HomePage.open` waits only for `domcontentloaded`, so the click lands
  on playwright.dev's server-rendered search button before Algolia DocSearch has attached its
  handler; nothing opens, and the subsequent wait times out. A probe against the live site
  confirmed the modal and its input are present and visible when the search control is clicked
  after the page settles (`.DocSearch-Modal`, `input.DocSearch-Input[type=search]`,
  `placeholder="Search docs"`), so the selectors in
  `apps/web_search/locators/home_page_locators.py` are current. Clicking immediately after
  `domcontentloaded` failed 3/3; clicking after a short settle opened the modal 3/3.
- **Reproduced on a pristine baseline**: the same failure occurs on commit `36aac2f` in a
  separate worktree, so it predates the AI test-engineering work and is not a regression from
  it. It fails on a developer machine as readily as in CI.
- **The repair**: `HomePage.open` now waits for `html[data-has-hydrated="true"]` — Docusaurus's
  own hydration flag, served as `false` and flipped to `true` by the client bundle — before
  anything is clicked. It synchronises on the application's state rather than on elapsed time:
  no `time.sleep`, no `wait_for_timeout`, no raised timeout (`action_timeout` is unchanged at
  15s), no added reruns, and the assertion that the modal and its input actually appear is
  untouched. The page object clicks the search control exactly once, so there is no retry that
  could toggle an open modal shut.
- **Measurements behind it**: with the fix, clicking straight after the readiness signal opened
  the modal 5/5 in a probe and the test then passed 10/10 as ten separate `pytest` processes
  (each launching its own browser, no reruns, 1.4–4.2s per run). Without it, the same click
  failed 3/3. The deterministic half of that evidence is now a test:
  `tests/web_search/ui/test_search_hydration.py` drives a local fixture whose button hydrates
  late, and all three of its cases fail against the unfixed page object.
- **What is not yet established**: the non-blocking CI job has not run, because nothing has been
  pushed. The first CI run of the restored test is that confirmation; if it fails there, the
  marker goes back on and this record reopens.
- **Still open, and separate from the repair**: this test gates PRs against a third party's
  live site, which §6 already argues against. Fixing the race removed the defect; whether a docs
  search on someone else's site belongs in the blocking PR gate at all is an architecture
  decision, tied to the sanctioned-target question in "Production-site applications and the CI
  exclusion" above. The deterministic fixture tests mean the interaction contract is covered
  either way, so that decision can be taken on its merits rather than under the pressure of a
  red gate.

## 9. Design Principles

**Moved to the framework.** The framework's principles - that it never knows an application's name, that nothing resolves against the installed package, that importing a module writes nothing - are stated with the code that honours them. It is documented in
[the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md), which is the single authoritative copy — a second one here would
drift from the code that implements it.

## 10. Fixed Since the Last Review

This section is kept whole, framework entries included, because several of them explain each
other and splitting it would destroy the chronology. Entries that name `pwpf/...` or a framework
self-test describe code that now lives in [the framework's repository](https://github.com/abhay-scaler/playwright-pytest-framework) — they are history,
not a map of this tree.

The previous review of this framework flagged several concrete bugs; these are now fixed as part
of adding multi-application support (since the same code paths needed touching either way):

- **Tracing previously started after the test had already failed**, producing an empty, useless
  trace file. Tracing now starts when the page is created and is stopped (and saved) only on
  failure, discarded otherwise.
- **The saved video path never matched Playwright's actual output file.** Video is now correctly
  retrieved via `page.video.path()` after the page closes, renamed to a predictable path on
  failure, and deleted on success (previously kept for every test, unbounded).
- **A scratch test that always failed by design sat in the default collection path**
  (`tests/tmp/test_failure_artifacts.py`), breaking any real CI run. It's now explicitly skipped
  with a clear reason, kept only for manual verification.
- **A dead, unregistered fixture file** (`fixtures/browser.py`) duplicated `conftest.py` without
  ever being imported. Deleted.
- **A half-wired global environment-config system** (`config/environments/*.json`, loaded into
  `ENV_CONFIG` but never read anywhere) has been replaced by the per-application config described
  above, which is actually consumed.
- **Found while validating this change**: the autouse artifact-capture fixture forced every test
  — including pure API and config unit tests — to launch a browser, since it declared `page`/
  `context` as parameters purely to control teardown order. This made the entire suite depend on a
  browser binary being installed, even for tests that never touch one. Fixed by moving capture
  logic into `page`'s own teardown (§5).
- **Found on the first real CI run**: `google_search`'s test (the network-app demo, at the time
  pointed at live `google.com`) failed intermittently with a timeout waiting for the search box.
  Root cause: Google serves a GDPR consent interstitial to traffic it geolocates to the EU/UK,
  which GitHub-hosted runners aren't guaranteed to avoid, on top of general anti-automation
  defenses outside this framework's control. Fixed two ways: the app was renamed `web_search` and
  repointed at `playwright.dev`'s own docs search (a target with no consent wall and no incentive
  to block Playwright-based automation — see §6), and `BasePage` gained a reusable
  `dismiss_if_visible(selector)` helper any application can wire through its config's
  `consent_selector` (or similarly-named `extra` key) for the case of a genuinely consent-walled
  target — see "Adding a New Application," step 2.

- **Found on the second real CI run**: after the `web_search` swap, the test still failed, but
  differently — `results_visible()` returned `False` instead of timing out. Confirmed directly
  against the live DOM (via a real browser, not Playwright's) that `.DocSearch-Hits` was the
  correct selector and genuinely became visible after a search — the actual bug was
  `Locator.is_visible(timeout=...)` itself: despite the parameter name, Playwright's `is_visible()`
  does **not** poll/retry until the timeout elapses, it's a single instantaneous check. It was
  called immediately after `fill()`, before DocSearch's async Algolia search-as-you-type request
  had time to resolve and render — a pure timing race, unrelated to the selector. This was latent
  in `BasePage.is_visible` itself (not just this one call site), silently non-functional for
  anyone who used it expecting wait-and-retry semantics; the original `google_search`/`HomePage`
  never surfaced it because a full-page navigation (Google's `Enter`-triggered results page load)
  happened to finish before the check ran, masking the race by coincidence rather than by
  correctness. Fixed at the source: `BasePage.is_visible` now uses `Locator.wait_for(state=
  "visible")`, which does retry, and `HomePage.results_visible()` now calls `self.is_visible(...)`
  instead of bypassing `BasePage` with a raw Playwright call.

**Deliberately not done in that pass** (real, but independent of multi-app support): a shared API
client abstraction for `tests/api/`, and placeholder test cleanup (`test_ui_sample.py`,
`test_api_placeholder`). Both were addressed in the hardening pass below.

### Hardening pass (following a full architecture audit)

A subsequent audit (scored 6.4/10, "Intermediate") surfaced several concrete issues, fixed on a
dedicated branch without changing the architecture described above:

- **Screenshot embedding was confirmed broken** — `report_embedder.py`'s glob was non-recursive
  and never found the per-app-namespaced screenshot subdirectories introduced by multi-app
  support. Fixed (§7), with an added `since=` filter so a stale screenshot from a previous run
  can't be silently re-embedded into a new report, and asset-name namespacing so two apps'
  identically-named screenshots can't collide once copied into one flat `assets/` folder. Covered
  by `tests/test_report_embedder.py`.
- **Logging was not xdist-safe** — every worker wrote to one shared, unattributed log file. Fixed
  by making `pwpf/utils/logger.py` worker-aware (§3/§7), covered by `tests/test_logger.py`.
- **No dependency lock file** — `requirements.txt` was loose lower-bound constraints only.
  Replaced with a `pip-compile`-generated lock (§9), verified to install cleanly in a completely
  fresh environment.
- **`ignore_https_errors` was a single global, unscoped `True`** — now a per-app `AppConfig` field
  (default `True`, preserving every existing app's behavior), covered by `tests/test_app_config.py`.
- **Mixed assertion idioms** — `sample_app`'s tests used plain `assert` against a value returned by
  `BasePage.get_text()`, which (unlike the already-fixed `is_visible()`) is still a single
  non-retrying read. Migrated those two tests to `expect(locator).to_have_text(...)`, via a new
  `SampleAppPage.message_locator()` returning the `Locator` itself rather than an extracted string
  — keeping the same Page Object → state query / Test → assertion boundary, not moving assertions
  into the page object. `web_search`'s test was left as-is: it already goes through the fixed,
  retry-safe `is_visible()`, so there was no further reliability gap to close there.
- **Three zero-value placeholder tests removed** (`test_ui_sample.py`, `test_api_placeholder`,
  `test_regression_sample.py`) — each asserted something that could never fail
  (`assert True`, `assert 2 + 2 == 4`), inflating the passing-test count without contributing real
  coverage. The `regression` marker remains registered for real future use; it's simply unused
  today rather than backed by a fake placeholder.
- **The one real API test moved off `requests`** and onto `pwpf/core/api_client.py`, a thin wrapper
  around Playwright's own `APIRequestContext` (§4) — `requests` was used nowhere else, so this
  removed a dependency rather than adding one.
- **Static type checking added** (mypy, non-strict, incremental — see `pyproject.toml`), which
  caught two real gaps while being introduced: `BasePage.goto()`'s `wait_until` accepted any `str`
  instead of Playwright's actual `Literal` union, and `web_search`/`uitesting_playground`'s page
  objects accessed `self.config` as if it were never `None` despite `BasePage` typing it
  `Optional` — both fixed at the type level, not suppressed.
- **Secret scanning added** (`detect-secrets` pre-commit hook + `.secrets.baseline`) as an
  automated guardrail behind the existing secrets-by-reference convention (§6), which previously
  relied on the convention alone.
- **Ruff's config was on a deprecated path** (top-level `select` instead of `[tool.ruff.lint]`),
  nagging on every invocation. Fixed with no behavior change.
- **CI restructured** into lint/type-check, PR-smoke, regression, and cross-browser jobs (§8),
  with dependency and browser-binary caching and JUnit XML output added — previously a single job
  ran the entire suite, uncached, on every push.

### Follow-on hardening pass (commit `04f214f`)

A further, smaller batch of fixes landed after the pass above, once the framework was already
running under real `pytest -n auto` load:

- **The report-embedding hook ran once per xdist worker plus once in the master** — `pytest
  -n auto` fires `pytest_terminal_summary` in every worker process as well as the master, so
  without a guard, each worker redundantly re-scanned and rewrote the same
  `reports/pytest_report.html`. Fixed with a one-line `config.workerinput is None` guard so only
  the master embeds (§3/§7). Confirmed under real `-n auto` execution: exactly one embed
  invocation instead of N+1.
- **No browser console/page-error visibility** — the `page` fixture now registers passive
  `page.on("console", ...)`/`page.on("pageerror", ...)` listeners, logging error-level console
  messages and uncaught JS exceptions through the existing worker-aware logger (§3/§7). Diagnostic
  only; never fails a test.
- **Allure results carried no browser/environment context** — the existing
  `_tag_allure_application` fixture now also labels every test with `browser` and `environment`
  (§3/§7), so a nightly cross-browser failure is identifiable from the Allure result itself.
- **No negative-path API coverage** — `tests/api/test_json_placeholder.py` gained a test asserting
  the real, verified contract for a nonexistent resource (`GET /posts/999999` → `status=404`,
  `ok=False`, no exception raised — `pwpf/core/api_client.py` is a thin passthrough to Playwright's own
  `APIRequestContext`, which does not raise on a non-2xx response).
- **`reports/allure-results/` accumulated forever** — allure-pytest never clears its own output
  directory, so every run added another UUID-named result per test with nothing ever removing old
  ones. Fixed with a `pytest_configure` hook (`pwpf/utils/allure_cleanup.py`, same xdist-master guard as
  above) that clears, once at the start of each run, Allure's own artefacts from the directory
  the run is actually writing to — taken from `--alluredir` and resolved the way allure-pytest
  resolves it, since the first version of this cleanup resolved it from the project root (so a
  run started from a subdirectory cleared nothing of the sort) and the second expanded `~` (so
  it deleted from a real `$HOME` directory Allure never writes to). Both are pinned by
  `tests/test_allure_cleanup.py`, which also covers the files it must leave alone.

---

## 11. AI-Assisted Test Engineering (Optional)

An optional way of working, not a part of the framework: a version-controlled set of prompts,
templates and conventions for using a coding assistant to help design and implement tests here.
Nothing in it is imported, installed or executed by a test run, it adds no dependency to
`requirements.in`/`requirements.txt`, and deleting both directories would leave every test
behaving identically.

- **[docs/ai-testing/](docs/ai-testing/README.md)** — the entry point: the twelve-stage workflow
  (inputs, outputs, owner and completion criterion per stage), scenario authoring and governance,
  the Codegen-to-page-object standards, a review checklist and evidence-based troubleshooting.
- **[ai_testing/](ai_testing/README.md)** — the prompt library (ten prompts, each with purpose,
  inputs, instructions, output format, acceptance criteria, safety constraints and human-review
  requirements), the feature-brief and scenario templates, and the house rules every prompt
  inherits.

Three constraints shape it, and they are the parts worth knowing even if you never use the
process:

- **The brief and the approved scenarios are the source of truth for expected behaviour**; the
  application is the source of truth only for what it currently does. An expectation derived
  from observed behaviour produces a test that agrees with the bug.
- **An assistant proposes, a human approves and merges.** No assistant approves a business
  expectation, authorizes a run against a live site, promotes a scenario to active regression,
  or merges its own change — and shared changes (the framework pin, `pytest.ini`, the CI
  workflow) are proposed separately, with a reason, never as a side effect of adding a test.
- **Prompt text enforces nothing.** What enforces anything here is executable: Ruff, Black and
  mypy; `--strict-markers`; the `-m "not production"` exclusion on every pytest invocation in
  CI, guarded by `tests/test_ci_production_exclusion.py` (§8); and human review. A YAML flag that
  no code reads is documentation, never a safety control.

Work in progress — drafts, recordings, exploration evidence — lives in `artifacts/ai-work/`,
which is git-ignored.

### The scenario catalog

Approved scenarios are committed per application, at `apps/<app>/scenarios/<feature>.yaml`, so an
application stays self-contained (§1) — there is deliberately no top-level catalog tree. They
are a design and traceability record: nothing in the test runtime reads them, and the executable
truth is always the test named in a scenario's `automation.test`.

- **Schema**: shipped inside the installed framework as package data, and readable in its
  repository at [scenario.schema.json](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/pwpf/ai_testing/schemas/scenario.schema.json).
  JSON Schema 2020-12, versioned
  (`schema_version: "1.0"`). Unknown keys are rejected, so a misspelled field fails instead of
  being silently ignored — the same failure mode `AppConfig.extra` has for configuration (§6),
  avoided here deliberately.
- **Validation**: `python -m pwpf.ai_testing.validate_catalog` — schema, id uniqueness across every
  catalog, the lifecycle rules, and the scenario-to-test mappings in both directions. Static
  analysis: it parses YAML and reads `tests/` as an AST, never importing a test, starting a
  browser or opening a socket. CI runs it in its own `Scenario Catalog` job (§8).
- **Traceability**: the implementing test carries `@pytest.mark.scenario("<id>")` — registered
  in `pytest.ini` like every other marker — and the plugin attaches each id as an
  Allure label named `scenario`, beside `application`, `browser` and `environment`. One scenario
  is implemented by exactly one test; one test may cover several scenarios.
- **Dependencies**: the validator needs PyYAML and jsonschema, pinned in `requirements-ai.txt`
  and deliberately **not** in the test-runtime lock that every test job installs. It imports
  them lazily, and `tests/test_scenario_catalog.py` skips when they are absent.
- **What it cannot enforce**: that a recorded approval is genuine. `review.approved_by` plus
  `approved_date` are required from `APPROVED` onwards, and `ACTIVE_REGRESSION` additionally
  requires `ci_eligible: true` and no `production` marker — but a name and a date in YAML are
  only as true as the review behind them. The checks make skipping review visible, not
  impossible; that part stays human, as does merging.

A CLI or LLM orchestration is still **not implemented** and remains a separate, later decision;
`docs/ai-testing/README.md` records what is built and what is not.

## 12. Packaging and the pytest plugin

**This is now a dependency, not a part of this repository.** The framework is the
`playwright-pytest-framework` distribution, importable as `pwpf`, built from
[its own repository](https://github.com/abhay-scaler/playwright-pytest-framework). Its packaging - the `pytest11` entry point that makes the plugin
arrive without a `conftest.py`, the `ai` and `report` extras, the wheel manifest and the
installed-package verification - is documented and tested there.

What this repository is responsible for is the **pin**:

- `requirements.in` declares the framework at an immutable tag, with the extras this project
  needs (`[ai,report]`), and `requirements.txt` carries that requirement into the lock. The tag is
  never moved; the commit it resolved to is recorded beside it in `requirements.in`.
- `pip-compile` copies a VCS requirement into the lock as written, with the tag rather than the
  commit - unlike `pip freeze`, which rewrites it to the SHA. That is why the pairing is written
  down rather than assumed.
- `tests/test_extraction_dry_run.py` fails if the requirement stops naming a tag or a commit, or
  loses its extras.
- `scripts/extraction_dry_run.py` installs that exact requirement into a throwaway environment,
  copies this repository's `apps/` and `tests/<app>/` into a project of their own and runs them
  there, with this project on neither `sys.path` nor `PYTHONPATH`. 18 checks, including that the
  blocking smoke selection really executes and that a base install without the extras is rejected
  by this repository's `pytest.ini`.
- There is **no root `conftest.py`**. The entry point supplies the plugin; restoring a one-line
  conftest that imports `pwpf.plugin` is the first rollback lever if a framework release ever
  breaks discovery.

The extraction itself - what moved, what stayed, and why - is recorded in
[docs/stage4-extraction-proposal.md](docs/stage4-extraction-proposal.md) and
[docs/framework-extraction-readiness.md](docs/framework-extraction-readiness.md).
## Adding a New Application

The conventions a project must follow for the framework to work — the `tests/<app>/` + `apps/<app>/`
pairing, the one `app_config` fixture, the configuration keys — are stated in
[the framework's README](https://github.com/abhay-scaler/playwright-pytest-framework/blob/v0.1.0/docs/framework-readme-draft.md). What follows is the walkthrough for *this* repository, with its
own applications as the examples.

Follow these steps to onboard a new application, e.g. `checkout_app`. Nothing here requires
editing another application's files or the framework layer.

### 1. Create the application's configuration

```
apps/checkout_app/config/local.json
apps/checkout_app/config/ci.json
```

One JSON file per environment you need (matches whatever `ENVIRONMENT` values your team uses —
`local`/`ci` today, add `staging`/`prod` the same way if needed).

### 2. Define URLs, credentials, browser settings, timeouts, environment-specific values

Inside each environment's JSON:

```json
{
  "base_url": "https://checkout.staging.example.com",
  "action_timeout": 12000,
  "retry_count": 1,
  "ignore_https_errors": false,
  "secrets": {
    "api_key": "CHECKOUT_APP_API_KEY"
  }
}
```

- `base_url` — read by page objects as `self.config.base_url`. Omit/leave empty for a
  file-based app with no real URL (see `sample_app`).
- `action_timeout` — available as `self.config.action_timeout` for any explicit
  timeout in a page object.
- `retry_count` — auto-applied as a `pytest.mark.flaky(reruns=N)` override for every test under
  `tests/checkout_app/` (falls back to the global `--reruns` default in `pytest.ini` if omitted).
- `secrets` — **never put an actual secret value here.** Map a logical name to the *name* of an
  environment variable, then set that environment variable locally (`.env`, shell export) or as a
  CI secret. Read it in a page object/test via `app_config.secret("api_key")`. If the environment
  variable isn't set, `.secret()` raises a clear error naming exactly which file to fix. A
  `detect-secrets` pre-commit hook (`.secrets.baseline`) is a backstop against an actual secret
  value landing here by mistake — it isn't a substitute for following the convention.
- `ignore_https_errors` — optional, defaults to `true` (omit the key entirely for that). Set to
  `false` only if this app's environment has a real certificate worth validating.
- Browser engine and headless mode are **framework-wide**, not per-app (`BROWSER`/`HEADLESS` env
  vars) — every application in a given run shares one browser process for launch efficiency. If an
  application genuinely needs a different browser engine than the rest of the suite, that's a real
  architectural change (a per-test browser fixture instead of session-scoped) — flag it rather
  than working around it, since it changes the performance characteristics of the whole suite.
- **Optional app-specific keys** — anything in the JSON beyond `base_url`/`action_timeout`/
  `retry_count`/`secrets` lands in `app_config.extra`. `web_search` uses this for a
  `consent_selector` key: if the target site shows a cookie/consent banner, set
  `"consent_selector": "text=Accept all"` (or whatever selector matches) and call
  `self.dismiss_if_visible(self.config.extra["consent_selector"])` early in the page object's
  `open()` — it's a no-op if the banner never appears, so it's safe to call unconditionally.
  `web_search`'s own config leaves this `null` since `playwright.dev` has no such banner.

### 3. Where application-specific page objects/components go

```
apps/checkout_app/pages/checkout_page.py
apps/checkout_app/locators/checkout_locators.py
```

```python
# apps/checkout_app/locators/checkout_locators.py
class CheckoutLocators:
    PAY_BUTTON = "#pay"

# apps/checkout_app/pages/checkout_page.py
from core.base_page import BasePage
from apps.checkout_app.locators.checkout_locators import CheckoutLocators

class CheckoutPage(BasePage):
    def open(self) -> None:
        self.goto(self.config.base_url)

    def pay(self) -> None:
        self.click(CheckoutLocators.PAY_BUTTON)
```

Don't forget `apps/checkout_app/__init__.py`, `apps/checkout_app/pages/__init__.py`, and
`apps/checkout_app/locators/__init__.py` (empty files — they make the folders importable
packages, matching every other app).

### 4. Create the fixtures the application needs

Exactly one file, one fixture:

```python
# tests/checkout_app/conftest.py
import pytest
from core.app_config import load_app_config

@pytest.fixture(scope="session")
def app_config():
    return load_app_config("checkout_app")
```

If the application needs extra fixtures beyond `app_config` (e.g. a logged-in session), add them
to this same `conftest.py` — they'll only be visible to `checkout_app`'s own tests, never leaking
into other applications.

### 5. Where application-specific test data lives

```
apps/checkout_app/testdata/
```

Only needed for static fixtures (sample HTML, JSON payloads, seed files) the app's own tests load
directly — mirrors `apps/sample_app/testdata/`.

### 6. Create the first smoke test

```
tests/checkout_app/smoke/test_checkout_smoke.py
```

```python
import pytest
from apps.checkout_app.pages.checkout_page import CheckoutPage

@pytest.mark.smoke
def test_checkout_page_loads(page, app_config):
    checkout_page = CheckoutPage(page, app_config)
    checkout_page.open()
    assert checkout_page.page.title() != ""
```

The `app_config` fixture comes from the `conftest.py` created in step 4 — Pytest resolves it
automatically because the test lives under `tests/checkout_app/`.

### 7. Execute tests for a specific application and environment

```bash
# local environment (default)
pytest tests/checkout_app

# a specific environment
ENVIRONMENT=ci pytest tests/checkout_app

# just this app's smoke suite
pytest tests/checkout_app/smoke

# this app's smoke tests, headed, against a non-default browser
BROWSER=firefox HEADLESS=false pytest tests/checkout_app/smoke
```

### 8. Integrate into CI/CD

**Nothing to change for basic execution** — the Regression job already runs `pytest -n auto` over
all of `tests/`, so `tests/checkout_app/` is picked up automatically. If any of its tests carry
`@pytest.mark.smoke`, they're automatically included in the PR Smoke job too.

If the new application needs a secret in CI, add it as a GitHub Actions secret and expose it as an
env var in the workflow's `env:` block, using the same variable name referenced in
`apps/checkout_app/config/ci.json`'s `secrets` map — nothing else changes.

Only add a dedicated CI job/matrix entry for this application if you have a real reason to isolate
it (separate schedule, separate secret scope, much longer runtime) — not by default.

### 9. How reporting, screenshots, traces, and logs identify the application

All automatic — no extra code needed once the app follows the `tests/checkout_app/...`
convention:

- Screenshots/traces/videos on failure land under `screenshots|traces|videos/checkout_app/`.
- Allure results carry an `application: checkout_app` label on every test.
- Logger names inside `apps/checkout_app/...` files read as
  `apps.checkout_app.pages.checkout_page` in `logs/<worker>/framework.log`.
- Test node IDs in the HTML report already read `tests/checkout_app/...`.

### 10. Files a developer needs to modify when adding a new application

**New files only — nothing existing needs to change:**

- `apps/checkout_app/__init__.py`, `pages/__init__.py`, `locators/__init__.py`
- `apps/checkout_app/config/local.json` (+ `ci.json`, etc.)
- `apps/checkout_app/pages/*.py`, `apps/checkout_app/locators/*.py`
- `apps/checkout_app/testdata/*` (if needed)
- `tests/checkout_app/conftest.py`
- `tests/checkout_app/<suite>/test_*.py`

The only case that touches a shared file is a **new secret in CI** (adding a GitHub Actions
secret + one `env:` line in `ci.yml`) — and even that never requires editing another
application's tests, and none to the framework.
