#!/usr/bin/env python3
"""Validate a realistic-video project before review or delivery."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workflow_common import (
    GATE_STAGES,
    SCHEMA_VERSION,
    STAGES,
    STATUSES,
    UPSTREAM_READY,
    WorkflowError,
    artifact_path,
    read_json,
    require_schema,
    version,
)


REQUIRED = [
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
    ".workflow/workflow-state.json",
    ".workflow/intake-manifest.json",
    ".workflow/approval-log.md",
]
ACTIVE_OR_FINISHED = {"running", "needs_review", "approved", "completed", "needs_revision", "blocked", "failed"}
STARTED_TASK_STATUSES = {"queued", "running", "completed", "failed"}


def started_generation_task(task: dict) -> bool:
    if task.get("invalidated_at"):
        return False
    return bool(task.get("started_at")) or task.get("status") in STARTED_TASK_STATUSES


def validate_state(root: Path, state: dict, errors: list[str]) -> None:
    if state.get("current_stage") not in STAGES:
        errors.append("Invalid current_stage")
    if state.get("status") not in STATUSES:
        errors.append(f"Invalid overall status: {state.get('status')!r}")

    stage_state = state.get("stages", {})
    dependency_graph = state.get("artifact_dependencies", {})
    if not isinstance(dependency_graph, dict):
        errors.append("artifact_dependencies must be an object")
        dependency_graph = {}
    for output, dependencies in dependency_graph.items():
        try:
            artifact_path(root, output)
        except WorkflowError as exc:
            errors.append(str(exc))
        if not isinstance(dependencies, list):
            errors.append(f"Artifact dependencies must be an array: {output}")
            continue
        for dependency in dependencies:
            try:
                artifact_path(root, dependency)
            except WorkflowError as exc:
                errors.append(str(exc))
    for index, stage in enumerate(STAGES):
        entry = stage_state.get(stage)
        if not isinstance(entry, dict):
            errors.append(f"Missing stage state: {stage}")
            continue
        status = entry.get("status")
        if status not in STATUSES:
            errors.append(f"Invalid status for {stage}: {status!r}")
        if stage in GATE_STAGES and status in UPSTREAM_READY:
            approval = entry.get("approval")
            if not isinstance(approval, dict) or approval.get("decision") != "approved":
                errors.append(f"Gate stage released without approval: {stage}")
        if status in ACTIVE_OR_FINISHED and index > 0:
            for upstream in STAGES[:index]:
                upstream_status = stage_state.get(upstream, {}).get("status")
                if upstream_status not in UPSTREAM_READY:
                    errors.append(
                        f"Stage order violation: {stage} is {status!r} while {upstream} is {upstream_status!r}"
                    )
        for relative in entry.get("artifacts", []):
            try:
                path = artifact_path(root, relative)
                if status in {"approved", "completed"} and not path.exists():
                    errors.append(f"Approved artifact missing: {relative}")
            except WorkflowError as exc:
                errors.append(str(exc))

    gate4_ready = stage_state.get("storyboard_generation_audit", {}).get("status") in UPSTREAM_READY
    for task in state.get("generation_tasks", []):
        if task.get("requires_gate4", True) and started_generation_task(task) and not gate4_ready:
            errors.append("Generation task started before Gate 4 approval")


def validate_manifest(root: Path, manifest: dict, errors: list[str], warnings: list[str]) -> None:
    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("Manifest files must be an array")
        return
    if not files:
        warnings.append("Intake manifest contains no files")
    hashes: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            errors.append("Manifest file record must be an object")
            continue
        stored = item.get("stored_path")
        try:
            path = artifact_path(root, stored or "")
            if not stored or not path.exists():
                errors.append(f"Manifest file missing: {stored}")
        except WorkflowError as exc:
            errors.append(str(exc))
        digest = item.get("sha256")
        if not digest:
            errors.append(f"Manifest file has no sha256: {stored}")
        elif digest in hashes:
            errors.append(f"Duplicate manifest sha256: {digest}")
        else:
            hashes.add(digest)
        if "source_path" in item and Path(str(item["source_path"])).is_absolute():
            warnings.append(f"Manifest exposes an absolute source_path: {stored}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=version())
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = args.project_dir.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED:
        if not (root / relative).exists():
            errors.append(f"Missing: {relative}")

    try:
        state = read_json(root / ".workflow" / "workflow-state.json", label="workflow state")
        require_schema(state, label="workflow state")
        validate_state(root, state, errors)
    except WorkflowError as exc:
        errors.append(str(exc))

    try:
        manifest = read_json(root / ".workflow" / "intake-manifest.json", label="intake manifest")
        require_schema(manifest, label="intake manifest")
        validate_manifest(root, manifest, errors, warnings)
    except WorkflowError as exc:
        errors.append(str(exc))

    valid = not errors and not (args.strict and warnings)
    print(
        json.dumps(
            {
                "ok": valid,
                "schema_version": SCHEMA_VERSION,
                "errors": errors,
                "warnings": warnings,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if valid else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WorkflowError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
