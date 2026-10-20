#!/usr/bin/env python3
"""Check or fix license headers in repository files across many languages.

Standard library only. See ../SKILL.md for the full description.

Usage::

    python3 license_header_check.py --header-file HEADER.txt            # check
    python3 license_header_check.py --header-file HEADER.txt --fix      # insert/replace
    python3 license_header_check.py --header-file HEADER.txt a.py b.ts  # limit to paths
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_EXCLUSIONS_NAME = ".license-header-exclusions"
PRUNED_DIRS = {".git", "node_modules", "target", "build", "dist", "__pycache__", "vendor", ".venv", "venv"}
_LICENSE_MARKERS = re.compile(r"copyright|licen[cs]e|apache|spdx", re.IGNORECASE)
_BOM = "\ufeff"


# ---------------------------------------------------------------------------
# Comment styles
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommentStyle:
    """Comment syntax for one family of file types.

    Line styles set ``line_prefix``. Block styles set ``block_open``, ``block_close``
    and optionally ``block_prefix`` (the prefix for inner lines).
    """

    name: str
    line_prefix: Optional[str] = None
    block_open: Optional[str] = None
    block_prefix: str = ""
    block_close: Optional[str] = None

    @property
    def is_block(self) -> bool:
        return self.block_open is not None

    def render(self, header_lines: Sequence[str]) -> List[str]:
        if not self.is_block:
            assert self.line_prefix is not None
            return [f"{self.line_prefix} {line}" if line else self.line_prefix for line in header_lines]
        assert self.block_open is not None and self.block_close is not None
        body = [f"{self.block_prefix}{line}".rstrip() if line else self.block_prefix.rstrip()
                for line in header_lines]
        return [self.block_open, *body, self.block_close]


STYLES: Dict[str, CommentStyle] = {
    "slash": CommentStyle("slash", line_prefix="//"),
    "hash": CommentStyle("hash", line_prefix="#"),
    "dash": CommentStyle("dash", line_prefix="--"),
    "semicolon": CommentStyle("semicolon", line_prefix=";;"),
    "percent": CommentStyle("percent", line_prefix="%"),
    "batch": CommentStyle("batch", line_prefix="REM"),
    "vb": CommentStyle("vb", line_prefix="'"),
    "css": CommentStyle("css", block_open="/*", block_prefix=" * ", block_close=" */"),
    "markup": CommentStyle("markup", block_open="<!--", block_prefix="  ", block_close="-->"),
    "ml-block": CommentStyle("ml-block", block_open="(*", block_prefix=" * ", block_close=" *)"),
}

# Default mappings. Extensions are lower case and include the dot.
DEFAULT_EXTENSIONS: Dict[str, str] = {
    ".java": "slash", ".kt": "slash", ".kts": "slash", ".scala": "slash", ".groovy": "slash",
    ".go": "slash", ".rs": "slash", ".c": "slash", ".h": "slash", ".cc": "slash", ".cpp": "slash",
    ".hpp": "slash", ".cs": "slash", ".swift": "slash", ".js": "slash", ".mjs": "slash",
    ".cjs": "slash", ".jsx": "slash", ".ts": "slash", ".tsx": "slash", ".php": "slash",
    ".dart": "slash", ".proto": "slash", ".gradle": "slash",
    ".py": "hash", ".rb": "hash", ".sh": "hash", ".bash": "hash", ".zsh": "hash", ".pl": "hash",
    ".r": "hash", ".yml": "hash", ".yaml": "hash", ".toml": "hash", ".ini": "hash", ".cfg": "hash",
    ".conf": "hash", ".properties": "hash", ".ps1": "hash", ".tf": "hash", ".nix": "hash",
    ".ex": "hash", ".exs": "hash", ".cmake": "hash", ".imports": "hash", ".cnf": "hash",
    ".sql": "dash", ".lua": "dash", ".hs": "dash", ".elm": "dash",
    ".clj": "semicolon", ".cljs": "semicolon", ".el": "semicolon", ".lisp": "semicolon", ".scm": "semicolon",
    ".tex": "percent", ".erl": "percent",
    ".css": "css", ".scss": "css", ".less": "css",
    ".html": "markup", ".htm": "markup", ".xml": "markup", ".vue": "markup", ".svg": "markup",
    ".xhtml": "markup", ".md": "markup",
    ".ml": "ml-block", ".mli": "ml-block", ".fs": "ml-block", ".fsx": "ml-block",
    ".bat": "batch", ".cmd": "batch",
    ".vb": "vb",
}

DEFAULT_FILENAMES: Dict[str, str] = {
    "Dockerfile": "hash", "Makefile": "hash", "Gemfile": "hash", "Rakefile": "hash",
    ".gitignore": "hash", ".gitattributes": "hash", ".editorconfig": "hash",
    ".dockerignore": "hash", ".helmignore": "hash", ".gitleaksignore": "hash", ".npmrc": "hash",
    ".browserslistrc": "hash",
}

DEFAULT_GLOBS: Tuple[Tuple[str, str], ...] = (
    ("**/requirements*.txt", "hash"),
    ("**/META-INF/services/*", "hash"),
)


@dataclass
class StyleMap:
    extensions: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_EXTENSIONS))
    filenames: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_FILENAMES))
    globs: List[Tuple[str, str]] = field(default_factory=lambda: list(DEFAULT_GLOBS))

    def resolve(self, path: str) -> Optional[CommentStyle]:
        for pattern, style_name in self.globs:
            if glob_to_regex(pattern).fullmatch(path):
                return STYLES[style_name]
        name = path.rsplit("/", 1)[-1]
        if name in self.filenames:
            return STYLES[self.filenames[name]]
        # Try the longest suffix first so that multi-part extensions such as .tf.json can match.
        parts = name.lower().split(".")[1:]
        for i in range(len(parts)):
            suffix = "." + ".".join(parts[i:])
            if suffix in self.extensions:
                return STYLES[self.extensions[suffix]]
        return None


def load_style_map(path: Optional[Path], base: StyleMap) -> StyleMap:
    """Return ``base`` extended with the JSON mappings in ``path`` (if given)."""
    if path is None:
        return base
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read style map {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"style map {path} must be a JSON object")
    for section in ("extensions", "filenames", "globs"):
        if section in data and not isinstance(data[section], dict):
            raise ValueError(f"style map {path}: '{section}' must be an object")
    for key, style_name in data.get("extensions", {}).items():
        _check_style_name(path, style_name)
        base.extensions[key.lower()] = style_name
    for key, style_name in data.get("filenames", {}).items():
        _check_style_name(path, style_name)
        base.filenames[key] = style_name
    for pattern, style_name in data.get("globs", {}).items():
        _check_style_name(path, style_name)
        base.globs.insert(0, (pattern, style_name))
    return base


def _check_style_name(path: Path, style_name: str) -> None:
    if style_name not in STYLES:
        raise ValueError(f"style map {path}: unknown style '{style_name}' (see --list-styles)")


# ---------------------------------------------------------------------------
# Glob and exclusions
# ---------------------------------------------------------------------------

def glob_to_regex(pattern: str) -> "re.Pattern[str]":
    """Translate a gitignore-like glob into a regex over POSIX paths.

    ``**/`` matches zero or more directories, ``**`` matches anything,
    ``*`` matches within one path segment and ``?`` matches one character.
    """
    out: List[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


@dataclass(frozen=True)
class Exclusion:
    pattern: str
    reason: str
    regex: "re.Pattern[str]"


def load_exclusions(path: Path) -> List[Exclusion]:
    """Parse ``<glob>  # <reason>`` lines. A missing file means no exclusions."""
    if not path.is_file():
        return []
    rules: List[Exclusion] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pattern, sep, reason = line.partition("#")
        pattern, reason = pattern.strip(), reason.strip()
        if not sep or not reason:
            raise ValueError(f"{path}:{number}: exclusion '{pattern}' must state a reason after '#'")
        rules.append(Exclusion(pattern, reason, glob_to_regex(pattern)))
    return rules


def is_excluded(path: str, rules: Sequence[Exclusion]) -> bool:
    return any(rule.regex.fullmatch(path) for rule in rules)


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def list_repository_files(root: Path) -> List[str]:
    """Return repository-relative files: git-tracked plus untracked-not-ignored, or a directory walk."""
    if _is_git_repo(root):
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root, check=True, stdout=subprocess.PIPE,
        )
        names = {name for name in result.stdout.decode("utf-8").split("\0") if name}
        return sorted(name for name in names if (root / name).is_file())

    names_walk: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in PRUNED_DIRS]
        for filename in filenames:
            full = Path(dirpath) / filename
            names_walk.append(full.relative_to(root).as_posix())
    return sorted(names_walk)


def _is_git_repo(root: Path) -> bool:
    result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Header detection and rewriting
# ---------------------------------------------------------------------------

_XML_DECLARATION = re.compile(r"^<\?xml\b.*\?>\s*$")
_DOCTYPE = re.compile(r"^<!doctype\b", re.IGNORECASE)
_PYTHON_ENCODING = re.compile(r"^#.*coding[:=]")
_DOCKER_DIRECTIVE = re.compile(r"^#\s*(syntax|escape|check)\s*=", re.IGNORECASE)
_PHP_OPEN = re.compile(r"^<\?php\b")


def preamble_length(lines: Sequence[str], path: str, style: CommentStyle) -> int:
    """Count leading lines that must stay above the header (shebangs, encoding cookies, etc.)."""
    index = 0
    name = path.rsplit("/", 1)[-1]
    if index < len(lines) and lines[index].startswith("#!"):
        index += 1
    if path.endswith(".py") and index < len(lines) and _PYTHON_ENCODING.match(lines[index]):
        index += 1
    if name == "Dockerfile":
        while index < len(lines) and _DOCKER_DIRECTIVE.match(lines[index]):
            index += 1
    if path.endswith(".php") and index < len(lines) and _PHP_OPEN.match(lines[index]):
        index += 1
    if style is STYLES["markup"] and index < len(lines):
        if _XML_DECLARATION.match(lines[index]) or _DOCTYPE.match(lines[index]):
            index += 1
        elif path.endswith(".md") and lines[index].strip() == "---":
            for end in range(index + 1, len(lines)):
                if lines[end].strip() == "---":
                    return end + 1
    return index


def leading_comment_span(lines: Sequence[str], start: int, style: CommentStyle) -> int:
    """Return the number of lines of the leading comment beginning at ``start`` (0 if none)."""
    if start >= len(lines):
        return 0
    first = lines[start].lstrip()
    # Legacy C-style blocks are recognised for C-like and CSS files, even where the new header uses "//".
    if style is STYLES["slash"] or style is STYLES["css"]:
        if first.startswith("/*"):
            return _span_until(lines, start, "/*", "*/")
    if style.is_block:
        opener, closer = style.block_open, style.block_close
        assert opener is not None and closer is not None
        if first.startswith(opener):
            return _span_until(lines, start, opener, closer.strip())
        return 0
    prefix = style.line_prefix
    assert prefix is not None
    if first.startswith(prefix):
        end = start
        while end < len(lines) and lines[end].lstrip().startswith(prefix) and not lines[end].startswith("#!"):
            end += 1
        return end - start
    return 0


def _span_until(lines: Sequence[str], start: int, opener: str, closer: str) -> int:
    for end in range(start, len(lines)):
        probe = lines[end] if end > start else lines[end].lstrip()[len(opener):]
        if closer in probe:
            return end - start + 1
    return 0


def check_text(text: str, path: str, style: CommentStyle, header_lines: Sequence[str]) -> Optional[str]:
    """Return None when the header is correct, otherwise a human-readable reason."""
    lines = _strip_bom(text).splitlines()
    start = preamble_length(lines, path, style)
    expected = style.render(header_lines)
    actual = lines[start:start + len(expected)]
    if not actual or not _mentions_license(actual):
        return "missing license header"
    for offset, (want, got) in enumerate(zip(expected, actual)):
        if want != got:
            return f"header mismatch at line {start + offset + 1}: expected {want!r}, found {got!r}"
    if len(actual) < len(expected):
        return "license header is truncated"
    after = start + len(expected)
    if after < len(lines) and lines[after].strip() != "":
        return f"line {after + 1} must be blank after the license header"
    return None


def fix_text(text: str, path: str, style: CommentStyle, header_lines: Sequence[str]) -> str:
    """Return ``text`` with exactly one correct header, replacing a legacy license comment."""
    bom = _BOM if text.startswith(_BOM) else ""
    body = _strip_bom(text)
    newline = "\r\n" if "\r\n" in body else "\n"
    had_trailing_newline = body.endswith(("\n", "\r"))
    lines = body.splitlines()

    start = preamble_length(lines, path, style)
    span = leading_comment_span(lines, start, style)
    if span and _mentions_license(lines[start:start + span]):
        rest = lines[start + span:]
    else:
        rest = lines[start:]
    while rest and rest[0].strip() == "":
        rest = rest[1:]

    new_lines = [*lines[:start], *style.render(header_lines)]
    if rest:
        new_lines += ["", *rest]
    result = newline.join(new_lines)
    if had_trailing_newline or not rest:
        result += newline
    return bom + result


def _strip_bom(text: str) -> str:
    return text[1:] if text.startswith(_BOM) else text


def _mentions_license(lines: Iterable[str]) -> bool:
    return any(_LICENSE_MARKERS.search(line) for line in lines)


# ---------------------------------------------------------------------------
# Run and command line
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    path: str
    reason: str


def read_header(path: Path) -> List[str]:
    """Read the header body: keep inner blank lines, drop leading/trailing blank lines."""
    raw = path.read_text(encoding="utf-8").splitlines()
    while raw and raw[-1].strip() == "":
        raw.pop()
    while raw and raw[0].strip() == "":
        raw.pop(0)
    if not raw:
        raise ValueError(f"header file {path} is empty")
    return raw


def run(root: Path, exclusions_path: Path, paths: Sequence[str], fix: bool, header_lines: Sequence[str],
        style_map: StyleMap,
        reader: Callable[[Path], str] = lambda p: p.read_text(encoding="utf-8")) -> Tuple[List[Finding], List[str]]:
    """Check (and optionally fix) files; return (remaining findings, fixed paths)."""
    rules = load_exclusions(exclusions_path)
    candidates = [os.path.relpath(os.path.abspath(p), root).replace(os.sep, "/") for p in paths] \
        if paths else list_repository_files(root)
    findings: List[Finding] = []
    fixed: List[str] = []
    for relative in candidates:
        if is_excluded(relative, rules):
            continue
        style = style_map.resolve(relative)
        if style is None:
            findings.append(Finding(relative, "no comment syntax known for this file type; "
                                              "add a mapping (--style-map) or an exclusion with a reason"))
            continue
        file_path = root / relative
        if not file_path.is_file():
            findings.append(Finding(relative, "file not found"))
            continue
        try:
            text = reader(file_path)
        except UnicodeDecodeError:
            findings.append(Finding(relative, "not UTF-8 text; exclude binary files explicitly"))
            continue
        reason = check_text(text, relative, style, header_lines)
        if reason is None:
            continue
        if fix:
            file_path.write_text(fix_text(text, relative, style, header_lines), encoding="utf-8", newline="")
            fixed.append(relative)
        else:
            findings.append(Finding(relative, reason))
    return findings, fixed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", help="repository-relative files to process (default: all)")
    parser.add_argument("--header-file", type=Path, help="file containing the header body text")
    parser.add_argument("--fix", action="store_true", help="insert or replace headers in place")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: cwd)")
    parser.add_argument("--exclusions", type=Path, default=None, help="exclusion rule file")
    parser.add_argument("--style-map", type=Path, default=None, help="JSON file adding or overriding mappings")
    parser.add_argument("--list-styles", action="store_true", help="print supported comment styles and exit")
    args = parser.parse_args(argv)

    if args.list_styles:
        for name, style in STYLES.items():
            example = style.block_open + " ... " + style.block_close if style.is_block \
                else f"{style.line_prefix} ..."
            print(f"{name:10} {example}")
        return 0

    if args.header_file is None:
        print("error: --header-file is required", file=sys.stderr)
        return 2

    root = args.root.resolve()
    exclusions = args.exclusions or (root / DEFAULT_EXCLUSIONS_NAME)
    try:
        header_lines = read_header(args.header_file)
        style_map = load_style_map(args.style_map, StyleMap())
        findings, fixed = run(root, exclusions, args.paths, args.fix, header_lines, style_map)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for path in fixed:
        print(f"fixed: {path}")
    for finding in findings:
        print(f"{finding.path}: {finding.reason}", file=sys.stderr)
    if findings:
        print(f"\n{len(findings)} file(s) without a valid license header.", file=sys.stderr)
        return 1
    print(f"license headers ok ({len(fixed)} fixed)" if args.fix else "license headers ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
