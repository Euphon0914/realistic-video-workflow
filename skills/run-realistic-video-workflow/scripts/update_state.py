#!/usr/bin/env python3
"""Update stages, approvals, artifacts, and downstream invalidation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from workflow_common import (
    GATE_STAGES,
    STAGES,
    STATUSES,
    WorkflowError,
    artifact_path,
    read_json,
    require_schema,
    require_upstream_ready,
    version,
    write_json,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state(project_dir: Path) -> tuple[Path, Path, dict]:
    root = project_dir.resolve()
    path = root / ".workflow" / "workflow-state.json"
    state = read_json(path, label="workflow state")
    require_schema(state, label="workflow state")
    return root, path, state


def validate_artifacts(root: Path, artifacts: list[str]) -> list[str]:
    normalized: list[str] = []
    for relative in artifacts:
        path = artifact_path(root, relative)
        if not path.exists():
            raise WorkflowError(f"Artifact does not exist: {relative}")
        normalized.append(path.relative_to(root).as_posix())
    return normalized


def normalize_artifact_references(root: Path, artifacts: list[str]) -> list[str]:
    return [artifact_path(root, relative).relative_to(root).as_posix() for relative in artifacts]


def record_dependencies(state: dict, outputs: list[str], inputs: list[str]) -> None:
    if inputs and not outputs:
        raise WorkflowError("--depends-on requires at least one --artifact")
    graph = state.setdefault("artifact_dependencies", {})
    for output in outputs:
        graph[output] = sorted(set(graph.get(output, []) + inputs))


def transitive_dependents(state: dict, changed: list[str]) -> set[str]:
    graph = state.get("artifact_dependencies", {})
    impacted = set(changed)
    added = True
    while added:
        added = False
        for output, dependencies in graph.items():
            if output not in impacted and any(item in impacted for item in dependencies):
                impacted.add(output)
                added = True
    return impacted - set(changed)


def append_approval(root: Path, stage: str, decision: str, note: str) -> None:
    log = root / ".workflow" / "approval-log.md"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"## {utc_now()} — {stage}\n\n- 决定：{decision}\n- 说明：{note or '无'}\n\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=version())
    parser.add_argument("project_dir", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)

    set_cmd = sub.add_parser("set")
    set_cmd.add_argument("--stage", required=True, choices=STAGES)
    set_cmd.add_argument("--status", required=True, choices=sorted(STATUSES))
    set_cmd.add_argument("--artifact", action="append", default=[])
    set_cmd.add_argument("--depends-on", action="append", default=[])
    set_cmd.add_argument("--pending-question", action="append", default=[])
    set_cmd.add_argument("--clear-pending-questions", action="store_true")

    approve_cmd = sub.add_parser("approve")
    approve_cmd.add_argument("--stage", required=True, choices=sorted(GATE_STAGES))
    approve_cmd.add_argument(
        "--decision", default="approved", choices=["approved", "revision", "rollback", "paused"]
    )
    approve_cmd.add_argument("--note", default="")
    approve_cmd.add_argument("--artifact", action="append", default=[])
    approve_cmd.add_argument("--depends-on", action="append", default=[])

    invalidate_cmd = sub.add_parser("invalidate")
    invalidate_target = invalidate_cmd.add_mutually_exclusive_group(required=True)
    invalidate_target.add_argument("--from-stage", choices=STAGES)
    invalidate_target.add_argument("--artifact", action="append")
    invalidate_cmd.add_argument("--reason", required=True)

    args = parser.parse_args()
    root, state_path, state = load_state(args.project_dir)

    if args.command == "set":
        if args.stage in GATE_STAGES and args.status in {"approved", "completed"}:
            raise WorkflowError(
                f"Gate stage {args.stage} can only be released with the approve command"
            )
        if args.status != "pending":
            require_upstream_ready(state, args.stage)
        new_artifacts = validate_artifacts(root, args.artifact)
        dependencies = validate_artifacts(root, args.depends_on)
        record_dependencies(state, new_artifacts, dependencies)
        entry = state["stages"][args.stage]
        entry["status"] = args.status
        entry["artifacts"] = sorted(set(entry.get("artifacts", []) + new_artifacts))
        if args.clear_pending_questions:
            state["pending_questions"] = []
        if args.pending_question:
            state["pending_questions"] = list(
                dict.fromkeys(state.get("pending_questions", []) + args.pending_question)
            )
        state["current_stage"] = args.stage
        state["status"] = args.status

    elif args.command == "approve":
        require_upstream_ready(state, args.stage)
        new_artifacts = validate_artifacts(root, args.artifact)
        dependencies = validate_artifacts(root, args.depends_on)
        record_dependencies(state, new_artifacts, dependencies)
        entry = state["stages"][args.stage]
        all_artifacts = sorted(set(entry.get("artifacts", []) + new_artifacts))
        if args.decision == "approved" and not all_artifacts:
            raise WorkflowError(f"Approving {args.stage} requires at least one existing artifact")
        status_by_decision = {
            "approved": "approved",
            "revision": "needs_revision",
            "rollback": "needs_revision",
            "paused": "blocked",
        }
        entry["artifacts"] = all_artifacts
        entry["approval"] = {"decision": args.decision, "note": args.note, "at": utc_now()}
        entry["status"] = status_by_decision[args.decision]
        state["status"] = entry["status"]
        state["current_stage"] = args.stage
        append_approval(root, args.stage, args.decision, args.note)

    elif args.command == "invalidate" and args.from_stage:
        start = STAGES.index(args.from_stage)
        for stage in STAGES[start:]:
            state["stages"][stage]["status"] = "pending"
            state["stages"][stage]["approval"] = None
        state["current_stage"] = args.from_stage
        state["status"] = "pending"
        state.setdefault("decisions", []).append(
            {"type": "invalidation", "from_stage": args.from_stage, "reason": args.reason, "at": utc_now()}
        )

    elif args.command == "invalidate":
        changed = normalize_artifact_references(root, args.artifact)
        impacted = transitive_dependents(state, changed)
        affected_stages: list[str] = []
        for stage in STAGES:
            entry = state["stages"][stage]
            tracked = set(entry.get("artifacts", []))
            if tracked.intersection(impacted):
                entry["artifacts"] = sorted(tracked - impacted)
                entry["status"] = "needs_revision"
                entry["approval"] = None
                affected_stages.append(stage)
        graph = state.setdefault("artifact_dependencies", {})
        for output in impacted:
            graph.pop(output, None)
        for task in state.get("generation_tasks", []):
            inputs = set(task.get("input_artifacts", []))
            if inputs.intersection(impacted.union(changed)):
                task["status"] = "invalidated"
                task["invalidated_at"] = utc_now()
                task["invalidation_reason"] = args.reason
        if affected_stages:
            state["current_stage"] = min(affected_stages, key=STAGES.index)
            state["status"] = "needs_revision"
        state.setdefault("decisions", []).append(
            {
                "type": "artifact_invalidation",
                "changed_artifacts": changed,
                "invalidated_artifacts": sorted(impacted),
                "affected_stages": affected_stages,
                "reason": args.reason,
                "at": utc_now(),
            }
        )

    state["updated_at"] = utc_now()
    write_json(state_path, state)
    print(json.dumps({"ok": True, "current_stage": state["current_stage"], "status": state["status"]}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WorkflowError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
