---
name: outbound-os
description: Create the canonical universal Outbound OS campaign from an account list or spreadsheet, a targeting brief, and confirmed inclusion, exclusion, and prioritization rules. Use for first-run onboarding or a new campaign; do not use to execute an already-created campaign.
---

# Outbound OS

Create a neutral, self-contained Outbound OS project. Do not assume an industry, account type, size metric, geography, seller, or email provider. Read and follow [references/onboarding-workflow.md](references/onboarding-workflow.md) for the shared intake, audit, targeting, confirmation, and profile rules.

## Build the project

Create a temporary JSON brief conforming to `references/campaign-contract.md`, then run:

```bash
python3 "<skill-dir>/scripts/build_project.py" build \
  --source "<resolved-source-path>" \
  --brief "<confirmed-brief.json>" \
  --preferred-runtime codex
```

The default destination is `~/Desktop/Outbound OS Projects/<campaign-name-date>/`. Request scoped filesystem approval when needed. The builder is transactional, preserves the original input, saves reusable non-secret team defaults, creates neutral account records, bundles both Codex and Claude runtimes, and validates the generated project.

## Handoff

Do not begin account research or create mailbox drafts in the builder task. After a successful build, address the user by name and label the response `Phase 2 — open the generated project`.

Show the clickable exact generated folder, its full path, counts, confirmed rules, and selected channels. Then give these instructions without shortening them:

1. **Do not type `run` in this current builder task.** Do not attach or mention the generated folder here; attaching a folder is not the same as opening a local project.
2. In Codex, open **Projects** and choose **Add local project**.
3. In the folder picker, navigate to `Desktop` → `Outbound OS Projects`.
4. Select the exact generated campaign folder named in `project_folder_name`. Do not select the shared `Outbound OS Projects` parent folder.
5. Confirm the selected folder contains `AGENTS.md`, `CLAUDE.md`, `PROJECT_INPUT.json`, `.agents/skills/run-outbound-campaign/SKILL.md`, and `.claude/skills/run-outbound-campaign/SKILL.md`.
6. Start a **new task inside that local project**. Verify the task's project/folder is the exact generated campaign folder before continuing.
7. Type exactly `run` in that new task.

If the user types `run` in the builder task, do not execute or fall back to the template. Address them by name and repeat the Phase 2 instructions with the exact generated path.

Nothing in onboarding authorizes sending messages.
