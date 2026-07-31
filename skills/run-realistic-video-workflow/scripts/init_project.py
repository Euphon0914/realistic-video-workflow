#!/usr/bin/env python3
"""Initialize or extend a resumable realistic-video project safely."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from workflow_common import SCHEMA_VERSION, STAGES, WorkflowError, is_within, read_json, require_schema, version, write_json


DIRECTORIES = [
    "00_intake/uploads",
    "01_brief",
    "02_script",
    "03_locked-assets",
    "04_visual-bible",
    "05_storyboards",
    "06_generation-plan",
    "07_generated-video",
    "08_postproduction",
    "09_delivery",
    ".workflow/audits",
]
EXCLUDED_DIRECTORIES = {
    ".git",
    ".workflow",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "tmp",
    "temp",
}
SENSITIVE_PATTERNS = (
    ".env",
    ".env.*",
    "credentials*.json",
    "secrets*.json",
    "*token*.json",
    "id_rsa*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_destination(directory: Path, name: str) -> Path:
    candidate = directory / name
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    index = 2
    while True:
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def sensitive_name(name: str) -> bool:
    lowered = name.lower()
    return any(fnmatch.fnmatch(lowered, pattern) for pattern in SENSITIVE_PATTERNS)


def collect_files(source: Path, project_root: Path) -> tuple[list[tuple[Path, str]], list[dict[str, str]]]:
    files: list[tuple[Path, str]] = []
    skipped: list[dict[str, str]] = []

    if not source.exists():
        raise WorkflowError(f"Source does not exist: {source}")
    if source.is_symlink():
        return files, [{"source_label": source.name, "reason": "symbolic_link"}]
    if source.is_file():
        return [(source, source.name)], skipped

    for current, dirnames, filenames in os.walk(source, followlinks=False):
        current_path = Path(current)
        kept_directories: list[str] = []
        for dirname in dirnames:
            candidate = current_path / dirname
            label = candidate.relative_to(source).as_posix()
            if dirname.lower() in EXCLUDED_DIRECTORIES or candidate.is_symlink():
                skipped.append({"source_label": label, "reason": "excluded_directory"})
            elif is_within(candidate, project_root):
                skipped.append({"source_label": label, "reason": "project_directory"})
            else:
                kept_directories.append(dirname)
        dirnames[:] = kept_directories

        for filename in filenames:
            candidate = current_path / filename
            label = candidate.relative_to(source).as_posix()
            if candidate.is_symlink():
                skipped.append({"source_label": label, "reason": "symbolic_link"})
            elif is_within(candidate, project_root):
                skipped.append({"source_label": label, "reason": "project_file"})
            else:
                files.append((candidate, f"{source.name}/{label}"))
    return files, skipped


def empty_state(root: Path, project_name: str | None) -> dict:
    stages = {stage: {"status": "pending", "artifacts": [], "approval": None} for stage in STAGES}
    stages[STAGES[0]]["status"] = "running"
    now = utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": root.name,
        "project_name": project_name or root.name,
        "current_stage": STAGES[0],
        "status": "running",
        "stages": stages,
        "decisions": [],
        "pending_questions": [],
        "artifact_dependencies": {},
        "generation_tasks": [],
        "created_at": now,
        "updated_at": now,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=version())
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--name", dest="project_name")
    parser.add_argument("--source", action="append", default=[], type=Path)
    parser.add_argument("--max-file-mib", type=int, default=500)
    parser.add_argument("--include-source-path", action="store_true")
    args = parser.parse_args()

    if args.max_file_mib <= 0:
        raise WorkflowError("--max-file-mib must be greater than zero")

    root = args.project_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    for relative in DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)

    workflow_dir = root / ".workflow"
    state_path = workflow_dir / "workflow-state.json"
    if state_path.exists():
        state = read_json(state_path, label="workflow state")
        require_schema(state, label="workflow state")
    else:
        state = empty_state(root, args.project_name)
    state["updated_at"] = utc_now()
    write_json(state_path, state)

    uploads = root / "00_intake" / "uploads"
    manifest_path = workflow_dir / "intake-manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path, label="intake manifest")
        require_schema(manifest, label="intake manifest")
    else:
        manifest = {"schema_version": SCHEMA_VERSION, "files": [], "updated_at": utc_now()}

    known_hashes = {item["sha256"] for item in manifest.get("files", [])}
    skipped: list[dict[str, str]] = []
    registered = 0
    max_bytes = args.max_file_mib * 1024 * 1024

    for source_argument in args.source:
        source = source_argument.expanduser().absolute()
        candidates, source_skips = collect_files(source, root)
        skipped.extend(source_skips)
        for item, source_label in candidates:
            if sensitive_name(item.name):
                skipped.append({"source_label": source_label, "reason": "sensitive_filename"})
                continue
            size = item.stat().st_size
            if size > max_bytes:
                skipped.append({"source_label": source_label, "reason": "file_too_large"})
                continue
            digest = sha256(item)
            if digest in known_hashes:
                skipped.append({"source_label": source_label, "reason": "duplicate_content"})
                continue
            destination = unique_destination(uploads, item.name)
            shutil.copy2(item, destination)
            record = {
                "stored_path": destination.relative_to(root).as_posix(),
                "source_label": source_label,
                "filename": destination.name,
                "extension": destination.suffix.lower(),
                "size_bytes": destination.stat().st_size,
                "sha256": digest,
                "category": "unclassified",
                "rights_status": "unknown",
                "added_at": utc_now(),
            }
            if args.include_source_path:
                record["source_path"] = str(item.resolve())
            manifest["files"].append(record)
            known_hashes.add(digest)
            registered += 1

    manifest["updated_at"] = utc_now()
    write_json(manifest_path, manifest)

    approval_log = workflow_dir / "approval-log.md"
    if not approval_log.exists():
        approval_log.write_text("# 审核记录\n\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": SCHEMA_VERSION,
                "project": str(root),
                "registered_files": registered,
                "total_files": len(manifest["files"]),
                "skipped_files": skipped,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WorkflowError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
