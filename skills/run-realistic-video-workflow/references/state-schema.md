# Workflow state schema v1

## Compatibility

The scripts support schema version `1` only. They must reject a newer or older schema with a machine-readable error rather than infer a migration. Future migrations must first preserve a backup of the original state.

## `workflow-state.json`

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | integer | Must equal `1`. |
| `project_id` | string | Stable local project identifier. |
| `project_name` | string | Human-readable project name. |
| `current_stage` | string | One value from the ordered stage list. |
| `status` | string | Overall status mirrored from the active stage. |
| `stages` | object | Per-stage status, artifact paths, and approval record. |
| `decisions` | array | Persisted user decisions and invalidation events. |
| `pending_questions` | array | Unresolved high-impact questions for the next review gate. |
| `artifact_dependencies` | object | Maps each relative output artifact path to the relative input artifact paths it depends on. |
| `generation_tasks` | array | Production jobs, settings, authorization requirement, and result state. |
| `created_at` / `updated_at` | string | UTC ISO-8601 timestamps. |

Ordered stages:

1. `intake_brief`
2. `script_narrative`
3. `locked_visual_assets`
4. `storyboard_generation_audit`
5. `video_production_qa`
6. `postproduction_delivery`

Review gates are stages 1, 2, 3, 4, and 6. Stage 5 completes automatically after production QA; it is not an additional default review gate.

Stage statuses: `pending`, `running`, `needs_review`, `approved`, `completed`, `needs_revision`, `blocked`, and `failed`.

Artifact paths must be relative to the project root and must not escape it. Approving a gate requires at least one existing artifact.

Use `--pending-question` on `set` to persist unresolved Gate questions and `--clear-pending-questions` after resolving them. Use `--depends-on` with `set` or `approve` whenever a tracked artifact derives from another artifact. `invalidate --artifact PATH --reason TEXT` walks this graph transitively and invalidates only dependent outputs; the changed source artifact remains tracked. The broad form, `invalidate --from-stage STAGE --reason TEXT`, remains available for changes such as a revised brief.

## `intake-manifest.json`

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | integer | Must equal `1`. |
| `files` | array | Deduplicated intake file records. |
| `updated_at` | string | UTC ISO-8601 timestamp. |

Each file record contains `stored_path`, `source_label`, `filename`, `extension`, `size_bytes`, `sha256`, `category`, `rights_status`, and `added_at`. Absolute `source_path` is omitted unless the operator explicitly enables it for a private local project.

## Production authorization

A generation task is considered started when it has `started_at` or a status of `queued`, `running`, `completed`, or `failed`. If `requires_gate4` is absent, treat it as `true`. No such task may exist unless `storyboard_generation_audit` is approved or completed.
