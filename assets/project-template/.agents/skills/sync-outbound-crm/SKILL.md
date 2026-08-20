---
name: sync-outbound-crm
description: Produce a channel-neutral CRM export from substantive campaign conversations and confirmed commercial interactions. Use after reply evidence exists; never use it to prospect, import, or mutate a live CRM.
---

# Sync Outbound CRM

Read the campaign's normalized relationship evidence and run:

```bash
python3 .agents/skills/sync-outbound-crm/scripts/crm_export.py \
  --root . --campaign "<campaign-id>"
```

Only `substantive_reply`, `confirmed_interaction`, and `qualified_opportunity` records enter the primary JSONL and CSV exports. Account for other relationship records in the exclusions output. Preserve stable account IDs and evidence. Never import, deploy, or change a live CRM.
