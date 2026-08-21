# Execution contract

## Qualification

Every rule result includes rule ID, result (`pass`, `fail`, or `unknown`), evidence URL, checked date, and note. Mandatory-rule failures and matched exclusions produce `excluded`; unknown hard-rule evidence produces `needs_review`; ranking signals affect order only.

## Review gates

The calibration review contains exactly three varied accounts. The complete preflight contains every account, its terminal status, rule evidence, suppression result, exact canonical message, destination, channel, and proposed action.

## Channel capabilities

- `gmail` creates a Gmail draft only when the active host has an available Gmail connection or tool.
- `outlook` creates an Outlook draft only when the active host has an available Outlook connection or tool.
- `manual_export` creates a local, copy-ready item and is always available.

Before a mailbox draft operation, verify current capability availability, re-list campaign drafts, check for duplicates or drift, and compare the action to the canonical message. Create only the approved draft. Never send or schedule it.

Capability unavailability affects only that action. Offer `manual_export` without changing its message.

## CRM and monitoring

Reply checks use the same capability boundary and are read-only. CRM export is channel-neutral and includes only substantive replies, confirmed interactions, or qualified opportunities. It never mutates a live CRM.
