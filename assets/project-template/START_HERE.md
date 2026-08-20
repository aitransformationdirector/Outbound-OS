# {{USER_NAME}}, your campaign project is ready

This Outbound OS project is prepared for **{{CAMPAIGN_NAME}}**.

- Source: `{{SOURCE_NAME}}`
- Imported accounts: `{{ACCOUNT_COUNT}}`
- Channels: `{{CHANNELS}}`
- Campaign ID: `{{CAMPAIGN_ID}}`

## Open the correct folder in Codex

Do not attach this folder to the campaign-builder task, and do not type `run` in that old task. An attachment is not a local project.

1. In Codex, open **Projects** and choose **Add local project**.
2. Navigate to `Desktop` → `Codex` → `Outbound OS Projects`.
3. Select this exact campaign folder—the folder containing this `START_HERE.md` file. Do not select the shared `Outbound OS Projects` parent.
4. Confirm the selected folder contains:
   - `AGENTS.md`
   - `PROJECT_INPUT.json`
   - `.agents/skills/run-outbound-campaign/SKILL.md`
5. Start a **new task inside this local project**.
6. Verify the task's project/folder name matches this campaign folder.
7. Type exactly `run` in that new task.

The run pauses for a three-account calibration review and a complete action preflight. Approval may create an exact draft or manual follow-up item. It never authorizes sending or submission.
