# Other CI systems

The rules from `SKILL.md` apply unchanged: job-level gating, one job per component, one trigger per commit, full run when the base is unknown, and a final status that passes when jobs are skipped.

## GitLab CI

GitLab evaluates `rules:changes` at pipeline creation, so unaffected jobs are never created. Use it natively; the YAML anchors are the single source of truth (do not keep a parallel `components.conf`).

```yaml
workflow:
  rules:
    # Merge request pipelines: safe to auto-cancel, always diffed against the target branch.
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      auto_cancel:
        on_new_commit: interruptible
    # A branch push that already has an open MR: the MR pipeline covers it. Avoid the duplicate.
    - if: $CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS
      when: never
    # Long-lived branches: never auto-cancel (each pipeline diffs against its own before-commit).
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH || $CI_COMMIT_BRANCH == "dev"
      auto_cancel:
        on_new_commit: none
    - if: $CI_PIPELINE_SOURCE == "web" || $CI_PIPELINE_SOURCE == "schedule"

.ci-wiring: &ci-wiring
  - .gitlab-ci.yml
  - .gitlab/ci/**/*

.java-paths: &java-paths
  - backend/**/*
  - pom.xml
  - .mvn/**/*
  - mvnw*

.rust-paths: &rust-paths
  - "**/*.rs"
  - "**/Cargo.toml"
  - Cargo.lock
  - rust-toolchain.toml

java:
  stage: test
  image: maven:3.9-eclipse-temurin-21
  interruptible: true
  rules:
    - changes: *ci-wiring
    - changes: *java-paths
  cache:
    key: maven
    paths: [.m2/repository]
  variables:
    MAVEN_OPTS: -Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository
  script:
    - mvn -B -ntp verify

rust:
  stage: test
  image: rust:1
  interruptible: true
  rules:
    - changes: *ci-wiring
    - changes: *rust-paths
  script:
    - rustup component add rustfmt clippy
    - cargo fmt --all --check
    - cargo clippy --workspace --all-targets --locked -- -D warnings
    - cargo test --workspace --locked

# Guarantees a pipeline exists (and succeeds) for docs-only merge requests.
ci-ok:
  stage: .post
  image: alpine:3
  script:
    - echo "all selected jobs passed"
```

Notes:

- `rules:changes` is true for pipelines without a diff (tags, schedules, manual runs, first push of a branch), which gives the required full run.
- GitLab matches `changes` paths with `fnmatch`; `**/` matches zero or more directories and `dir/**/*` covers a whole directory.
- `workflow:rules:auto_cancel` needs GitLab 16.8 or later. On older instances leave auto-cancel off for branch pipelines.
- For very large monorepos, generate a child pipeline: run `changed-components.sh` in a `generate` job, write only the needed jobs to a YAML artifact, and trigger it with `trigger: include: artifact:`.
- Verify with `glab ci lint` or the project's CI Lint page.

## Jenkins (declarative pipeline)

Run the detector once, export its result, and gate stages with `when`. Use the last successful commit as the base so aborted builds never lose coverage.

```groovy
stage('Changes') {
  steps {
    script {
      def base = env.CHANGE_TARGET ? "origin/${env.CHANGE_TARGET}" : (env.GIT_PREVIOUS_SUCCESSFUL_COMMIT ?: '')
      def out = sh(returnStdout: true, script: base ? "bash .ci/changed-components.sh --base ${base}" : 'bash .ci/changed-components.sh --all').trim()
      out.split('\n').each { line -> def kv = line.split('=', 2); env["CHANGED_${kv[0].toUpperCase()}"] = kv[1] }
    }
  }
}
stage('Java') {
  when { environment name: 'CHANGED_JAVA', value: 'true' }
  steps { sh './mvnw -B -ntp verify' }
}
```

Use `disableConcurrentBuilds(abortPrevious: true)` only for pull request jobs.

## Azure Pipelines

```yaml
jobs:
  - job: changes
    steps:
      - checkout: self
        fetchDepth: 0
      - bash: |
          # Use the env var: the $(...) macro stays literal on non-PR builds.
          if [ -n "${SYSTEM_PULLREQUEST_TARGETBRANCH:-}" ]; then
            base="origin/${SYSTEM_PULLREQUEST_TARGETBRANCH#refs/heads/}"
            out=$(bash .ci/changed-components.sh --base "$base")
          else
            out=$(bash .ci/changed-components.sh --all)
          fi
          echo "$out" | while IFS='=' read -r k v; do echo "##vso[task.setvariable variable=$k;isOutput=true]$v"; done
        name: detect
  - job: java
    dependsOn: changes
    condition: eq(dependencies.changes.outputs['detect.java'], 'true')
    steps:
      - script: ./mvnw -B -ntp verify
```

Use `trigger:` for long-lived branches and `pr:` for pull requests; do not trigger CI on every branch. Branch builds run everything here because Azure exposes no before-commit; to narrow them, pass the commit of the last successful build as `--base`. Use `batch: true` on the branch trigger instead of cancelling.

## CircleCI

Use a setup workflow (`setup: true`) with the `circleci/path-filtering` orb, mapping path regexes to pipeline parameters, and gate each workflow with `when: << pipeline.parameters.<component> >>`. Alternatively run `changed-components.sh` in the setup job and pass the parameters to the `continuation` orb.

## Bitbucket Pipelines

Gate steps with `condition: changesets: includePaths: [...]` in the `pull-requests` section; keep `branches` pipelines only for long-lived branches.
