# GitHub Actions

## Layout

```
.ci/
  changed-components.sh     # copied from this skill's scripts/
  components.conf           # path rules
.github/workflows/
  ci.yml                    # the only build/test workflow
  release.yml               # tags only; builds artifacts, does not rerun the test suite
```

## Template: `.github/workflows/ci.yml`

Adapt component names, toolchain versions and commands to the repository. Keep the structure.

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main, dev]        # long-lived branches only; tags do not match
  workflow_dispatch:             # manual run = full run

permissions:
  contents: read

concurrency:
  group: ci-${{ github.event.pull_request.number || github.ref }}
  # Safe for PRs (always diffed against the base). Unsafe for pushes (see pitfalls).
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  changes:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    outputs:
      java: ${{ steps.detect.outputs.java }}
      rust: ${{ steps.detect.outputs.rust }}
      python: ${{ steps.detect.outputs.python }}
      web: ${{ steps.detect.outputs.web }}
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0         # the diff needs the base commit
      - id: detect
        run: bash .ci/changed-components.sh --github-output -v

  java:
    needs: changes
    if: needs.changes.outputs.java == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-java@v5
        with:
          distribution: temurin
          java-version: '21'
          cache: maven
      - run: ./mvnw -B -ntp verify

  rust:
    needs: changes
    if: needs.changes.outputs.rust == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy
      - uses: Swatinem/rust-cache@v2
      - run: cargo fmt --all --check
      - run: cargo clippy --workspace --all-targets --locked -- -D warnings
      - run: cargo test --workspace --locked

  python:
    needs: changes
    if: needs.changes.outputs.python == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pytest

  web:
    needs: changes
    if: needs.changes.outputs.web == 'true'
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v5
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v5
        with:
          node-version-file: web/.nvmrc
          cache: pnpm
          cache-dependency-path: web/pnpm-lock.yaml
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm test
      - run: pnpm build           # if build already type-checks, do not also run tsc

  # The only required status check.
  ci-ok:
    if: always()
    needs: [changes, java, rust, python, web]
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - env:
          RESULTS: ${{ join(needs.*.result, ' ') }}
        run: |
          echo "job results: $RESULTS"
          case " $RESULTS " in
            *" failure "*|*" cancelled "*) exit 1 ;;
          esac
```

## Jobs that depend on several components

A job that `needs` a skipped job is skipped too, unless its condition overrides the default `success()`. Use:

```yaml
  e2e:
    needs: [changes, java, web]
    if: >-
      !cancelled()
      && !contains(needs.*.result, 'failure')
      && (needs.changes.outputs.java == 'true' || needs.changes.outputs.web == 'true')
```

Add every such job to `ci-ok.needs`.

## Dynamic matrix (many similar packages)

When components are homogeneous (for example 30 Python packages under `packages/`), use one matrix job instead of 30 jobs:

```yaml
  changes:
    outputs:
      components: ${{ steps.detect.outputs.components }}
      any: ${{ steps.detect.outputs.any }}
  test:
    needs: changes
    if: needs.changes.outputs.any == 'true'
    strategy:
      fail-fast: false
      matrix:
        component: ${{ fromJSON(needs.changes.outputs.components) }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: ./scripts/test.sh "${{ matrix.component }}"
```

The `if` is mandatory: an empty matrix is an error, not a skip.

## Large repositories

`fetch-depth: 0` is fine for most repositories because only the small `changes` job uses it. For very large histories:

```yaml
      - uses: actions/checkout@v5
        with:
          fetch-depth: 2         # PR merge commit + its first parent (the base)
      - if: github.event_name == 'push'
        env:
          BEFORE: ${{ github.event.before }}
        run: git fetch --no-tags --depth=1 origin "$BEFORE" || true
```

If the base still cannot be resolved, the detector falls back to a full run.

## Using dorny/paths-filter instead

If the repository already uses `dorny/paths-filter`, keep it: put the rules in its `filters:` block, gate jobs on its outputs exactly as above, and keep `ci-ok`. Add an explicit full-run override for `workflow_dispatch`/`schedule`, because the action does not do that on its own:

```yaml
      java: ${{ github.event_name == 'workflow_dispatch' || steps.filter.outputs.java == 'true' }}
```

## Pitfalls

- **Workflow-level `paths:` / `paths-ignore:` on a required workflow** leaves the required check "Expected - waiting" forever when the workflow does not start. Use job-level `if` instead.
- **Matrix job names as required checks** (`test (ubuntu-latest)`) never report when the job is skipped. Require only `ci-ok`.
- **Cancelling push runs** loses coverage: push 1 changes Java and is cancelled, push 2 changes docs, so Java is never verified on that branch. Cancel only pull request runs.
- **`push` on all branches + `pull_request`** runs everything twice for every PR commit.
- **Step-level `if`** still allocates a runner, checks out and sets up toolchains. Gate whole jobs.
- **`needs` on a skipped job** silently skips downstream jobs, including deploys. Use `!cancelled()` conditions as shown above.
- **Path rules missing the lockfile or toolchain file**: a dependency bump then skips the only job that would catch it.
- **`pull_request_target`** checks out the base branch by default; never run untrusted PR code with secrets in it.
- **Release on tags** should build from the tagged commit, which already passed `ci.yml` on its branch. If a test gate is required, call the CI jobs through `workflow_call` instead of copying them.
