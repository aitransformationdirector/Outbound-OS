---
name: monitor-outbound-replies
description: Perform a read-only reply check for a prepared Outbound OS campaign through its configured Gmail or Outlook adapter, normalize matching evidence, and refresh local follow-up state. Never send, reply, or change mailbox content.
---

# Monitor Outbound Replies

Read the campaign's configured channels and proposed-action receipts. Use only an available selected mailbox adapter. Search narrowly by recorded destination, subject, draft/message identifiers, and timestamps; do not perform unrelated mailbox triage.

Normalize adapter results with:

```bash
python3 .agents/skills/monitor-outbound-replies/scripts/normalize_replies.py \
  --root . --campaign "<campaign-id>" --input "<adapter-results.jsonl>"
```

Every result records its adapter, account ID, checked time, message evidence, and classification. Automated notices, bounces, and out-of-office messages are not substantive replies. This workflow is read-only and never sends, replies, edits, deletes, labels, or moves mailbox content.
