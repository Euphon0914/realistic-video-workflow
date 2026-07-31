# Minimal synthetic example

From the repository root:

```bash
python skills/run-realistic-video-workflow/scripts/init_project.py \
  ./example-output \
  --name "The Last Repair Shop" \
  --source ./examples/minimal-project/materials

python skills/run-realistic-video-workflow/scripts/validate_project.py ./example-output
```

The initialized project is intentionally not committed. The Skill would next inspect the manifest and source text, create the project brief and evidence table, and pause at Gate 1.
