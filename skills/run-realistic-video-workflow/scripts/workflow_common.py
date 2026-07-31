#!/usr/bin/env python3
"""Shared constants and validation helpers for the workflow commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
STAGES = [
    "intake_brief",
    "script_narrative",
    "locked_visual_assets",
    "storyboard_generation_audit",
    "video_production_qa",
    "postproduction_delivery",
]
GATE_STAGES = {
    "intake_brief",
    "script_narrative",
    "locked_visual_assets",
    "storyboard_generation_audit",
    "postproduction_delivery",
}
STATUSES = {
    "pending",
    "running",
    "needs_review",
    "approved",
    "completed",
    "needs_revision",
    "blocked",
    "failed",
}
UPSTREAM_READY = {"approved", "completed"}


class WorkflowError(Exception):
    """A stable, user-correctable workflow error."""


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def version() -> str:
    return (skill_root() / "VERSION").read_text(encoding="utf-8").strip()


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"Missing {label}: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"Invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"Invalid {label}: top-level value must be an object")
    return value


def require_schema(value: dict[str, Any], *, label: str) -> None:
    found = value.get("schema_version")
    if found != SCHEMA_VERSION:
        raise WorkflowError(
            f"Unsupported {label} schema_version {found!r}; supported version is {SCHEMA_VERSION}"
        )


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_within(path: Path, parent: Path) -> bool:
    resolved_path = path.resolve()
    resolved_parent = parent.resolve()
    return resolved_path == resolved_parent or resolved_parent in resolved_path.parents


def artifact_path(project_root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise WorkflowError(f"Artifact path must be relative: {relative}")
    resolved = (project_root / candidate).resolve()
    if not is_within(resolved, project_root):
        raise WorkflowError(f"Artifact path escapes project root: {relative}")
    return resolved


def require_upstream_ready(state: dict[str, Any], target_stage: str) -> None:
    target_index = STAGES.index(target_stage)
    stage_state = state.get("stages", {})
    for stage in STAGES[:target_index]:
        status = stage_state.get(stage, {}).get("status")
        if status not in UPSTREAM_READY:
            raise WorkflowError(
                f"Cannot advance to {target_stage}; upstream stage {stage} is {status!r}"
            )
