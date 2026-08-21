# {{USER_NAME}}, launch this campaign from the local project

- Campaign: `{{CAMPAIGN_NAME}}`
- Campaign ID: `{{CAMPAIGN_ID}}`
- Source: `{{SOURCE_NAME}}`
- Accounts: `{{ACCOUNT_COUNT}}`
- Channels: `{{CHANNELS}}`

Before launching, confirm the session is opened inside the exact generated campaign folder. Do not run from the original builder task or attach this folder there.

- **Codex:** confirm `.agents/skills/run-outbound-campaign/SKILL.md` exists, then type exactly `run`.
- **Claude Code:** confirm `.claude/skills/run-outbound-campaign/SKILL.md` exists, then invoke `/run-outbound-campaign`.
