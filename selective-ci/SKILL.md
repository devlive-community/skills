---
name: selective-ci
description: Design or fix CI so only the components touched by a change are built and tested, every untouched language job is skipped, and nothing runs twice. Works for any language mix (Java, Kotlin, Rust, Python, Go, Node/TypeScript, .NET, C/C++, Swift, Ruby, PHP, Dart and more) on GitHub Actions, GitLab CI and other systems. Use when creating, editing or reviewing CI workflows, path filters, monorepo builds, or when CI is slow, redundant or runs jobs for unrelated changes.
---

# Selective CI

Goal: a change runs exactly the jobs it can affect, once. A Java change runs the Java job and nothing else. A docs-only change runs no build job at all. No component is ever built or tested twice for the same commit.

This skill is agent-neutral: it relies only on reading files, running shell commands and editing YAML. Paths below are relative to this skill's directory.

## Non-negotiable rules

1. **Gate at the job level, never inside steps.** An unaffected job must be skipped before a runner starts (`if:` on the job, `rules:` in GitLab). Starting a job and exiting early still costs a runner and is not a skip.
2. **One change-detection step, one source of truth.** A single `changes` job computes a boolean per component from the diff. Every component job reads those outputs. Do not scatter `paths:` filters across many workflows.
3. **One job per component.** Each language/module is built and tested by exactly one job (optionally a matrix over a real compatibility axis). No second workflow, no "build" job plus a "test" job that compiles the same code again.
4. **One trigger per commit.** `pull_request` for review, `push` only for long-lived branches. Never `push` on all branches together with `pull_request`.
5. **Fail safe toward running.** When the diff base is unknown (new branch, manual run, schedule, shallow clone), run everything. Never skip because detection failed.
6. **A single required status check.** An aggregator job (`ci-ok`) with `if: always()` is the only required check; it fails if any needed job failed or was cancelled and passes when jobs were skipped.
7. **CI wiring changes run everything.** Edits to the CI workflow, the detection script or its config trigger a full run (`_all` rule), because any job definition may have changed.

## Workflow

### 1. Discover

Before editing anything, inventory the repository:

- CI system and every existing pipeline file (`.github/workflows/*`, `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`, `.circleci/config.yml`, `bitbucket-pipelines.yml`).
- Components: each language root and build manifest (`pom.xml`, `build.gradle*`, `Cargo.toml`, `pyproject.toml`, `package.json`, `go.mod`, `*.csproj`, `CMakeLists.txt`, `Package.swift`, `Gemfile`, `composer.json`, `pubspec.yaml`, `Dockerfile`). Note whether languages live in separate directories or are mixed.
- Cross-component inputs: shared schemas (`proto/`, OpenAPI specs), generated code, shared scripts, Docker images that bundle several components, frontend embedded in a backend (Tauri, Spring static resources).
- Existing duplication: overlapping workflows, both `push` and `pull_request` on every branch, separate compile/test/package steps, matrices nobody needs, release workflows that rerun the full test suite.
- Branch model (`main`, `dev`, release branches), required status checks, and whether a merge queue is used. Ask the user if the required checks cannot be determined from the repository.

Summarize the plan to the user (components, their path rules, jobs kept/merged/removed) before rewriting large pipelines.

### 2. Define components and path rules

Copy `scripts/changed-components.sh` into the repository (default location `.ci/changed-components.sh`, executable) and create `.ci/components.conf`. Start from `assets/components.conf.example` and the per-language rules in `references/languages.md`.

Rules for good filters:

- Prefer directory rules (`backend/**`) when a language owns a directory; use extension rules (`**/*.py`) only for mixed layouts.
- Always include the manifest, lockfile, toolchain pin and wrapper of that language (`pom.xml`, `.mvn/**`, `mvnw*`, `Cargo.lock`, `rust-toolchain.toml`, `uv.lock`, `.nvmrc`, `go.sum`, `global.json`).
- Add a shared input to every component that consumes it (a `proto/**` change triggers Java and Python if both generate code from it).
- Map a composite action or helper script to the components that use it; put truly global files in `_all`.
- Put docs, licenses and editor config in `_ignore` so they never trigger anything.
- Exclude non-code files inside a component with `!` patterns only when they truly cannot affect the build.

Verify the rules locally before touching CI (see step 5).

### 3. Write the pipeline

- GitHub Actions: follow `references/github-actions.md` (complete template with `changes`, component jobs, dependent jobs and `ci-ok`).
- GitLab CI and other systems: follow `references/other-ci.md`.
- Use the single-pass command per ecosystem from `references/languages.md` so each job compiles once (for example `mvn verify`, not `compile` + `test` + `package`).
- Reuse the action versions, toolchain versions and cache setup already present in the repository; the templates show known-good majors at the time of writing.
- If the repository already uses `dorny/paths-filter` or GitLab `rules:changes` consistently, keep that mechanism and apply the same rules instead of replacing it.

### 4. Remove duplication

Check every item and fix what applies:

- [ ] Triggers: `pull_request` plus `push` restricted to long-lived branches; tag pushes are not matched by the CI workflow.
- [ ] Concurrency: `cancel-in-progress` for pull requests only. Do not cancel push runs: each push run diffs against its own `before` commit, so a cancelled push run would leave its changes untested.
- [ ] No overlapping workflows: merge per-language workflow files that duplicate the new jobs, then delete them. Release and deploy workflows build artifacts only and do not re-run tests that already passed for the same commit.
- [ ] Each job runs one build/test chain; no repeated install, compile or test step.
- [ ] A matrix exists only for a real support contract (OS, runtime version). Consider the full matrix on `push` and a single cell on pull requests.
- [ ] Caches are configured once per job through the setup action (`cache: maven`, `Swatinem/rust-cache`, `cache: pnpm`, `setup-uv` cache).
- [ ] Post-merge runs: keeping `push` on the default branch reruns the merged components once to validate the merged result. If the user wants zero reruns, use a merge queue (`merge_group`) and drop the `push` trigger for that branch. Confirm with the user before removing it.

### 5. Verify

Do not report success without evidence:

1. Run the detector against representative change sets and check the output:

   ```bash
   printf '%s\n' backend/src/Main.java | bash .ci/changed-components.sh --files - -v
   printf '%s\n' README.md docs/guide.md | bash .ci/changed-components.sh --files - -v
   printf '%s\n' .github/workflows/ci.yml | bash .ci/changed-components.sh --files - -v
   bash .ci/changed-components.sh --base origin/main -v
   ```

   Expected: only the owning component is `true`; docs-only gives `any=false`; CI wiring gives a full run. Cover every component, every shared input and at least one deletion or rename.

2. Lint the pipeline: `actionlint` for GitHub Actions, `shellcheck` for scripts, the GitLab CI lint API or `glab ci lint` for GitLab, when available. Report any tool that is not installed instead of skipping silently.
3. Read the final YAML once more for: job-level `if`, every component job listed in `ci-ok.needs`, no workflow-level `paths` filter on the required workflow, `fetch-depth` sufficient for the diff.
4. Tell the user to set `ci-ok` as the only required status check and to remove old per-language required checks; never change repository settings yourself.

## Reference files

| File | When |
|------|------|
| `references/github-actions.md` | GitHub Actions template, aggregator, dependent jobs, required checks, pitfalls |
| `references/languages.md` | Path rules, single-pass commands and caching per language; monorepo module selection |
| `references/other-ci.md` | GitLab CI, Jenkins, Azure Pipelines, CircleCI, Bitbucket |
| `scripts/changed-components.sh` | Portable change detector (bash 3.2+, git only); run with `--help` |
| `assets/components.conf.example` | Starting point for `.ci/components.conf` |

## Definition of done

- [ ] Every component has a path rule, a single job gated at the job level, and a single-pass command.
- [ ] Docs-only changes run no build job; CI wiring changes run everything; unknown base runs everything.
- [ ] No overlapping workflows, no duplicated triggers, no repeated compile/test inside a job.
- [ ] `ci-ok` aggregates all jobs and is documented as the only required check.
- [ ] Detector scenarios and linters were run, and their results were reported to the user.
- [ ] No push, tag, repository-setting or secret change was made without an explicit user request.
