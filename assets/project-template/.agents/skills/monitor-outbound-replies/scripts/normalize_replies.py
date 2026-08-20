#!/usr/bin/env python3
"""Normalize read-only mailbox adapter results into campaign evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ADAPTERS = {"gmail", "outlook"}
CLASSIFICATIONS = {"substantive_reply", "automated", "bounce", "out_of_office", "no_reply"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError("Adapter result file is missing")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize(root: Path, campaign_id: str, input_path: Path) -> int:
    normalized: list[dict[str, Any]] = []
    for row in read_jsonl(input_path):
        if row.get("adapter") not in ADAPTERS:
            raise ValueError("Reply result has an invalid adapter")
        if row.get("classification") not in CLASSIFICATIONS:
            raise ValueError("Reply result has an invalid classification")
        for key in ("account_id", "checked_at", "evidence"):
            if not row.get(key):
                raise ValueError(f"Reply result lacks {key}")
        normalized.append({"schema_version": 1, "campaign_id": campaign_id, **row})
    output = root / "01_CAMPAIGNS" / campaign_id / "state/reply-evidence.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in normalized), encoding="utf-8")
    return len(normalized)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    try:
        count = normalize(Path(args.root).expanduser().resolve(), args.campaign, Path(args.input).expanduser().resolve())
        print(json.dumps({"normalized": count}, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
