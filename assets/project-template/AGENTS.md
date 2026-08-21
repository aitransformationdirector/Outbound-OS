# Outbound OS operating rules

This project turns a confirmed target-account brief into evidence-backed, reviewable outreach actions.

## Start and continuity

- At the beginning of every response, read `PROJECT_INPUT.json` and use `user_name` naturally at least once. Do not infer or substitute another name.
- Before acting on `run`, verify that the current project root contains `AGENTS.md`, `CLAUDE.md`, `PROJECT_INPUT.json`, `system/runtime/campaign_engine.py`, and the runtime skill for the current host.
- If any marker is absent from the current project root, do not research accounts and do not use a global skill or external template as a fallback. Tell the user by name that this task is not opened inside the generated project, show `project_root` from `PROJECT_INPUT.json` when available, and instruct them to add that exact folder as a local project and start a new task there.
- Codex uses `.agents/skills/run-outbound-campaign/SKILL.md`; Claude uses `.claude/skills/run-outbound-campaign/SKILL.md`. Hidden paths may not appear in ordinary file searches. Check the applicable exact path directly and include hidden files in searches.
- When the user types exactly `run` and all project-root markers exist, read the bundled skill for the current host, use the campaign ID and confirmed brief, and begin without repeating onboarding. Never substitute the other host's installation, a global skill, or an external template.
- Continue automatically between the calibration review and complete preflight review. Stop only at those gates, for missing authority, or for a genuine blocker.
- Report the current stage, completed and remaining account counts, and next automatic step at material checkpoints.

## Qualification

- Treat `must_match`, `exclude`, and `prioritize` rules differently. Ranking signals never remove accounts.
- Evidence that is unavailable for a hard rule produces `needs_review`, never an inferred pass or exclusion.
- Resolve names and websites from current public evidence. Never guess an ambiguous identity.
- Preserve the supplied row, stable account ID, evidence URL, checked date, and rule-level result.
- Every imported account must finish as `qualified`, `excluded`, `needs_review`, or `failed`.

## Research and messaging

- Research only facts needed by the confirmed brief, qualification rules, personalization, route discovery, and suppression.
- Keep canonical account identity, public brand, and website distinct.
- Store one versioned canonical message per account and review stage. Reviews and channel actions must derive from it without rewriting.
- Do not claim a relationship, result, integration, fit, or characteristic without evidence.

## Reviews and authority

- First create a deliberately varied three-account calibration review.
- After feedback, create a complete review containing every account, rule results, evidence, exact message, recipient or manual route, and proposed action.
- An approved action may create the exact displayed draft or local manual item through its configured adapter.
- Nothing authorizes sending, scheduling, form submission, posting, calling, or changing a live CRM.
- Re-check the exact destination and existing campaign drafts immediately before any authorized draft creation. Suppress duplicates and isolate unexpected drift to affected actions.

## Channels and records

- Campaign state uses the channel-neutral `ProposedAction` contract.
- Channel adapters translate approved actions into mailbox drafts or manual exports. They may not change the canonical message.
- Connections remain app-managed references. Never store credentials, tokens, cookies, passwords, or API keys in project files.
- CRM exports contain account and conversation evidence, not untouched prospects, and never overwrite live CRM state.
