---
name: new-campaign
description: Create a universal Outbound OS campaign from an account list or spreadsheet and confirmed targeting rules. Use for first-run onboarding or a new campaign; do not use to execute an already-created campaign.
---

# New Outbound OS Campaign

Create a neutral, self-contained Outbound OS project. Do not assume an industry, account type, size metric, geography, seller, or email provider.

Read and follow these shared resources before starting intake:

- [Shared onboarding workflow](../../references/onboarding-workflow.md)
- [Campaign contract](../../references/campaign-contract.md)
- [Guided intake](../../references/guided-intake.md)

Use `${CLAUDE_SKILL_DIR}/../../scripts/build_project.py` for audit and build commands. After the user confirms the brief, build with:

```bash
python3 "${CLAUDE_SKILL_DIR}/../../scripts/build_project.py" build \
  --source "<resolved-source-path>" \
  --brief "<confirmed-brief.json>" \
  --preferred-runtime claude
```

The default destination is `~/Desktop/Outbound OS Projects/<campaign-name-date>/`. Request only the filesystem access needed for that folder. The generated project includes both Claude and Codex runtimes.

## Claude handoff

Do not begin account research or create mailbox drafts in the builder conversation. After a successful build, address the user by name and label the response `Phase 2 — open the generated project`.

Show the exact generated folder and full path. Then explain:

1. Do not type `run` in the builder conversation.
2. Open a new Claude Code session rooted at the exact generated campaign folder. In a terminal, run `cd "<exact-generated-path>"` and then `claude`. In Claude Code Desktop, choose that exact folder as the project.
3. Do not choose the shared `Outbound OS Projects` parent folder.
4. Confirm the folder contains `CLAUDE.md`, `PROJECT_INPUT.json`, and `.claude/skills/run-outbound-campaign/SKILL.md`.
5. Start a new conversation in that project and invoke `/run-outbound-campaign`.

If the user types `run` in the builder conversation, do not execute or fall back to the repository template. Repeat the handoff using the exact generated path. Nothing in onboarding authorizes sending messages.
