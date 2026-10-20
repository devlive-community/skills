---
name: license-header-check
description: Check or insert license headers in source files across many languages (Java, TypeScript, JavaScript, Python, Go, Rust, C/C++, C#, Kotlin, Swift, PHP, Ruby, SQL, shell, YAML, TOML, HTML, XML, Markdown, CSS, Dockerfile and more). Use when the user asks to verify, add, fix, or enforce license/copyright headers in a repository, or to wire such a check into CI.
---

# license-header-check

A dependency-free (Python 3 standard library only) checker that verifies every
repository file carries the same license header, written with the comment syntax
of its file type. It can also insert or replace headers with `--fix`.

## Quick start

1. Write the header text to a plain file (one line per row; blank lines are kept):

   ```text
   Copyright (c) 2026 Example Corp

   Licensed under the MIT License. See the LICENSE file in the
   project root for full license text.
   ```

2. Check the repository:

   ```bash
   python3 scripts/license_header_check.py --header-file LICENSE_HEADER.txt
   ```

3. Insert or repair headers:

   ```bash
   python3 scripts/license_header_check.py --header-file LICENSE_HEADER.txt --fix
   ```

Exit codes: `0` ok, `1` files lack a valid header (or cannot be classified), `2` usage or configuration error.

## Options

| Option | Purpose |
|---|---|
| `--header-file PATH` | Required. Header body text. Trailing blank lines are dropped. |
| `--root DIR` | Repository root (default: current directory). |
| `--exclusions PATH` | Exclusion rules (default: `<root>/.license-header-exclusions` if present). |
| `--style-map PATH` | JSON file adding or overriding file-type mappings (see below). |
| `--fix` | Insert or replace headers in place. Only leading license-like comments are removed. |
| `--list-styles` | Print the supported comment styles and their extensions, then exit. |
| `paths...` | Limit the check to these repository-relative files. |

File discovery uses `git ls-files --cached --others --exclude-standard` inside a git
repository; otherwise it walks the directory tree and skips common dependency and
build directories (`.git`, `node_modules`, `target`, `build`, `dist`, `__pycache__`,
`vendor`, `.venv`).

## Exclusions

One rule per line: `<glob>  # <reason>`. A reason is mandatory. Blank lines and
lines starting with `#` are ignored. Supported glob syntax: `*`, `?`, `**/`, `**`.

```text
LICENSE                 # the license text itself
**/*.png                # binary image
**/*.json               # JSON does not allow comments
**/package-lock.json    # generated
```

Files whose type has no known comment syntax are reported as errors unless excluded,
so unknown file types force an explicit decision.

## Supported comment styles

| Style | Syntax | Default extensions and names |
|---|---|---|
| slash | `// ...` | .java .kt .kts .scala .groovy .go .rs .c .h .cc .cpp .hpp .cs .swift .js .mjs .cjs .jsx .ts .tsx .php .dart .proto .gradle |
| hash | `# ...` | .py .rb .sh .bash .zsh .pl .r .yml .yaml .toml .ini .cfg .conf .cnf .properties .imports .ps1 .tf .nix .ex .exs .cmake, Dockerfile, Makefile, .gitignore, .gitattributes, .editorconfig, .dockerignore, .helmignore, .gitleaksignore, `requirements*.txt` |
| dash | `-- ...` | .sql .lua .hs .elm |
| semicolon | `; ...` | .clj .cljs .el .lisp .scm |
| percent | `% ...` | .tex .erl |
| css | `/* ... */` | .css .scss .less |
| markup | `<!-- ... -->` | .html .htm .xml .vue .svg .md .xhtml |
| ml-block | `(* ... *)` | .ml .mli .fs .fsx |
| batch | `REM ...` | .bat .cmd |
| vb | `' ...` | .vb |

Preamble lines that must stay on top are preserved automatically: shebangs (`#!`),
Python encoding cookies, `<?php` opening tags, Dockerfile parser directives,
XML declarations, HTML doctypes and Markdown front matter.

To add or override a mapping, pass `--style-map` with JSON:

```json
{
  "extensions": { ".tf.json": "hash", ".mdx": "markup" },
  "filenames": { "Jenkinsfile": "slash" },
  "globs": { "scripts/*.tmpl": "hash" }
}
```

Glob entries take precedence over file names, which take precedence over extensions.

## Behaviour details

- A file is correct when its first comment block (after any preamble) matches the
  header exactly and is followed by a blank line.
- `--fix` replaces an existing leading comment only if it mentions copyright, license,
  SPDX or Apache. Other documentation comments are never removed.
- BOM, CRLF/LF line endings and trailing newlines are preserved.
- Non-UTF-8 files are reported and must be excluded explicitly.

## CI example

```yaml
- name: License headers
  run: python3 scripts/license_header_check.py --header-file LICENSE_HEADER.txt
```

## Tests

```bash
python3 -m unittest discover -s scripts/tests -v
```
