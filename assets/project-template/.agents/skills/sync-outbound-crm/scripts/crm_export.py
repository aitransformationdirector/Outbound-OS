#!/usr/bin/env python3
"""Create neutral, import-ready CRM files without mutating a CRM."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


ELIGIBLE = {"substantive_reply", "confirmed_interaction", "qualified_opportunity"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def export(root: Path, campaign_id: str) -> dict[str, int]:
    campaign = root / "01_CAMPAIGNS" / campaign_id
    relationships = read_jsonl(campaign / "state/relationships.jsonl")
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in relationships:
        if row.get("campaign_id") != campaign_id or not row.get("account_id"):
            raise ValueError("Relationship records require matching campaign_id and account_id")
        status = row.get("relationship_status")
        if status in ELIGIBLE and row.get("evidence"):
            included.append(row)
        else:
            excluded.append({"campaign_id": campaign_id, "account_id": row["account_id"], "reason": "not_conversation_backed" if status not in ELIGIBLE else "missing_evidence"})
    output = root / "03_OUTPUTS" / campaign_id / "crm"
    write_jsonl(output / "accounts.jsonl", included)
    write_jsonl(output / "exclusions.jsonl", excluded)
    csv_path = output / "accounts.csv"
    fields = ["campaign_id", "account_id", "account_name", "relationship_status"]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in included:
            writer.writerow({key: row.get(key, "") for key in fields})
    return {"included": len(included), "excluded": len(excluded)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--campaign", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(export(Path(args.root).expanduser().resolve(), args.campaign), indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
