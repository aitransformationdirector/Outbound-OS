# Builder input contract

## Required inputs

- `source`: readable `.csv` file containing a URL/domain column.
- `provider`: non-empty SSP or advertising-manager name.

Do not infer either value.

## Defaults

- Output root: `~/Desktop/Codex/SSP Projects`
- Minimum monthly traffic: `50000`
- Target verticals: `travel,travel_adjacent`
- Geographies: unrestricted
- Outreach company: `TIKI`
- Sender: `Dean <dean@tiki.com>`

## Threshold parsing

Accept whole numbers with commas and compact suffixes:

- `50000`
- `50,000`
- `50k`
- `1.5m`

Reject zero, negative, or non-numeric thresholds.

## List parsing

Accept comma, semicolon, or pipe-separated verticals and geographies. Normalize verticals to lowercase underscore labels while preserving geography display values.

Examples:

- `travel or travel adjacent` becomes `travel,travel_adjacent` when the user clearly names both criteria;
- `travel, food & drink` becomes `travel,food_drink`;
- blank geography means no geography restriction.

## Destination behavior

Create one self-contained project per distinct input fingerprint. The fingerprint covers:

- source bytes;
- provider;
- threshold;
- verticals;
- geographies;
- note;
- TIKI/sender settings.

If an existing project has the same fingerprint, return it as `resumed: true`. Never overwrite an existing project with a different fingerprint; add a numeric suffix.

Build in a hidden temporary sibling directory and rename only after validation succeeds.

## Build boundary

The builder prepares state only. It must not:

- research the provider or publishers;
- use Gmail;
- create a review site;
- create drafts;
- send or submit anything.

The generated project owns campaign execution after the user opens it and types `run`.

