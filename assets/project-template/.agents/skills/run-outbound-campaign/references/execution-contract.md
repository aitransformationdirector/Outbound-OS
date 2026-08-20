# Execution contract

## Qualification

Every rule result includes rule ID, result (`pass`, `fail`, or `unknown`), evidence URL, checked date, and note. Mandatory-rule failures and matched exclusions produce `excluded`; unknown hard-rule evidence produces `needs_review`; ranking signals affect order only.

## Review gates

The calibration review contains exactly three varied accounts. The complete preflight contains every account, its terminal status, rule evidence, suppression result, exact canonical message, destination, channel, and proposed action.

## Channel adapters

- `gmail` creates a Gmail draft through an available app connection.
- `outlook` creates an Outlook draft through an available app connection.
- `manual_export` creates a local, copy-ready item when no mailbox connection is available or the route is manual.

Before a mailbox draft operation, verify the adapter connection, re-list campaign drafts, check for duplicates or drift, and compare the action to the canonical message. Create only the approved draft. Never send or schedule it.

Adapter unavailability affects only that action. Offer `manual_export` without changing its message.

## CRM and monitoring

Reply checks use the same adapter boundary and are read-only. CRM export is channel-neutral and includes only substantive replies, confirmed interactions, or qualified opportunities. It never mutates a live CRM.
