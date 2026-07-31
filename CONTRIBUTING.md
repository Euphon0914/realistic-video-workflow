# Contributing

Contributions should preserve the workflow's core guarantees: photorealistic live-action baseline, five review gates, resumable state, minimal downstream invalidation, privacy-safe intake, and optional production integrations.

## Before opening a pull request

1. Create a focused branch.
2. Add or update tests for every behavior change.
3. Run `python -m unittest discover -s tests -v`.
4. Run `python -m compileall -q skills/run-realistic-video-workflow/scripts`.
5. Confirm no real media, local absolute paths, credentials, task IDs, caches, or generated project state are included.
6. Keep `SKILL.md` concise; put detailed procedures in one-level `references/` files.

Use synthetic text fixtures only. Do not submit user-owned photos, videos, logos, documents, prompts, or production results.

## Maintainer setup and release

- Protect `main` with a repository ruleset that requires pull requests and the `test` matrix to pass.
- Enable secret scanning and push protection before accepting contributions.
- Run the full test suite from a clean clone, update `CHANGELOG.md` and `VERSION`, then create a signed or annotated version tag.
- Publish the matching GitHub Release from that tag; do not attach project materials or generated media.
