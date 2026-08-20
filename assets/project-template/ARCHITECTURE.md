# Architecture

Outbound OS separates campaign intent, account evidence, canonical messaging, human approval, and channel execution.

1. `PROJECT_INPUT.json` contains the confirmed brief and import audit.
2. `01_CAMPAIGNS/<campaign_id>/source/accounts.jsonl` preserves normalized source accounts.
3. Research produces rule-level evidence and a terminal qualification for every account.
4. A calibration review tests targeting and copy on three varied accounts.
5. A complete preflight shows every account and exact proposed action.
6. Approved actions are translated by a channel adapter without changing canonical copy.
7. CRM exports include only conversation-backed records and do not mutate live systems.

Unknown evidence never silently fails a hard rule. Sending is always outside project authority.
