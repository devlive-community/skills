#!/usr/bin/env bash
# Maintain the project-memory structure under <project>/.claude/.
#
# Usage:
#   memory.sh init  [project-root]   # create missing files; never overwrites existing content
#   memory.sh check [project-root]   # report structure, index, git-ignore, and size problems
#
# project-root defaults to the git top-level directory, or the current directory.

set -uo pipefail

cmd="${1:-}"
root="${2:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
dir="$root/.claude"
mem="$dir/memory"
entry="$dir/CLAUDE.md"
index="$mem/features/INDEX.md"
today="$(date +%F)"

write_if_missing() { # <path> <content>
  if [[ -e "$1" ]]; then
    echo "  keep    ${1#$root/}"
  else
    mkdir -p "$(dirname "$1")"
    printf '%s\n' "$2" > "$1"
    echo "  create  ${1#$root/}"
  fi
}

ensure_import() { # <line-to-find> <line-to-append>
  grep -qF "$1" "$entry" || { printf '%s\n' "$2" >> "$entry"; echo "  append  import $1 → .claude/CLAUDE.md"; }
}

init() {
  echo "project-memory init: $root"
  write_if_missing "$entry" "# Project Memory Entry Point

> Maintained by the project-memory skill and loaded automatically by Claude Code.
> Do not remove the import lines below. Append imports here for any new always-loaded memory.

## Always-Loaded Memory
- User habits and preferences: @memory/preferences.md
- Project conventions: @memory/conventions.md
- Feature memory index: @memory/features/INDEX.md

Detailed feature memory lives in memory/features/<feature-name>.md. Read it when needed using the index above."

  ensure_import "@memory/preferences.md" "- User habits and preferences: @memory/preferences.md"
  ensure_import "@memory/conventions.md" "- Project conventions: @memory/conventions.md"
  ensure_import "@memory/features/INDEX.md" "- Feature memory index: @memory/features/INDEX.md"

  write_if_missing "$mem/preferences.md" "# User Preferences

> How the user likes to work in this project. One bullet per preference, newest wording wins.

## Communication

## Workflow

## Tooling

_Last updated: ${today}_"

  write_if_missing "$mem/conventions.md" "# Project Conventions

> Rules every contributor (human or AI) follows in this repository.

## Code Style

## Architecture

## Git and Commits

## Testing and CI

## Prohibited Patterns

_Last updated: ${today}_"

  write_if_missing "$index" "# Feature Memory Index

> Add or update one row whenever a feature is completed or modified. See the linked file for details.

| Feature | File | Summary | Updated |
|---------|------|---------|---------|"

  check_ignored
}

check_ignored() {
  git -C "$root" rev-parse --git-dir >/dev/null 2>&1 || return 0
  local f rel hit
  for f in "$entry" "$mem/preferences.md" "$mem/conventions.md" "$index"; do
    rel="${f#$root/}"
    if git -C "$root" check-ignore -q --no-index "$rel" 2>/dev/null; then
      hit="$(git -C "$root" check-ignore -v --no-index "$rel" 2>/dev/null)"
      echo "  WARN    $rel is git-ignored ($hit)"
      problems=$((problems + 1))
    fi
  done
}

check() {
  problems=0
  echo "project-memory check: $root"
  [[ -f "$entry" ]] || { echo "  MISSING .claude/CLAUDE.md (run: memory.sh init)"; exit 1; }

  local imp
  for imp in "@memory/preferences.md" "@memory/conventions.md" "@memory/features/INDEX.md"; do
    if ! grep -qF "$imp" "$entry"; then
      echo "  WARN    .claude/CLAUDE.md does not import $imp"; problems=$((problems + 1))
    elif grep -F "$imp" "$entry" | grep -q '`'; then
      echo "  WARN    import $imp is inside backticks and will not load"; problems=$((problems + 1))
    fi
    [[ -f "$dir/${imp#@}" ]] || { echo "  WARN    imported file .claude/${imp#@} does not exist"; problems=$((problems + 1)); }
  done

  if grep -qE '@memory/features/[^I][^ ]*\.md' "$entry"; then
    echo "  WARN    .claude/CLAUDE.md imports an individual feature file; list it in INDEX.md instead"
    problems=$((problems + 1))
  fi

  if [[ -f "$index" ]]; then
    local f base
    for f in "$mem"/features/*.md; do
      [[ -e "$f" ]] || continue
      base="$(basename "$f")"
      [[ "$base" == "INDEX.md" ]] && continue
      grep -qF "| $base |" "$index" || grep -qF "($base)" "$index" || {
        echo "  WARN    features/$base has no row in INDEX.md"; problems=$((problems + 1)); }
    done
    for base in $(grep -oE '[a-z0-9][a-z0-9-]*\.md' "$index" | grep -v '^INDEX\.md$' | sort -u); do
      [[ -f "$mem/features/$base" ]] || {
        echo "  WARN    INDEX.md lists $base but the file does not exist"; problems=$((problems + 1)); }
    done
  fi

  local lines
  lines=$(cat "$entry" "$mem/preferences.md" "$mem/conventions.md" "$index" 2>/dev/null | wc -l | tr -d ' ')
  if (( lines > 400 )); then
    echo "  WARN    always-loaded memory is $lines lines; prune or move detail into feature files"
    problems=$((problems + 1))
  fi

  if grep -rEniq 'BEGIN [A-Z ]*PRIVATE KEY|(api[_-]?key|secret|token|password)[[:space:]]*[:=][[:space:]]*[A-Za-z0-9_\-]{12,}' "$dir/CLAUDE.md" "$mem" 2>/dev/null; then
    echo "  WARN    memory appears to contain a secret; remove it before committing"
    problems=$((problems + 1))
  fi

  check_ignored

  if (( problems > 0 )); then echo "project-memory check: $problems problem(s)"; exit 1; fi
  echo "project-memory check: OK (always-loaded memory: $lines lines)"
}

case "$cmd" in
  init)  problems=0; init ;;
  check) check ;;
  *) echo "usage: memory.sh {init|check} [project-root]" >&2; exit 2 ;;
esac
