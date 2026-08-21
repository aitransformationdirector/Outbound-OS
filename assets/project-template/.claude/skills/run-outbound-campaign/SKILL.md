---
name: run-outbound-campaign
description: Execute a prepared universal Outbound OS campaign from its confirmed brief, with evidence-backed qualification, review gates, and no automatic sending. Do not use for campaign onboarding.
---

# Run Outbound Campaign

This is the Claude Code entry point bundled inside the generated project. Before any work, verify the current project root contains `CLAUDE.md`, `PROJECT_INPUT.json`, this exact relative file, and `system/runtime/campaign_engine.py`. If not, stop and direct the user to open the exact generated campaign folder; never fall back to another project, plugin, or template.

Read `PROJECT_INPUT.json`, address the user by its `user_name` at least once in every response, then read the campaign state and [the shared execution contract](../../../system/runtime/execution-contract.md). Validate before work:

```bash
python3 system/runtime/campaign_engine.py --root . validate --campaign "<campaign-id>"
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
9. Convert approved messages to channel-neutral proposed actions. Use a selected, available adapter only after approval, preserve exact copy, and never send.
10. Produce CRM export records only for conversation-backed accounts.

Use the shared runtime to create validated neutral action records. Adapter availability is host-specific; if a configured mailbox capability is unavailable, hold the action and offer `manual_export` without changing the canonical message.
