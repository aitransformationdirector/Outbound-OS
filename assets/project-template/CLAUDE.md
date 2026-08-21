@AGENTS.md

# Claude Code runtime

This generated project supports Claude Code. For `run` or `/run-outbound-campaign`, use `.claude/skills/run-outbound-campaign/SKILL.md` and the shared executable at `system/runtime/campaign_engine.py`.

Before campaign work, confirm the current project root contains `CLAUDE.md`, `PROJECT_INPUT.json`, `.claude/skills/run-outbound-campaign/SKILL.md`, and `system/runtime/campaign_engine.py`. If any marker is absent, stop and guide the user to open the exact `project_root` recorded in `PROJECT_INPUT.json`.

Do not use `.agents/skills` as Claude's runtime entry point. Both host packages are included so the campaign can move between supported hosts, but campaign state and shared runtime files remain canonical.
