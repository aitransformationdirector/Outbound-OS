#!/usr/bin/env python3
"""Materialize and configure a ready-to-run Codex SSP outreach project."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


TOKENS = (
    "{{TARGET_PROVIDER}}",
    "{{MINIMUM_MONTHLY_TRAFFIC}}",
    "{{TARGET_VERTICALS}}",
    "{{TARGET_GEOGRAPHIES}}",
    "{{SOURCE_NAME}}",
    "{{CAMPAIGN_ID}}",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "ssp"


def project_label(value: str) -> str:
    words = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return words or "SSP-Outreach"


def parse_threshold(value: str) -> int:
    text = str(value).strip().casefold().replace(",", "")
    multiplier = 1
    if text.endswith("k"):
        multiplier, text = 1_000, text[:-1]
    elif text.endswith("m"):
        multiplier, text = 1_000_000, text[:-1]
    try:
        parsed = int(float(text) * multiplier)
    except ValueError as exc:
        raise ValueError(f"Invalid monthly-traffic threshold: {value!r}") from exc
    if parsed <= 0:
        raise ValueError("Monthly-traffic threshold must be greater than zero")
    return parsed


def split_values(value: str, normalize: bool) -> list[str]:
    raw = [
        part.strip()
        for part in re.split(r"[,;|]", value or "")
        if part.strip()
    ]
    values: list[str] = []
    for item in raw:
        if normalize:
            item = re.sub(r"[^a-z0-9]+", "_", item.casefold()).strip("_")
        if item and item not in values:
            values.append(item)
    return values


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_checked(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise ValueError(message)
    return result


def input_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def find_destination(
    output_root: Path, base_name: str, fingerprint: str
) -> tuple[Path, dict[str, Any] | None]:
    suffix = 1
    while True:
        name = base_name if suffix == 1 else f"{base_name}-{suffix}"
        candidate = output_root / name
        if not candidate.exists():
            return candidate, None
        receipt_path = candidate / "BUILD_RECEIPT.json"
        if receipt_path.is_file():
            try:
                receipt = read_json(receipt_path)
            except (OSError, json.JSONDecodeError):
                receipt = {}
            if receipt.get("input_fingerprint") == fingerprint:
                return candidate, receipt
        suffix += 1


def render_tokens(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for token, value in replacements.items():
        text = text.replace(token, value)
    path.write_text(text, encoding="utf-8")


def build(args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.source).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"Source CSV not found: {source}")
    if source.suffix.casefold() != ".csv":
        raise ValueError("Source input must be a .csv file")
    provider = args.provider.strip()
    if not provider:
        raise ValueError("SSP/ad-manager name is required")
    if len(provider) > 120 or "\n" in provider or "\r" in provider:
        raise ValueError("SSP/ad-manager name must be one line and at most 120 characters")

    threshold = parse_threshold(args.minimum_monthly_traffic)
    verticals = split_values(args.verticals, normalize=True)
    if not verticals:
        raise ValueError("At least one target vertical is required")
    geographies = split_values(args.geographies, normalize=False)
    source_hash = hash_file(source)
    effective_note = args.note.strip()
    identity = {
        "source_sha256": source_hash,
        "provider": provider.casefold(),
        "minimum_monthly_traffic": threshold,
        "target_verticals": verticals,
        "target_geographies": geographies,
        "note": effective_note,
        "outreach_company": args.outreach_company,
        "sender_name": args.sender_name,
        "sender_email": args.sender_email,
    }
    fingerprint = input_fingerprint(identity)

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    shared_root = output_root / "_shared"
    shared_root.mkdir(parents=True, exist_ok=True)
    suppression_memory = shared_root / "suppression-memory.jsonl"
    suppression_memory.touch(exist_ok=True)
    date_label = dt.datetime.now().astimezone().date().isoformat()
    base_name = project_label(
        args.project_label or f"SSP-{provider}-{date_label}"
    )
    destination, existing_receipt = find_destination(
        output_root, base_name, fingerprint
    )
    if existing_receipt is not None:
        return {
            "project_path": str(destination),
            "campaign_id": existing_receipt["campaign_id"],
            "resumed": True,
            "next_prompt": "run",
            "counts": existing_receipt.get("counts", {}),
            "effective_config": existing_receipt.get("effective_config", {}),
        }

    template = (
        Path(__file__).resolve().parent.parent / "assets/project-template"
    )
    if not (template / "AGENTS.md").is_file():
        raise ValueError(f"Bundled project template is incomplete: {template}")

    temporary = Path(
        tempfile.mkdtemp(prefix=f".{base_name}.building-", dir=output_root)
    )
    try:
        shutil.copytree(template, temporary, dirs_exist_ok=True)
        defaults_path = temporary / "system/defaults.json"
        defaults = read_json(defaults_path)
        defaults["project_name"] = f"{provider} SSP Outreach"
        defaults["outreach_company"] = args.outreach_company
        defaults["sender_name"] = args.sender_name
        defaults["sender_email"] = args.sender_email
        defaults["selection"]["minimum_monthly_pageviews"] = threshold
        defaults["selection"]["target_verticals"] = verticals
        defaults["selection"]["target_geographies"] = geographies
        defaults["selection"]["geography_filter_mode"] = (
            "include" if geographies else "none"
        )
        write_json(defaults_path, defaults)

        launch_note_parts = [
            f"Minimum monthly traffic: {threshold}",
            "Target verticals: " + ", ".join(verticals),
        ]
        if geographies:
            launch_note_parts.append("Target geographies: " + ", ".join(geographies))
        if effective_note:
            launch_note_parts.append(effective_note)
        launch_note = ". ".join(launch_note_parts).rstrip(".") + "."
        campaign_label = f"tiki-{slug(provider)}-{date_label}"
        project_input = {
            "schema_version": 1,
            "status": "building",
            "source_csv": {
                "original_path": str(source),
                "name": source.name,
                "sha256": source_hash,
            },
            "target_provider": provider,
            "minimum_monthly_traffic": threshold,
            "target_verticals": verticals,
            "target_geographies": geographies,
            "user_note": effective_note,
            "launch_note": launch_note,
            "input_fingerprint": fingerprint,
            "suppression_memory_path": str(suppression_memory),
            "next_prompt": "run",
            "created_at": now_iso(),
        }
        write_json(temporary / "PROJECT_INPUT.json", project_input)

        engine = (
            temporary
            / ".agents/skills/run-ssp-outreach/scripts/campaign_engine.py"
        )
        bootstrap = run_checked(
            [
                sys.executable,
                str(engine),
                "--root",
                str(temporary),
                "bootstrap",
                "--source",
                str(source),
                "--provider",
                provider,
                "--note",
                launch_note,
                "--label",
                campaign_label,
            ],
            temporary,
        )
        bootstrap_result = json.loads(bootstrap.stdout)
        campaign_id = bootstrap_result["campaign_id"]
        project_input["status"] = "ready"
        project_input["campaign_id"] = campaign_id
        project_input["prepared_at"] = now_iso()
        write_json(temporary / "PROJECT_INPUT.json", project_input)

        replacements = {
            "{{TARGET_PROVIDER}}": provider,
            "{{MINIMUM_MONTHLY_TRAFFIC}}": f"{threshold:,}",
            "{{TARGET_VERTICALS}}": ", ".join(verticals),
            "{{TARGET_GEOGRAPHIES}}": ", ".join(geographies) or "No restriction",
            "{{SOURCE_NAME}}": source.name,
            "{{CAMPAIGN_ID}}": campaign_id,
        }
        for relative in ("START_HERE.md", "RUN.md"):
            render_tokens(temporary / relative, replacements)
        for token in TOKENS:
            for relative in ("START_HERE.md", "RUN.md"):
                if token in (temporary / relative).read_text(encoding="utf-8"):
                    raise ValueError(f"Unresolved template token {token} in {relative}")

        validator = temporary / "system/scripts/validate_system.py"
        run_checked(
            [sys.executable, str(validator), "--root", str(temporary)],
            temporary,
        )
        run_checked(
            [
                sys.executable,
                str(engine),
                "--root",
                str(temporary),
                "validate",
                "--campaign",
                campaign_id,
            ],
            temporary,
        )
        counts = {
            key: bootstrap_result.get(key, 0)
            for key in (
                "parsed_rows",
                "invalid_url_rows",
                "eligible",
                "below_threshold",
                "unknown_traffic",
                "unknown_geography",
                "excluded_geography",
                "unique_hostnames",
            )
        }
        receipt = {
            "schema_version": 1,
            "project_path": str(destination),
            "campaign_id": campaign_id,
            "input_fingerprint": fingerprint,
            "source_sha256": source_hash,
            "source_name": source.name,
            "suppression_memory_path": str(suppression_memory),
            "effective_config": {
                "target_provider": provider,
                "minimum_monthly_traffic": threshold,
                "target_verticals": verticals,
                "target_geographies": geographies,
                "user_note": effective_note,
            },
            "counts": counts,
            "built_at": now_iso(),
            "next_prompt": "run",
        }
        write_json(temporary / "BUILD_RECEIPT.json", receipt)
        os.replace(temporary, destination)
        return {
            "project_path": str(destination),
            "campaign_id": campaign_id,
            "resumed": False,
            "next_prompt": "run",
            "counts": counts,
            "effective_config": receipt["effective_config"],
        }
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--minimum-monthly-traffic", default="50000")
    parser.add_argument("--verticals", default="travel,travel_adjacent")
    parser.add_argument("--geographies", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--project-label")
    parser.add_argument(
        "--output-root",
        default=str(Path.home() / "Desktop/Codex/SSP Projects"),
    )
    parser.add_argument("--outreach-company", default="TIKI")
    parser.add_argument("--sender-name", default="Dean")
    parser.add_argument("--sender-email", default="dean@tiki.com")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        print(json.dumps(build(args), indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
