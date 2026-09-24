#!/usr/bin/env bash
# Validate a commit message against the git-commit-convention skill.
#
# Usage:
#   check-commit-msg.sh <file>        # validate a message file
#   check-commit-msg.sh --head        # validate the HEAD commit message
#   echo "feat: add x" | check-commit-msg.sh
#
# Exit code 0 = OK, 1 = violations found (each printed on stderr).

set -uo pipefail

if [[ "${1:-}" == "--head" ]]; then
  msg="$(git log -1 --format=%B)"
elif [[ -n "${1:-}" && "${1}" != "-" ]]; then
  msg="$(cat "$1")"
else
  msg="$(cat)"
fi

# Drop git comment lines and trailing blank lines.
msg="$(printf '%s\n' "$msg" | grep -v '^#' | sed -e :a -e '/^[[:space:]]*$/{$d;N;ba' -e '}')"

errors=0
fail() { echo "✗ $*" >&2; errors=$((errors + 1)); }

header="$(printf '%s\n' "$msg" | head -n 1)"
second="$(printf '%s\n' "$msg" | sed -n 2p)"

types='feat|fix|perf|refactor|test|docs|style|i18n|build|ci|chore|revert'
if ! printf '%s' "$header" | grep -Eq "^($types)(\([a-z0-9][a-z0-9._/-]*\))?!?: [^ ]"; then
  fail "header must match '<type>(<scope>): <subject>' with type in: ${types//|/, } (got: $header)"
fi

if (( ${#header} > 72 )); then
  fail "header is ${#header} chars (max 72)"
fi

[[ "$header" == *. ]] && fail "header must not end with a period"

subject="${header#*: }"
first_word="$(printf '%s' "$subject" | awk '{print $1}')"
if [[ "$header" != revert:* ]]; then
  if printf '%s' "$first_word" | grep -Eq '^[A-Z]'; then
    fail "subject must start with a lowercase verb (got: $first_word)"
  fi
  lw="$(printf '%s' "$first_word" | tr '[:upper:]' '[:lower:]')"
  case "$lw" in
    added|fixed|updated|removed|changed|implemented|refactored|improved|created|deleted|\
    renamed|moved|bumped|upgraded|cleaned|replaced|introduced|supported|enabled|disabled|\
    adds|fixes|updates|removes|changes|implements|refactors|improves|creates|deletes|\
    renames|moves|bumps|upgrades|cleans|replaces|introduces|supports|enables|disables|\
    adding|fixing|updating|removing|changing|implementing|refactoring|improving)
      fail "subject must use imperative mood ('$first_word' → use the base verb)" ;;
  esac
  if printf '%s' "$subject" | grep -Eiq '^(fix(ed)? bugs?|update(d)? code|wip|temp|tmp|misc|changes|update|updates|minor (fix|changes)|some (fix|fixes|changes)|clean ?up code)$'; then
    fail "subject is too vague: '$subject'"
  fi
fi

if [[ -n "$second" ]]; then
  fail "line 2 must be blank (separates header from body)"
fi

lineno=0
while IFS= read -r line; do
  lineno=$((lineno + 1))
  (( lineno == 1 )) && continue
  [[ "$line" == *://* ]] && continue   # allow long URLs
  (( ${#line} > 100 )) && fail "line $lineno is ${#line} chars (max 100)"
done <<< "$msg"

if printf '%s' "$msg" | perl -CSD -ne 'exit 1 if /[\p{Han}\p{Hiragana}\p{Katakana}\p{Hangul}]/'; then :; else
  fail "message contains CJK characters (English only)"
fi

if printf '%s' "$msg" | grep -Eiq 'co-authored-by:.*(claude|anthropic|openai|chatgpt|gpt|copilot|cursor|gemini|codex)|generated (with|by) (claude|ai|chatgpt|copilot|cursor)|noreply@anthropic\.com|🤖'; then
  fail "message contains AI attribution (remove Co-Authored-By / Generated-with lines)"
fi

if printf '%s' "$msg" | grep -Eq '/Users/[^/ ]+/|/home/[^/ ]+/|[A-Z]:\\Users\\'; then
  fail "message contains an absolute personal path"
fi

if (( errors > 0 )); then
  echo "commit message check failed: $errors problem(s)" >&2
  exit 1
fi
echo "✓ commit message OK"
