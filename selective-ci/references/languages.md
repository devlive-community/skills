# Per-language rules

For each ecosystem: the path patterns that must trigger it, the single-pass command chain (each line compiles at most once), and the cache. Replace `<dir>/` with the component directory when the language owns one; drop it for root-level projects.

Pattern syntax follows `scripts/changed-components.sh`: `**/` matches zero or more directories, `*` matches anything including `/`.

## Java / Kotlin with Maven

- Paths: `<dir>/**`, `**/pom.xml`, `.mvn/**`, `mvnw`, `mvnw.cmd`
- Command: `./mvnw -B -ntp verify` (compile, test, package and verify plugins in one pass). Never pass `-DskipTests` in CI.
- Do not: run `mvn compile`, `mvn test` and `mvn package` as separate steps; run `install` unless a later step in the same job consumes the local repository.
- Cache: `actions/setup-java` with `cache: maven`.
- Multi-module: build only affected modules and their dependents with `-pl <m1>,<m2> -am -amd`. Derive modules from changed directories; fall back to the full reactor when a parent `pom.xml` changes.

## Java / Kotlin with Gradle

- Paths: `<dir>/**`, `**/*.gradle`, `**/*.gradle.kts`, `gradle/**`, `gradlew`, `gradlew.bat`, `gradle.properties`, `settings.gradle*`, `gradle/libs.versions.toml`
- Command: `./gradlew build` (includes `check` and `test`). Do not add a separate `./gradlew test`.
- Cache: `gradle/actions/setup-gradle` (do not also cache `~/.gradle` manually).
- Android: `./gradlew assembleDebug testDebugUnitTest lintDebug` in one invocation.

## Rust

- Paths: `**/*.rs`, `**/Cargo.toml`, `Cargo.lock`, `rust-toolchain`, `rust-toolchain.toml`, `.cargo/**`, `**/build.rs`, plus non-Rust inputs embedded with `include_str!`/`include_bytes!` or used by `build.rs`
- Command: `cargo fmt --all --check`, `cargo clippy --workspace --all-targets --locked -- -D warnings`, `cargo test --workspace --locked`. Clippy and test share the target directory; do not add `cargo build`.
- Cache: `Swatinem/rust-cache@v2`.
- Workspace: test affected crates with `-p <crate>` when crates own directories; run the whole workspace when `Cargo.lock` or the root `Cargo.toml` changes.

## Python

- Paths: `**/*.py`, `**/*.pyi`, `pyproject.toml`, `uv.lock`, `poetry.lock`, `requirements*.txt`, `setup.cfg`, `setup.py`, `tox.ini`, `.python-version`, `pytest.ini`, `conftest.py`
- Command (uv): `uv sync --frozen`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` (if configured), `uv run pytest`.
- Command (pip): install once with `pip install -e ".[dev]"`, then the same tools. Do not reinstall per step.
- Cache: `astral-sh/setup-uv` with `enable-cache: true`, or `actions/setup-python` with `cache: pip`.
- Matrix over Python versions only when `requires-python` promises a range; consider the oldest and newest only on pull requests.

## Node.js / TypeScript

- Paths: `<dir>/**`, `package.json`, the lockfile (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lockb`, `bun.lock`), `pnpm-workspace.yaml`, `.nvmrc`, `.node-version`, `tsconfig*.json`, lint and bundler configs
- Command: one frozen install (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`, `bun install --frozen-lockfile`), then lint, test, build. If `build` runs `tsc` or `vue-tsc`, do not add a separate typecheck.
- Cache: `actions/setup-node` with `cache: npm|pnpm|yarn`.
- Workspaces: `pnpm -r --filter "...[origin/main]" run test`, `turbo run test --filter=...[origin/main]`, or `nx affected -t test` select affected packages inside one job.

## Go

- Paths: `**/*.go`, `go.mod`, `go.sum`, `go.work`, `go.work.sum`, `**/testdata/**`
- Command: `go vet ./...`, `go test -race ./...` (and `golangci-lint run` if configured, which replaces `go vet`). No separate `go build ./...`.
- Cache: `actions/setup-go` (cache enabled by default).

## .NET

- Paths: `**/*.cs`, `**/*.fs`, `**/*.csproj`, `**/*.fsproj`, `**/*.sln`, `**/*.slnx`, `Directory.Build.*`, `Directory.Packages.props`, `global.json`, `nuget.config`
- Command: `dotnet restore --locked-mode`, `dotnet build --no-restore -c Release`, `dotnet test --no-build -c Release`. The `--no-restore`/`--no-build` flags are what prevent the second compile.
- Cache: `actions/setup-dotnet` with `cache: true` (needs `packages.lock.json`).

## C / C++

- Paths: `**/*.c`, `**/*.cc`, `**/*.cpp`, `**/*.h`, `**/*.hpp`, `**/CMakeLists.txt`, `**/*.cmake`, `CMakePresets.json`, `conanfile.*`, `vcpkg.json`, `meson.build`
- Command: `cmake -S . -B build -G Ninja`, `cmake --build build`, `ctest --test-dir build --output-on-failure`.
- Cache: `ccache` via `hendrikmuhs/ccache-action`, plus the package manager cache.

## Swift

- Paths: `**/*.swift`, `Package.swift`, `Package.resolved`, `*.xcodeproj/**`, `*.xcworkspace/**`
- Command: `swift test` (builds once). For Xcode projects: a single `xcodebuild test`, not `build` then `test`.

## Ruby

- Paths: `**/*.rb`, `Gemfile`, `Gemfile.lock`, `*.gemspec`, `.ruby-version`, `Rakefile`
- Command: `bundle exec rubocop`, `bundle exec rake test` (or `rspec`).
- Cache: `ruby/setup-ruby` with `bundler-cache: true`.

## PHP

- Paths: `**/*.php`, `composer.json`, `composer.lock`, `phpunit.xml*`, `phpstan.neon*`
- Command: `composer install --no-progress`, `vendor/bin/phpstan analyse`, `vendor/bin/phpunit`.

## Dart / Flutter

- Paths: `**/*.dart`, `pubspec.yaml`, `pubspec.lock`, `analysis_options.yaml`
- Command: `flutter pub get`, `flutter analyze`, `flutter test` (or the `dart` equivalents).

## Containers

- Paths: `**/Dockerfile*`, `**/.dockerignore`, `compose*.yaml`, plus every path copied into the image.
- A Docker job usually needs the component jobs; gate it with the multi-component condition from `github-actions.md` and build the image from artifacts instead of compiling again inside the Dockerfile when the job already built them.

## Mixed stacks

- **Tauri / Electron**: Rust component (`src-tauri/**` or `crates/**`), web component (frontend directory), and a bundle job that runs only on `push` and needs both.
- **Backend serving a frontend** (Spring Boot with static assets, Django templates): the frontend component triggers its own job; also add its output path to the backend rule only if the backend build consumes it.
- **Shared schemas** (`proto/**`, `openapi/**`, `graphql/**`): list the pattern under every component that generates code from it.
- **Infrastructure as code** (`terraform/**`, `helm/**`, `k8s/**`): its own component with `terraform fmt -check`, `terraform validate`, `helm lint`; never part of `_all`.
