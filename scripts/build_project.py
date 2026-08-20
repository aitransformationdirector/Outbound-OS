#!/usr/bin/env python3
"""Audit account sources and build validated universal Outbound OS projects."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


BUILDER_VERSION = "2.1.0"
NAME_HEADERS = {"account", "account_name", "business_name", "company", "company_name", "name", "organisation", "organization", "publisher_name"}
WEB_HEADERS = {"business_domain", "canonical_domain", "company_domain", "domain", "publisher_domain", "site", "url", "website", "website_url"}
ALLOWED_CHANNELS = {"gmail", "outlook", "manual_export"}
RULE_KINDS = {"must_match", "exclude", "prioritize"}
SENSITIVE_KEY = re.compile(r"(?:api.?key|cookie|credential|password|secret|token)", re.I)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slug(value: str, fallback: str = "campaign") -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or fallback


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def source_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().casefold()).strip("_")


def clean_domain(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    candidate = text if "://" in text else "https://" + text
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").casefold().strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host if "." in host and " " not in host else ""


def looks_like_domain(value: str) -> bool:
    return bool(clean_domain(value))


def read_delimited(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return [], []
    if path.suffix.casefold() == ".txt" and all(sep not in text.splitlines()[0] for sep in (",", "\t", ";")):
        values = [line.strip() for line in text.splitlines() if line.strip()]
        header = "website" if values and sum(looks_like_domain(v) for v in values) >= len(values) / 2 else "account_name"
        return [header], [{header: value} for value in values]
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel_tab if path.suffix.casefold() == ".tsv" else csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    headers = [str(value or "") for value in (reader.fieldnames or [])]
    return headers, [{str(k or ""): str(v or "").strip() for k, v in row.items()} for row in reader]


def _xlsx_cell_text(cell: ET.Element, shared: list[str], ns: dict[str, str]) -> str:
    kind = cell.attrib.get("t")
    value = cell.find("x:v", ns)
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//x:t", ns))
    if value is None or value.text is None:
        return ""
    if kind == "s":
        try:
            return shared[int(value.text)]
        except (IndexError, ValueError):
            return ""
    return value.text


def read_xlsx(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//x:t", ns)) for item in root.findall("x:si", ns)]
        sheets = sorted(name for name in archive.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
        if not sheets:
            return [], []
        root = ET.fromstring(archive.read(sheets[0]))
        matrix: list[list[str]] = []
        for row in root.findall(".//x:sheetData/x:row", ns):
            values: dict[int, str] = {}
            for cell in row.findall("x:c", ns):
                ref = cell.attrib.get("r", "A1")
                letters = re.match(r"[A-Z]+", ref)
                index = 0
                for char in (letters.group(0) if letters else "A"):
                    index = index * 26 + ord(char) - 64
                values[index - 1] = _xlsx_cell_text(cell, shared, ns)
            width = max(values, default=-1) + 1
            matrix.append([values.get(i, "") for i in range(width)])
    if not matrix:
        return [], []
    headers = [str(value).strip() for value in matrix[0]]
    rows = [{headers[i]: str(row[i] if i < len(row) else "").strip() for i in range(len(headers))} for row in matrix[1:]]
    return headers, rows


def read_source(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    suffix = path.suffix.casefold()
    if suffix in {".csv", ".tsv", ".txt"}:
        return read_delimited(path)
    if suffix == ".xlsx":
        return read_xlsx(path)
    raise ValueError("Source must be CSV, TSV, XLSX, or TXT")


def pick_column(headers: list[str], candidates: set[str]) -> str | None:
    for header in headers:
        if normalize_header(header) in candidates:
            return header
    return None


def import_accounts(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    headers, source_rows = read_source(path)
    if not headers:
        raise ValueError("Account source is empty or has no header")
    name_column = pick_column(headers, NAME_HEADERS)
    web_column = pick_column(headers, WEB_HEADERS)
    if not name_column and not web_column and len(headers) == 1:
        web_column = headers[0] if any(looks_like_domain(row.get(headers[0], "")) for row in source_rows) else None
        name_column = None if web_column else headers[0]
    if not name_column and not web_column:
        raise ValueError("Could not find an account-name or website column")

    accounts: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicates = unusable = missing_names = missing_websites = 0
    for row_number, row in enumerate(source_rows, start=2):
        name = str(row.get(name_column, "") if name_column else "").strip()
        supplied_website = str(row.get(web_column, "") if web_column else "").strip()
        domain = clean_domain(supplied_website)
        if not name and not domain:
            unusable += 1
            continue
        key = "domain:" + domain if domain else "name:" + slug(name, "unknown")
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        if not name:
            missing_names += 1
            name = domain.split(".")[0].replace("-", " ").title()
        if not domain:
            missing_websites += 1
        account_id = "acct-" + hashlib.sha256(key.encode()).hexdigest()[:12]
        accounts.append({
            "schema_version": 1,
            "account_id": account_id,
            "source_row": row_number,
            "supplied_name": str(row.get(name_column, "") if name_column else "").strip() or None,
            "supplied_website": supplied_website or None,
            "canonical_name": name,
            "canonical_domain": domain or None,
            "original_fields": row,
            "resolution_status": "resolved" if domain else "needs_review",
            "qualification_status": "pending_research" if domain else "needs_review",
            "priority": None,
            "evidence": [],
        })
    if not accounts:
        raise ValueError("Account source contains no usable accounts")
    audit = {
        "source_rows": len(source_rows),
        "imported_accounts": len(accounts),
        "duplicates": duplicates,
        "unusable_rows": unusable,
        "missing_names": missing_names,
        "missing_websites": missing_websites,
        "available_columns": headers,
        "name_column": name_column,
        "website_column": web_column,
    }
    return accounts, audit


def recommendations(context: str, headers: list[str]) -> list[dict[str, str]]:
    text = (context + " " + " ".join(headers)).casefold()
    suggestions: list[tuple[str, str, str]] = []
    if any(word in text for word in ("hotel", "resort", "hospitality")):
        suggestions.extend([
            ("property-footprint", "Property count separates single locations from groups.", "Official location directory or supplied data"),
            ("market-fit", "Operating markets may materially affect offer relevance.", "Current location pages or supplied data"),
        ])
    if any(word in text for word in ("tourism", "destination", "visitor")):
        suggestions.append(("geographic-remit", "The organization's formal remit can prevent out-of-area targeting.", "Official mandate or about page"))
    if any(word in text for word in ("media", "content", "audience", "website")):
        suggestions.extend([
            ("audience-scale", "Audience size may help distinguish viable accounts when it matters to the offer.", "Supplied metric or reputable current estimate"),
            ("business-model", "Business model can separate relevant commercial sites from incompatible site types.", "Current site and commercial pages"),
        ])
    if any(word in text for word in ("technology", "software", "platform", "ad tech", "adtech")):
        suggestions.extend([
            ("company-scale", "Team or revenue scale may indicate buying capacity.", "Supplied data or current authoritative company source"),
            ("technology-category", "A precise category check can remove adjacent but irrelevant companies.", "Current product documentation or company website"),
        ])
    if not suggestions:
        suggestions.extend([
            ("market-fit", "Confirming served markets can prevent geographically irrelevant outreach.", "Current company website or supplied data"),
            ("organization-scale", "A campaign-relevant size measure can improve prioritization.", "Supplied data or current authoritative source"),
        ])
    unique: list[dict[str, str]] = []
    for identifier, rationale, evidence in suggestions:
        if any(row["recommendation_id"] == identifier for row in unique):
            continue
        unique.append({
            "recommendation_id": identifier,
            "rationale": rationale,
            "evidence_requirement": evidence,
            "expected_coverage": "Depends on supplied columns and publicly verifiable evidence",
            "active": False,
        })
    return unique


def validate_brief(brief: dict[str, Any]) -> None:
    required = ("campaign_name", "goal", "desired_outcome", "offer", "account_definition", "team_profile", "channels", "targeting_rules")
    for key in required:
        if key not in brief or brief[key] in (None, ""):
            raise ValueError(f"Brief is missing {key}")
    if brief.get("confirmed") is not True:
        raise ValueError("Brief must be explicitly confirmed before build")
    channels = brief.get("channels")
    if not isinstance(channels, list) or not channels or set(channels) - ALLOWED_CHANNELS:
        raise ValueError("Channels must use gmail, outlook, or manual_export")
    profile = brief.get("team_profile")
    if not isinstance(profile, dict) or not profile.get("profile_name") or not profile.get("user_name") or not profile.get("organization"):
        raise ValueError("Team profile requires profile_name, user_name, and organization")
    if not isinstance(profile.get("senders"), list) or not profile["senders"] or not profile["senders"][0].get("name"):
        raise ValueError("Team profile requires at least one named sender")
    def walk(value: Any, path: str = "team_profile") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if SENSITIVE_KEY.search(str(key)):
                    raise ValueError(f"Credentials are forbidden in {path}.{key}")
                walk(child, path + "." + str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
    walk(profile)
    for rule in brief.get("targeting_rules", []):
        if rule.get("kind") not in RULE_KINDS:
            raise ValueError(f"Invalid targeting rule kind: {rule.get('kind')}")
        if not rule.get("rule_id") or not rule.get("statement"):
            raise ValueError("Every targeting rule requires rule_id and statement")
        if rule["kind"] in {"must_match", "exclude"} and rule.get("unknown_handling") != "needs_review":
            raise ValueError("Hard targeting rules must send unknown evidence to needs_review")


def run_checked(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or "validation failed")


def render(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for token, value in replacements.items():
        text = text.replace(token, value)
    path.write_text(text, encoding="utf-8")


def save_team_profile(shared_root: Path, profile: dict[str, Any]) -> None:
    path = shared_root / "team-profiles.json"
    payload = read_json(path) if path.is_file() else {"schema_version": 1, "profiles": []}
    profiles = [row for row in payload.get("profiles", []) if row.get("profile_name") != profile.get("profile_name")]
    stored = dict(profile)
    stored["updated_at"] = now_iso()
    profiles.append(stored)
    temporary = path.with_suffix(".tmp")
    write_json(temporary, {"schema_version": 1, "profiles": profiles})
    os.replace(temporary, path)


def build_project(source: Path, brief_path: Path, output_root: Path) -> dict[str, Any]:
    source = source.expanduser().resolve()
    brief_path = brief_path.expanduser().resolve()
    if not source.is_file() or not brief_path.is_file():
        raise ValueError("Source and confirmed brief files are required")
    brief = read_json(brief_path)
    validate_brief(brief)
    accounts, audit = import_accounts(source)
    digest = source_hash(source)
    fingerprint_payload = json.dumps({"builder_version": BUILDER_VERSION, "source_sha256": digest, "brief": brief}, sort_keys=True, ensure_ascii=False)
    fingerprint = hashlib.sha256(fingerprint_payload.encode()).hexdigest()
    date_label = dt.datetime.now().astimezone().date().isoformat()
    base_name = f"{slug(brief['campaign_name'])}-{date_label}"
    output_root = output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    shared_root = output_root / "_shared"
    shared_root.mkdir(exist_ok=True)
    suffix = 1
    while True:
        destination = output_root / (base_name if suffix == 1 else f"{base_name}-{suffix}")
        receipt_path = destination / "BUILD_RECEIPT.json"
        if receipt_path.is_file():
            receipt = read_json(receipt_path)
            if receipt.get("input_fingerprint") == fingerprint:
                return {**receipt, "resumed": True}
        if not destination.exists():
            break
        suffix += 1

    template = Path(__file__).resolve().parent.parent / "assets/project-template"
    temporary = Path(tempfile.mkdtemp(prefix=f".{base_name}.building-", dir=output_root))
    try:
        shutil.copytree(template, temporary, dirs_exist_ok=True)
        for relative in ("00_INBOX", "01_CAMPAIGNS", "02_REVIEW", "03_OUTPUTS"):
            (temporary / relative).mkdir(parents=True, exist_ok=True)
        campaign_id = f"campaign-{slug(brief['campaign_name'])}-{fingerprint[:8]}"
        campaign_root = temporary / "01_CAMPAIGNS" / campaign_id
        (campaign_root / "source").mkdir(parents=True)
        (campaign_root / "state").mkdir()
        shutil.copy2(source, temporary / "00_INBOX" / source.name)
        write_jsonl(campaign_root / "source/accounts.jsonl", accounts)
        write_json(campaign_root / "state/campaign.json", {
            "schema_version": 1,
            "campaign_id": campaign_id,
            "stage": "ready",
            "brief": brief,
            "source": {"name": source.name, "sha256": digest},
            "account_counts": audit,
            "external_actions": {"sending_authorized": False, "drafts_require_review": True},
            "created_at": now_iso(),
        })
        project_input = {
            "schema_version": 1,
            "builder_version": BUILDER_VERSION,
            "status": "ready",
            "campaign_id": campaign_id,
            "campaign_name": brief["campaign_name"],
            "user_name": brief["team_profile"]["user_name"],
            "project_root": str(destination),
            "runtime_skill_path": ".agents/skills/run-outbound-campaign/SKILL.md",
            "source": {"name": source.name, "sha256": digest},
            "brief": brief,
            "audit": audit,
            "next_prompt": "run",
            "prepared_at": now_iso(),
        }
        write_json(temporary / "PROJECT_INPUT.json", project_input)
        replacements = {
            "{{CAMPAIGN_NAME}}": brief["campaign_name"],
            "{{CAMPAIGN_ID}}": campaign_id,
            "{{USER_NAME}}": brief["team_profile"]["user_name"],
            "{{SOURCE_NAME}}": source.name,
            "{{ACCOUNT_COUNT}}": str(audit["imported_accounts"]),
            "{{CHANNELS}}": ", ".join(brief["channels"]),
        }
        for relative in ("START_HERE.md", "RUN.md"):
            render(temporary / relative, replacements)
        validator = temporary / "system/scripts/validate_system.py"
        engine = temporary / ".agents/skills/run-outbound-campaign/scripts/campaign_engine.py"
        run_checked([sys.executable, str(validator), "--root", str(temporary)], temporary)
        run_checked([sys.executable, str(engine), "--root", str(temporary), "validate", "--campaign", campaign_id], temporary)
        receipt = {
            "schema_version": 1,
            "builder_version": BUILDER_VERSION,
            "project_path": str(destination),
            "project_folder_name": destination.name,
            "parent_path": str(output_root),
            "campaign_id": campaign_id,
            "input_fingerprint": fingerprint,
            "counts": audit,
            "channels": brief["channels"],
            "targeting_rules": brief["targeting_rules"],
            "built_at": now_iso(),
            "next_prompt": "run",
            "handoff": {
                "user_name": brief["team_profile"]["user_name"],
                "must_open_as_local_project": True,
                "do_not_run_in_builder_task": True,
                "do_not_attach_folder_to_builder_task": True,
                "exact_project_path": str(destination),
                "project_folder_name": destination.name,
                "required_markers": [
                    "AGENTS.md",
                    "PROJECT_INPUT.json",
                    ".agents/skills/run-outbound-campaign/SKILL.md",
                ],
            },
            "resumed": False,
        }
        write_json(temporary / "BUILD_RECEIPT.json", receipt)
        os.replace(temporary, destination)
        if brief.get("save_team_profile"):
            save_team_profile(shared_root, brief["team_profile"])
        return receipt
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("--source", required=True)
    audit.add_argument("--context", default="")
    build = commands.add_parser("build")
    build.add_argument("--source", required=True)
    build.add_argument("--brief", required=True)
    build.add_argument("--output-root", default=str(Path.home() / "Desktop/Codex/Outbound OS Projects"))
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "audit":
            source = Path(args.source).expanduser().resolve()
            accounts, audit = import_accounts(source)
            print(json.dumps({"audit": audit, "sample": accounts[:5], "suggested_filters": recommendations(args.context, audit["available_columns"])}, indent=2, ensure_ascii=False))
        else:
            result = build_project(Path(args.source), Path(args.brief), Path(args.output_root))
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
