from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillPackageTests(unittest.TestCase):
    def test_skill_frontmatter_is_portable(self) -> None:
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        frontmatter = content.split("---\n", 2)[1]
        keys = {
            match.group(1)
            for line in frontmatter.splitlines()
            if (match := re.match(r"^([a-z_]+):", line))
        }
        self.assertEqual(keys, {"name", "description"})
        self.assertIn("name: what-did-i-do", frontmatter)
        self.assertLessEqual(len(content.splitlines()), 500)

    def test_local_markdown_links_exist(self) -> None:
        for source_name in ("README.md", "SKILL.md", "references/compatibility.md"):
            source = ROOT / source_name
            content = source.read_text(encoding="utf-8")
            for target in re.findall(r"!?\[[^]]*]\(([^)]+)\)", content):
                if target.startswith(("http://", "https://", "#")):
                    continue
                path = (source.parent / target).resolve()
                self.assertTrue(
                    path.exists(), f"{source_name} links to missing {target}"
                )

    def test_openai_metadata_icons_exist(self) -> None:
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        for icon in ("assets/icon-small.png", "assets/icon-large.png"):
            self.assertIn(f'"./{icon}"', metadata)
            self.assertTrue((ROOT / icon).is_file())

    def test_eval_cases_cover_core_scopes(self) -> None:
        payload = json.loads(
            (ROOT / "evals" / "cases.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["skill"], "what-did-i-do")
        case_ids = {case["id"] for case in payload["cases"]}
        self.assertEqual(
            case_ids,
            {
                "working-tree-summary",
                "outgoing-push-summary",
                "clean-repository",
                "outgoing-without-upstream",
            },
        )
        for case in payload["cases"]:
            self.assertTrue(case["prompt"])
            self.assertGreaterEqual(len(case["assertions"]), 3)


if __name__ == "__main__":
    unittest.main()
