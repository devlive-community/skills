"""Unit tests for scripts/license_header_check.py (stdlib unittest only)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "license_header_check.py"
_SPEC = importlib.util.spec_from_file_location("license_header_check", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
lhc = importlib.util.module_from_spec(_SPEC)
sys.modules["license_header_check"] = lhc
_SPEC.loader.exec_module(lhc)

HEADER = [
    "Copyright (c) 2026 Example Corp",
    "",
    "Licensed under the MIT License. See the LICENSE file in the",
    "project root for full license text.",
]
STYLE_MAP = lhc.StyleMap()


class RenderTests(unittest.TestCase):
    def test_line_style(self) -> None:
        out = lhc.STYLES["slash"].render(HEADER)
        self.assertEqual(out[0], "// Copyright (c) 2026 Example Corp")
        self.assertEqual(out[1], "//")

    def test_block_style(self) -> None:
        out = lhc.STYLES["css"].render(HEADER)
        self.assertEqual(out[0], "/*")
        self.assertEqual(out[-1], " */")

    def test_markup_style(self) -> None:
        out = lhc.STYLES["markup"].render(HEADER)
        self.assertEqual(out[0], "<!--")
        self.assertEqual(out[-1], "-->")


class ResolveTests(unittest.TestCase):
    def test_extension_and_filename(self) -> None:
        self.assertEqual(STYLE_MAP.resolve("a/b/Main.java").name, "slash")
        self.assertEqual(STYLE_MAP.resolve("deploy/Dockerfile").name, "hash")
        self.assertEqual(STYLE_MAP.resolve("x/requirements-dev.txt").name, "hash")

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(STYLE_MAP.resolve("data/blob.bin"))
        self.assertIsNone(STYLE_MAP.resolve("README"))

    def test_multi_part_extension_from_style_map(self) -> None:
        mapping = lhc.StyleMap()
        mapping.extensions[".tf.json"] = "hash"
        self.assertEqual(mapping.resolve("infra/main.tf.json").name, "hash")


class CheckAndFixTests(unittest.TestCase):
    def check(self, text: str, path: str) -> str | None:
        style = STYLE_MAP.resolve(path)
        assert style is not None
        return lhc.check_text(text, path, style, HEADER)

    def fix(self, text: str, path: str) -> str:
        style = STYLE_MAP.resolve(path)
        assert style is not None
        return lhc.fix_text(text, path, style, HEADER)

    def test_fixed_output_passes_check_for_many_types(self) -> None:
        samples = {
            "a.java": "class A {}\n",
            "b.py": "print(1)\n",
            "c.sh": "echo hi\n",
            "d.sql": "select 1;\n",
            "e.css": "a {}\n",
            "f.html": "<html></html>\n",
            "g.go": "package main\n",
            "h.ml": "let x = 1\n",
            "i.bat": "@echo off\r\n",
            "j.vb": "Module M\r\n",
        }
        for path, body in samples.items():
            with self.subTest(path=path):
                self.assertIsNotNone(self.check(body, path))
                fixed = self.fix(body, path)
                self.assertIsNone(self.check(fixed, path))

    def test_shebang_stays_first(self) -> None:
        fixed = self.fix("#!/usr/bin/env python3\nprint(1)\n", "tool.py")
        self.assertTrue(fixed.startswith("#!/usr/bin/env python3\n# Copyright"))
        self.assertIsNone(self.check(fixed, "tool.py"))

    def test_php_open_tag_stays_first(self) -> None:
        fixed = self.fix("<?php\necho 1;\n", "index.php")
        self.assertTrue(fixed.startswith("<?php\n// Copyright"))
        self.assertIsNone(self.check(fixed, "index.php"))

    def test_markdown_front_matter_stays_first(self) -> None:
        text = "---\ntitle: x\n---\n\n# Doc\n"
        fixed = self.fix(text, "doc.md")
        self.assertTrue(fixed.startswith("---\ntitle: x\n---\n<!--"))
        self.assertIsNone(self.check(fixed, "doc.md"))

    def test_legacy_license_comment_is_replaced(self) -> None:
        text = "/* Copyright 2019 Old Co. Apache-2.0 */\nclass A {}\n"
        fixed = self.fix(text, "A.java")
        self.assertNotIn("Old Co", fixed)
        self.assertIsNone(self.check(fixed, "A.java"))

    def test_documentation_comment_is_kept(self) -> None:
        text = "// Parses the input stream.\nclass A {}\n"
        fixed = self.fix(text, "A.java")
        self.assertIn("// Parses the input stream.", fixed)
        self.assertIsNone(self.check(fixed, "A.java"))

    def test_crlf_and_bom_preserved(self) -> None:
        text = "\ufeffclass A {}\r\n"
        fixed = self.fix(text, "A.java")
        self.assertTrue(fixed.startswith("\ufeff// Copyright"))
        self.assertIn("\r\n", fixed)
        self.assertNotRegex(fixed.replace("\r\n", "\n"), r"\n\n\n")
        self.assertTrue(fixed.endswith("\r\nclass A {}\r\n"))
        self.assertIsNone(self.check(fixed, "A.java"))

    def test_header_must_be_followed_by_blank_line(self) -> None:
        good = "\n".join(STYLE_MAP.resolve("A.java").render(HEADER)) + "\nclass A {}\n"
        self.assertIn("must be blank", self.check(good, "A.java"))


class ExclusionTests(unittest.TestCase):
    def test_reason_is_mandatory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ex"
            path.write_text("**/*.png\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                lhc.load_exclusions(path)

    def test_glob_and_reason_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ex"
            path.write_text("# comment\n**/*.png   # binary image\n", encoding="utf-8")
            rules = lhc.load_exclusions(path)
            self.assertTrue(lhc.is_excluded("img/a.png", rules))
            self.assertFalse(lhc.is_excluded("img/a.jpg", rules))


class EndToEndTests(unittest.TestCase):
    def test_run_fix_then_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
            (root / "data.png").write_bytes(b"\x89PNG")
            exclusions = Path(tmp).parent / (Path(tmp).name + ".excl")
            self.addCleanup(lambda: exclusions.unlink(missing_ok=True))
            exclusions.write_text("**/*.png  # binary image\n", encoding="utf-8")

            findings, fixed = lhc.run(root, exclusions, [], False, HEADER, STYLE_MAP)
            self.assertEqual([f.path for f in findings], ["src/a.ts"])

            findings, fixed = lhc.run(root, exclusions, [], True, HEADER, STYLE_MAP)
            self.assertEqual(fixed, ["src/a.ts"])
            self.assertEqual(findings, [])

            findings, _ = lhc.run(root, exclusions, [], False, HEADER, STYLE_MAP)
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
