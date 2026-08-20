---
name: run-outbound-campaign
description: Execute a prepared universal Outbound OS campaign from its confirmed brief, researching and qualifying every account, producing two review gates, and creating only explicitly approved drafts or local actions. Do not use for campaign onboarding.
---

# Run Outbound Campaign

This skill is bundled inside the generated project. Before any work, verify the current project root contains `PROJECT_INPUT.json` and this exact relative file. If not, stop and direct the user to open the exact generated folder as a local Codex project; never fall back to a template or another installation.

Read `PROJECT_INPUT.json`, address the user by its `user_name` at least once in every response, then read the campaign state and [references/execution-contract.md](references/execution-contract.md). Validate before work:

```bash
python3 .agents/skills/run-outbound-campaign/scripts/campaign_engine.py \
  --root . validate --campaign "<campaign-id>"
```

## Execute

1. Resolve accounts that lack a confident website. Put ambiguous results in `needs_review`.
2. Research each confirmed targeting rule and record source URLs, checked dates, and explicit pass/fail/unknown results.
3. Apply mandatory and exclusion rules. Unknown evidence for either ends in `needs_review`. Apply prioritization only after eligibility.
4. Account for every source row as qualified, excluded, needs review, or failed.
5. Discover one current route appropriate to the configured channels. Do not infer addresses.
6. Draft one versioned canonical message per actionable account.
7. Create a three-account calibration review with varied account and rule outcomes.
8. Apply feedback, run suppression checks, and create a complete preflight for all accounts.
9. Convert approved messages to channel-neutral proposed actions. Use the selected adapter only after approval, preserve exact copy, and never send.
10. Produce CRM export records only for conversation-backed accounts.

Use `prepare-actions` to create validated neutral action records from canonical messages. Adapters and safety requirements are defined in [references/execution-contract.md](references/execution-contract.md).
