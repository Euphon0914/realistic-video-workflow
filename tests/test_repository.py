from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "run-realistic-video-workflow"
TEXT_EXTENSIONS = {".md", ".py", ".yaml", ".yml", ".json", ".csv", ".txt", ""}
MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".wav", ".mp3"}


class RepositoryHygieneTest(unittest.TestCase):
    def tracked_candidates(self):
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            yield path

    def test_skill_layout_and_frontmatter(self) -> None:
        skill_md = SKILL / "SKILL.md"
        self.assertTrue(skill_md.exists())
        text = skill_md.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        keys = [line.split(":", 1)[0].strip() for line in frontmatter.splitlines() if ":" in line]
        self.assertEqual(keys, ["name", "description"])
        self.assertIn("name: run-realistic-video-workflow", frontmatter)
        self.assertTrue((SKILL / "agents" / "openai.yaml").exists())
        self.assertTrue((SKILL / "VERSION").exists())

    def test_text_is_utf8_lf_and_has_no_local_absolute_paths(self) -> None:
        windows_absolute = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/](?![\\/])")
        for path in self.tracked_candidates():
            if path.suffix.lower() not in TEXT_EXTENSIONS and path.name != "VERSION":
                continue
            data = path.read_bytes()
            self.assertNotIn(b"\r\n", data, path)
            text = data.decode("utf-8")
            self.assertIsNone(windows_absolute.search(text), path)

    def test_no_large_files_media_or_caches(self) -> None:
        for path in self.tracked_candidates():
            self.assertLess(path.stat().st_size, 1024 * 1024, path)
            self.assertNotIn(path.suffix.lower(), MEDIA_EXTENSIONS, path)
            self.assertNotIn("__pycache__", path.parts)

    def test_openai_metadata_has_no_fake_dependencies(self) -> None:
        text = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertNotIn("dependencies:", text)
        self.assertIn("$run-realistic-video-workflow", text)

    def test_public_package_contains_no_known_project_material(self) -> None:
        forbidden = [
            "种下" + "善因",
            "NA" + "NUX",
            "Ju" + "ng",
            "K" + "en",
            "7ec2434f" + "fffa4f88824f44ca61dc57c3",
        ]
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in self.tracked_candidates()
            if path.suffix.lower() in TEXT_EXTENSIONS
        )
        for marker in forbidden:
            self.assertNotIn(marker, combined)


if __name__ == "__main__":
    unittest.main()
