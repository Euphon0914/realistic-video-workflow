# Optional production integrations

The core workflow, intake manifest, state machine, audits, and review gates require only Python 3.10+ and its standard library. Do not fail project startup because a production integration is absent.

## Capability detection

Detect capabilities only when the current approved stage needs them. Do not declare Skill-to-Skill dependencies in `agents/openai.yaml`; its dependency schema is not for local Skills or CLIs.

| Need | Preferred capability when available | Without it |
|---|---|---|
| Character boards, style frames, storyboard references, targeted image correction | `imagegen` | Prepare complete image briefs and reference mappings, then pause at the visual output boundary or use another user-approved image capability. |
| Canvas orchestration, asset uploads, node connections, job execution, result queries | `libtv-cli` | Produce a platform-neutral generation manifest and task table; do not fabricate node IDs or task results. |
| Seedance multimodal prompt structure | `seedance-prompt-zh` or `seedance-prompt-en` | Use the workflow's prompt-reference checklist and write a platform-neutral prompt package. |

## Safety rules

- Never start a paid or quota-consuming task before Gate 4 approval.
- Never request credentials in a document or commit them to the project.
- Record the selected integration, model settings, prompt version, reference roles, task ID, and result in workflow state or an approved artifact.
- Treat missing integrations as a localized production boundary, not a reason to discard completed upstream work.
- Offer an alternative only when it preserves the approved visual and factual constraints; otherwise pause for review.
