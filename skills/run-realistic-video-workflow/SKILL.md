---
name: run-realistic-video-workflow
description: Run or resume a material-driven, human-in-the-loop workflow for photorealistic live-action video projects. Use when the user uploads source materials and wants Codex to independently develop a documentary, character story, brand or product film, cultural/travel/educational video, social short, or another realistic human-centered video without restating production requirements; also use to continue an existing project from saved workflow state.
---

# Run Realistic Video Workflow

Turn uploaded materials into a complete photorealistic live-action video project. Advance independently, preserve decisions, and pause only at defined review gates or genuine exceptions.

## Load the protocol

Read these files completely before starting or resuming work:

- `references/workflow.md` for stages, state transitions, review gates, deliverables, and exception handling.
- `references/checklists.md` for intake, prompt-reference, realism, video, and final-master checks.
- `references/state-schema.md` before reading or changing workflow JSON.

Read `references/integrations.md` only when visual generation, video generation, or orchestration becomes necessary.

Do not ask the user to repeat information that exists in source materials, approved artifacts, or workflow state.

## Keep the scope general

Do not assume a fixed project type. Derive the subject and narrative form from the supplied materials. Support documentaries, portraits, product or service stories, public-interest content, culture and travel, education, events, social shorts, and other live-action formats.

Hold only this visual baseline unless the user explicitly overrides it:

- photorealistic live-action human texture;
- natural skin, anatomy, expressions, clothing, and motion;
- physically plausible locations, objects, lighting, lenses, camera placement, and sound;
- restrained grading and effects that do not make people look synthetic.

Do not inherit a prior project's location, brand, story, palette, aspect ratio, language, runtime, or model settings.

## Start or resume

1. Inspect the provided files and target project directory.
2. If `.workflow/workflow-state.json` exists, run `scripts/validate_project.py` and resume the earliest incomplete or invalidated stage.
3. Otherwise, initialize with `scripts/init_project.py` and register source files without moving or overwriting them.
4. Build the intake manifest and evidence table before asking any question.
5. Resolve discoverable facts from the materials. Consolidate only high-impact unresolved decisions into Gate 1.
6. Execute stages in `references/workflow.md`. Batch closely related artifacts into one state update; otherwise update state after each material output. Persist Gate questions with `--pending-question`.
7. Never start paid or quota-consuming production before Gate 4 approval.

## Review behavior

Use exactly five default gates:

1. project brief;
2. script and narrative;
3. visual identity and locked assets;
4. storyboards, generation plan, prompt-reference audit, and production authorization;
5. final cut and archive.

At each gate, provide one compact review package containing previews, changed files, automated checks, unresolved issues, and a recommended decision. Accept approval, revision, rollback, or pause. Persist the decision so it is not asked again.

Pause outside these gates only for conflicting facts, missing rights, an unavailable required capability, a change that invalidates approved upstream work, unapproved extra consumption, or a risk of materially misleading the audience.

## Version and state rules

- Never overwrite approved artifacts; create a new version and preserve the approved pointer.
- Invalidate only downstream stages that depend on a changed artifact.
- Use `scripts/update_state.py` for state changes and `scripts/validate_project.py` before each gate and final handoff.
- Keep source labels, references, prompts, task IDs, approvals, QA results, and final outputs traceable.
- Reject a state schema newer than the supported version instead of guessing a migration.

## Use optional integrations

Keep the core workflow independent of production services. At the stage that needs an integration, detect whether an appropriate capability is available and follow `references/integrations.md`. Continue safe upstream work when it is absent; pause only when the next required output cannot be produced without it.
