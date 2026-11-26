"""Check shipped Markdown against the actual CLI, without installing AI tools."""
import contextlib
import io
import re
import shlex
import unittest
from pathlib import Path

from steam_release_guard.cli import parser

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = [ROOT / name for name in ("README.md", "README.en.md", "CONTRIBUTING.md", "docs/USAGE.zh-CN.md", "AI-START.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md",
                                    "skills/steam-release-guard/SKILL.md")]
DOCUMENTS += sorted((ROOT / "workflows").glob("*.md"))
DOCUMENTS += [ROOT / "skills/steam-release-guard" / name for name in ("INSTALL.md", "INSTALL.en.md", "EXAMPLES.md")]


class MarkdownTests(unittest.TestCase):
    def test_bilingual_readmes_keep_identical_cli_examples(self):
        def commands(name):
            return [shlex.split(line) for line in (ROOT / name).read_text(encoding="utf-8").splitlines()
                    if line.startswith("python -m steam_release_guard ")]
        self.assertTrue(commands("README.md"))
        self.assertEqual(commands("README.md"), commands("README.en.md"))

    def test_documented_commands_parse_with_real_cli(self):
        commands = 0
        for path in DOCUMENTS:
            text = path.read_text(encoding="utf-8").replace("`\n", " ")
            for line in text.splitlines():
                if not line.startswith("python -m steam_release_guard "):
                    continue
                args = shlex.split(line)[3:]
                with self.subTest(file=path.name, command=line), contextlib.redirect_stdout(io.StringIO()):
                    if args in (["--version"], ["--help"], ["advanced", "--help"]):
                        with self.assertRaises(SystemExit) as caught:
                            parser().parse_args(args)
                        self.assertEqual(caught.exception.code, 0)
                    else:
                        parser().parse_args(args)
                commands += 1
        self.assertGreater(commands, 40, "Workflow command examples were not discovered")

    def test_local_markdown_links_and_client_imports_resolve(self):
        for path in DOCUMENTS:
            text = path.read_text(encoding="utf-8")
            links = re.findall(r"\]\(([^)]+)\)", text)
            links += re.findall(r"(?m)^@([^\s]+)$", text)
            for link in links:
                if "://" in link or link.startswith("#"):
                    continue
                with self.subTest(file=path.name, link=link):
                    target = (path.parent / link.split("#")[0]).resolve()
                    self.assertTrue(target.is_relative_to(ROOT))
                    self.assertTrue(target.is_file(), str(target))

    def test_skill_frontmatter_and_all_project_entries_reference_canonical_source(self):
        text = (ROOT / "skills/steam-release-guard/SKILL.md").read_text(encoding="utf-8")
        header = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(header)
        metadata = dict(line.split(": ", 1) for line in header.group(1).splitlines())
        self.assertEqual(metadata["name"], "steam-release-guard")
        self.assertTrue(0 < len(metadata["description"]) < 1024)
        for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "AI-START.md", "README.md"):
            self.assertIn("skills/steam-release-guard/SKILL.md", (ROOT / name).read_text(encoding="utf-8"))
