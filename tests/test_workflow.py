from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "skills" / "run-realistic-video-workflow" / "scripts"
INIT = SCRIPT_DIR / "init_project.py"
UPDATE = SCRIPT_DIR / "update_state.py"
VALIDATE = SCRIPT_DIR / "validate_project.py"


def run_script(script: Path, *args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(script), *(str(arg) for arg in args)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != expected:
        raise AssertionError(
            f"Expected exit {expected}, got {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


class WorkflowScriptsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.source = self.root / "materials"
        self.source.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def initialize(self, *extra: object) -> dict:
        result = run_script(INIT, self.project, "--name", "Synthetic Project", *extra)
        return json.loads(result.stdout)

    def state(self) -> dict:
        return json.loads((self.project / ".workflow" / "workflow-state.json").read_text(encoding="utf-8"))

    def write_artifact(self, relative: str, content: str = "approved") -> Path:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_all_commands_report_version(self) -> None:
        for script in (INIT, UPDATE, VALIDATE):
            result = run_script(script, "--version")
            self.assertEqual(result.stdout.strip(), "0.1.0")

    def test_intake_redacts_paths_deduplicates_and_skips_sensitive_files(self) -> None:
        (self.source / "story.txt").write_text("synthetic story", encoding="utf-8")
        (self.source / "story-copy.txt").write_text("synthetic story", encoding="utf-8")
        (self.source / ".env").write_text("TOKEN=not-a-real-token", encoding="utf-8")
        (self.source / "credentials-demo.json").write_text("{}", encoding="utf-8")
        cache = self.source / "__pycache__"
        cache.mkdir()
        (cache / "cache.pyc").write_bytes(b"cache")

        symlink_created = False
        try:
            (self.source / "linked.txt").symlink_to(self.source / "story.txt")
            symlink_created = True
        except (OSError, NotImplementedError):
            pass

        output = self.initialize("--source", self.source)
        self.assertEqual(output["registered_files"], 1)
        reasons = {item["reason"] for item in output["skipped_files"]}
        self.assertIn("duplicate_content", reasons)
        self.assertIn("sensitive_filename", reasons)
        self.assertIn("excluded_directory", reasons)
        if symlink_created:
            self.assertIn("symbolic_link", reasons)

        manifest = json.loads((self.project / ".workflow" / "intake-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["files"]), 1)
        record = manifest["files"][0]
        self.assertNotIn("source_path", record)
        self.assertFalse(Path(record["source_label"]).is_absolute())

        second = self.initialize("--source", self.source)
        self.assertEqual(second["registered_files"], 0)
        self.assertEqual(second["total_files"], 1)

    def test_large_file_is_not_copied(self) -> None:
        (self.source / "large.bin").write_bytes(b"x" * (1024 * 1024 + 1))
        output = self.initialize("--source", self.source, "--max-file-mib", 1)
        self.assertEqual(output["registered_files"], 0)
        self.assertEqual(output["skipped_files"][0]["reason"], "file_too_large")

    def test_newer_schema_is_rejected(self) -> None:
        self.initialize()
        state_path = self.project / ".workflow" / "workflow-state.json"
        state = self.state()
        state["schema_version"] = 2
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result = run_script(VALIDATE, self.project, expected=1)
        payload = json.loads(result.stdout)
        self.assertIn("Unsupported workflow state schema_version", payload["errors"][0])

    def test_gate_order_artifacts_and_unicode_approval(self) -> None:
        self.initialize()
        bypass = run_script(
            UPDATE,
            self.project,
            "set",
            "--stage",
            "intake_brief",
            "--status",
            "completed",
            expected=1,
        )
        self.assertIn("can only be released with the approve command", bypass.stderr)
        blocked = run_script(
            UPDATE,
            self.project,
            "set",
            "--stage",
            "script_narrative",
            "--status",
            "running",
            expected=1,
        )
        self.assertIn("upstream stage intake_brief", blocked.stderr)

        self.write_artifact("01_brief/project-brief.md")
        run_script(
            UPDATE,
            self.project,
            "approve",
            "--stage",
            "intake_brief",
            "--artifact",
            "01_brief/project-brief.md",
            "--note",
            "用户确认",
        )
        run_script(
            UPDATE,
            self.project,
            "set",
            "--stage",
            "script_narrative",
            "--status",
            "running",
        )
        self.write_artifact("02_script/script.md")
        run_script(
            UPDATE,
            self.project,
            "set",
            "--stage",
            "script_narrative",
            "--status",
            "needs_review",
            "--artifact",
            "02_script/script.md",
            "--depends-on",
            "01_brief/project-brief.md",
        )
        self.assertEqual(
            self.state()["artifact_dependencies"]["02_script/script.md"],
            ["01_brief/project-brief.md"],
        )
        log = (self.project / ".workflow" / "approval-log.md").read_text(encoding="utf-8")
        self.assertIn("用户确认", log)

    def test_pending_questions_are_persisted_and_cleared(self) -> None:
        self.initialize()
        run_script(
            UPDATE,
            self.project,
            "set",
            "--stage",
            "intake_brief",
            "--status",
            "needs_review",
            "--pending-question",
            "Confirm runtime",
        )
        self.assertEqual(self.state()["pending_questions"], ["Confirm runtime"])
        run_script(
            UPDATE,
            self.project,
            "set",
            "--stage",
            "intake_brief",
            "--status",
            "needs_review",
            "--clear-pending-questions",
        )
        self.assertEqual(self.state()["pending_questions"], [])

    def test_manually_released_gate_fails_validation(self) -> None:
        self.initialize()
        state_path = self.project / ".workflow" / "workflow-state.json"
        state = self.state()
        state["stages"]["intake_brief"]["status"] = "completed"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result = run_script(VALIDATE, self.project, expected=1)
        self.assertIn("Gate stage released without approval", result.stdout)

    def test_missing_approved_artifact_fails_validation(self) -> None:
        self.initialize()
        artifact = self.write_artifact("01_brief/project-brief.md")
        run_script(
            UPDATE,
            self.project,
            "approve",
            "--stage",
            "intake_brief",
            "--artifact",
            "01_brief/project-brief.md",
        )
        artifact.unlink()
        result = run_script(VALIDATE, self.project, expected=1)
        self.assertIn("Approved artifact missing", result.stdout)

    def test_generation_cannot_start_before_gate_four(self) -> None:
        self.initialize()
        state_path = self.project / ".workflow" / "workflow-state.json"
        state = self.state()
        state["generation_tasks"].append({"task_id": "synthetic", "status": "queued"})
        state_path.write_text(json.dumps(state), encoding="utf-8")
        result = run_script(VALIDATE, self.project, expected=1)
        self.assertIn("Generation task started before Gate 4 approval", result.stdout)

    def test_invalidation_preserves_only_upstream_approval(self) -> None:
        self.initialize()
        self.write_artifact("01_brief/project-brief.md")
        run_script(
            UPDATE,
            self.project,
            "approve",
            "--stage",
            "intake_brief",
            "--artifact",
            "01_brief/project-brief.md",
        )
        self.write_artifact("02_script/script.md")
        run_script(
            UPDATE,
            self.project,
            "approve",
            "--stage",
            "script_narrative",
            "--artifact",
            "02_script/script.md",
        )
        run_script(
            UPDATE,
            self.project,
            "invalidate",
            "--from-stage",
            "script_narrative",
            "--reason",
            "runtime changed",
        )
        state = self.state()
        self.assertEqual(state["stages"]["intake_brief"]["status"], "approved")
        self.assertEqual(state["stages"]["script_narrative"]["status"], "pending")
        self.assertTrue(all(state["stages"][stage]["status"] == "pending" for stage in state["stages"] if stage != "intake_brief"))

    def test_artifact_invalidation_only_removes_transitive_dependents(self) -> None:
        self.initialize()
        state_path = self.project / ".workflow" / "workflow-state.json"
        changed = "03_locked-assets/lead.md"
        unaffected_source = "03_locked-assets/location.md"
        dependent = "05_storyboards/lead-shot.md"
        transitive = "06_generation-plan/lead-unit.md"
        unaffected = "05_storyboards/location-shot.md"
        for relative in (changed, unaffected_source, dependent, transitive, unaffected):
            self.write_artifact(relative)

        state = self.state()
        state["stages"]["locked_visual_assets"]["artifacts"] = [changed, unaffected_source]
        state["stages"]["storyboard_generation_audit"]["artifacts"] = [dependent, unaffected]
        state["stages"]["storyboard_generation_audit"]["status"] = "approved"
        state["stages"]["storyboard_generation_audit"]["approval"] = {"decision": "approved"}
        state["stages"]["video_production_qa"]["artifacts"] = [transitive]
        state["artifact_dependencies"] = {
            dependent: [changed],
            transitive: [dependent],
            unaffected: [unaffected_source],
        }
        state["generation_tasks"] = [
            {"task_id": "synthetic", "status": "completed", "input_artifacts": [changed]}
        ]
        state_path.write_text(json.dumps(state), encoding="utf-8")

        run_script(
            UPDATE,
            self.project,
            "invalidate",
            "--artifact",
            changed,
            "--reason",
            "asset revised",
        )
        state = self.state()
        self.assertEqual(state["stages"]["locked_visual_assets"]["artifacts"], [changed, unaffected_source])
        self.assertEqual(state["stages"]["storyboard_generation_audit"]["artifacts"], [unaffected])
        self.assertEqual(state["stages"]["storyboard_generation_audit"]["status"], "needs_revision")
        self.assertEqual(state["stages"]["video_production_qa"]["artifacts"], [])
        self.assertNotIn(dependent, state["artifact_dependencies"])
        self.assertNotIn(transitive, state["artifact_dependencies"])
        self.assertIn(unaffected, state["artifact_dependencies"])
        self.assertEqual(state["generation_tasks"][0]["status"], "invalidated")
        self.assertIn("invalidated_at", state["generation_tasks"][0])


if __name__ == "__main__":
    unittest.main()
