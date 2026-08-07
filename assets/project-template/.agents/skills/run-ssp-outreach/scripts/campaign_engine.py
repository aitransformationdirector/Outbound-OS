#!/usr/bin/env python3
"""Deterministic state, review, and validation engine for Codex SSP outreach."""

from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


HEADER_ALIASES = {
    "url": ("url", "domain", "website", "site", "publisherurl", "publisherdomain"),
    "pageviews": (
        "monthlypageviews",
        "pageviews",
        "monthlyviews",
        "monthlytraffic",
        "monthlyvisitors",
        "monthlyuniquevisitors",
        "uniquevisitors",
        "visitors",
        "traffic",
        "visits",
    ),
    "category": ("category", "vertical", "sitecategory", "industry"),
    "country": ("country", "geography", "geo", "market"),
    "publisher_name": ("publishername", "sitename", "brand", "publisher"),
    "provider_signal": (
        "domainmanager",
        "admanager",
        "manager",
        "ssp",
        "provider",
        "targetprovider",
    ),
    "contacts": (
        "genericcontactemails",
        "contactemails",
        "email",
        "emails",
        "contact",
    ),
}

GEOGRAPHY_ALIASES = {
    "uk": "united kingdom",
    "u.k.": "united kingdom",
    "great britain": "united kingdom",
    "gb": "united kingdom",
    "us": "united states",
    "u.s.": "united states",
    "usa": "united states",
    "u.s.a.": "united states",
    "united states of america": "united states",
}

PROHIBITED_COLD_COPY = (
    "ads.txt",
    "ssp",
    "dsp",
    "prebid",
    "header bidding",
    "yield",
    "inventory",
    "integration",
    "programmatic",
    "cpm",
)

STAGE_ORDER = (
    "source_audited",
    "provider_profile_ready",
    "candidates_classified",
    "accounts_consolidated",
    "waiting_smoke_review",
    "smoke_approved",
    "waiting_full_review",
    "full_review_approved",
    "actions_complete",
)

NODE_FILES = {
    "provider_profile": ("state/provider_profile.json", "object", ("provider_name",)),
    "classifications": ("state/classifications.jsonl", "records", ("candidate_id",)),
    "accounts": ("state/accounts.jsonl", "records", ("account_id",)),
    "research": ("state/research.jsonl", "records", ("account_id",)),
    "verifications": (
        "state/verifications.jsonl",
        "records",
        ("account_id", "claim_id"),
    ),
    "outreach": (
        "state/outreach.jsonl",
        "records",
        ("account_id", "review_stage"),
    ),
    "suppressions": (
        "state/gmail_suppressions.jsonl",
        "records",
        ("account_id",),
    ),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").casefold())


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned or "campaign"


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} is not a JSON object")
        records.append(value)
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    text = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )
    atomic_write_text(path, text)


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def discover_root(explicit: str | None = None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not (root / "system/defaults.json").is_file():
            raise ValueError(f"Not an SSP Codex project root: {root}")
        return root
    env_root = os.environ.get("SSP_CODEX_ROOT")
    if env_root:
        return discover_root(env_root)
    candidates = [Path.cwd().resolve(), *Path.cwd().resolve().parents]
    script_path = Path(__file__).resolve()
    candidates.extend(script_path.parents)
    for candidate in candidates:
        if (candidate / "system/defaults.json").is_file():
            return candidate
    raise ValueError("Could not locate system/defaults.json")


def safe_campaign_id(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,119}", value):
        raise ValueError(f"Invalid campaign ID: {value!r}")
    return value


def campaign_dir(root: Path, campaign_id: str) -> Path:
    return root / "01_CAMPAIGNS" / safe_campaign_id(campaign_id)


@contextlib.contextmanager
def project_lock(root: Path):
    lock_path = root / ".ssp-outreach.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def event(cdir: Path, event_type: str, **data: Any) -> None:
    append_jsonl(
        cdir / "run/events.jsonl",
        {
            "event_id": stable_id("evt", event_type, now_iso(), len(data)),
            "event_type": event_type,
            "recorded_at": now_iso(),
            **data,
        },
    )


def detect_columns(fieldnames: list[str]) -> dict[str, str | None]:
    normalized = {normalize_header(name): name for name in fieldnames if name}
    mapping: dict[str, str | None] = {}
    for canonical, aliases in HEADER_ALIASES.items():
        mapping[canonical] = next(
            (normalized[alias] for alias in aliases if alias in normalized), None
        )
    return mapping


def parse_pageviews(value: object) -> int | None:
    text = str(value or "").strip().casefold().replace(",", "")
    if not text or text in {"n/a", "na", "null", "none", "-", "unknown"}:
        return None
    multiplier = 1
    if text.endswith("k"):
        multiplier, text = 1_000, text[:-1]
    elif text.endswith("m"):
        multiplier, text = 1_000_000, text[:-1]
    elif text.endswith("b"):
        multiplier, text = 1_000_000_000, text[:-1]
    try:
        parsed = int(float(text) * multiplier)
        return parsed if parsed >= 0 else None
    except ValueError:
        return None


def normalize_geography(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip().casefold())
    return GEOGRAPHY_ALIASES.get(text, text)


def normalize_url(value: object) -> tuple[str, str] | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = text if "://" in text else f"https://{text}"
    parsed = urlparse(candidate)
    hostname = (parsed.hostname or "").casefold().strip(".")
    if not hostname or "." not in hostname or " " in hostname:
        return None
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return candidate, hostname


def natural_brand(hostname: str) -> str:
    first = hostname.split(".")[0]
    return re.sub(r"[-_]+", " ", first).title()


def value_at(row: dict[str | None, Any], field: str | None) -> Any:
    return row.get(field) if field else None


def clean_source_row(row: dict[str | None, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    unnamed_index = 0
    for key, value in row.items():
        if key is None:
            unnamed_index += 1
            cleaned[f"_unnamed_{unnamed_index}"] = value
        else:
            cleaned[key] = value
    return cleaned


def find_existing_campaign(root: Path, source_hash: str, provider: str) -> str | None:
    for state_path in sorted((root / "01_CAMPAIGNS").glob("*/state/campaign.json")):
        try:
            state = read_json(state_path)
        except (OSError, json.JSONDecodeError):
            continue
        if (
            state.get("source", {}).get("sha256") == source_hash
            and str(state.get("target_provider", "")).casefold() == provider.casefold()
        ):
            return str(state["campaign_id"])
    return None


def unique_campaign_id(root: Path, provider: str, label: str | None) -> str:
    date_label = dt.datetime.now().astimezone().date().isoformat()
    base = slug(label) if label else f"tiki-{slug(provider)}-{date_label}"
    candidate = base
    suffix = 2
    while (root / "01_CAMPAIGNS" / candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def bootstrap(args: argparse.Namespace, root: Path) -> int:
    source = Path(args.source).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"Source CSV not found: {source}")
    if source.suffix.casefold() != ".csv":
        raise ValueError("Source input must be a CSV")
    provider = args.provider.strip()
    if not provider:
        raise ValueError("Target provider is required")

    source_bytes = source.read_bytes()
    source_hash = sha256_bytes(source_bytes)
    existing = find_existing_campaign(root, source_hash, provider)
    if existing:
        print(json.dumps({"campaign_id": existing, "resumed": True}, indent=2))
        return 0

    defaults = read_json(root / "system/defaults.json")
    campaign_id = unique_campaign_id(root, provider, args.label)
    cdir = campaign_dir(root, campaign_id)
    for relative in ("source", "state", "reviews", "outputs", "run"):
        (cdir / relative).mkdir(parents=True, exist_ok=False)
    (cdir / "source/original.csv").write_bytes(source_bytes)

    try:
        decoded = source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 or UTF-8 with BOM") from exc
    reader = csv.DictReader(io.StringIO(decoded))
    fieldnames = [name for name in (reader.fieldnames or []) if name]
    if not fieldnames:
        raise ValueError("CSV has no header")
    columns = detect_columns(fieldnames)
    if not columns["url"]:
        raise ValueError(
            "CSV has no usable URL/domain column. Supported names include URL, domain, website, and site."
        )

    threshold = int(defaults["selection"]["minimum_monthly_pageviews"])
    target_geographies = {
        normalize_geography(value)
        for value in defaults["selection"].get("target_geographies", [])
        if normalize_geography(value)
    }
    candidates: list[dict[str, Any]] = []
    invalid_urls = 0
    for row_number, row in enumerate(reader, start=2):
        normalized = normalize_url(value_at(row, columns["url"]))
        if not normalized:
            invalid_urls += 1
            continue
        publisher_url, hostname = normalized
        pageviews = parse_pageviews(value_at(row, columns["pageviews"]))
        country = str(value_at(row, columns["country"]) or "").strip() or None
        normalized_country = normalize_geography(country)
        filter_reason = None
        if pageviews is None:
            status = "unknown_traffic"
            filter_reason = "Monthly traffic is unavailable"
        elif pageviews < threshold:
            status = "below_threshold"
            filter_reason = f"Monthly traffic is below {threshold}"
        elif target_geographies and not normalized_country:
            status = "unknown_geography"
            filter_reason = "Country is unavailable for the configured geography filter"
        elif target_geographies and normalized_country not in target_geographies:
            status = "excluded"
            filter_reason = "Country is outside the configured geography filter"
        else:
            status = "eligible"
        contacts_raw = str(value_at(row, columns["contacts"]) or "")
        contact_tokens = [
            token.strip()
            for token in re.split(r"[|;,]", contacts_raw)
            if token.strip() and token.strip().casefold() not in {"n/a", "na"}
        ]
        publisher_name = str(value_at(row, columns["publisher_name"]) or "").strip()
        candidates.append(
            {
                "campaign_id": campaign_id,
                "candidate_id": stable_id("cand", campaign_id, hostname, row_number),
                "source_row_id": f"row-{row_number}",
                "publisher_url": publisher_url,
                "hostname": hostname,
                "publisher_name": publisher_name or None,
                "input_monthly_pageviews": pageviews,
                "input_category": str(value_at(row, columns["category"]) or "").strip()
                or None,
                "input_country": country,
                "source_provider_signal": str(
                    value_at(row, columns["provider_signal"]) or ""
                ).strip()
                or None,
                "source_contact_tokens": contact_tokens,
                "status": status,
                "filter_reason": filter_reason,
                "source_row": clean_source_row(row),
            }
        )
    if not candidates:
        raise ValueError("CSV contains no usable publisher URL/domain rows")

    counts = {
        "parsed_rows": len(candidates),
        "invalid_url_rows": invalid_urls,
        "eligible": sum(item["status"] == "eligible" for item in candidates),
        "below_threshold": sum(
            item["status"] == "below_threshold" for item in candidates
        ),
        "unknown_traffic": sum(
            item["status"] == "unknown_traffic" for item in candidates
        ),
        "unknown_geography": sum(
            item["status"] == "unknown_geography" for item in candidates
        ),
        "excluded_geography": sum(
            item["status"] == "excluded"
            and item.get("filter_reason")
            == "Country is outside the configured geography filter"
            for item in candidates
        ),
        "unique_hostnames": len({item["hostname"] for item in candidates}),
    }
    write_jsonl(cdir / "state/candidates.jsonl", candidates)
    write_json(
        cdir / "source/intake_audit.json",
        {
            "campaign_id": campaign_id,
            "source_name": source.name,
            "source_size_bytes": len(source_bytes),
            "source_sha256": source_hash,
            "columns": fieldnames,
            "detected_columns": columns,
            "threshold": threshold,
            "counts": counts,
            "audited_at": now_iso(),
        },
    )
    state = {
        "schema_version": 1,
        "campaign_id": campaign_id,
        "target_provider": provider,
        "user_note": args.note or "",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "stage": "source_audited",
        "source": {
            "original_path": str(source),
            "project_path": "source/original.csv",
            "sha256": source_hash,
            "size_bytes": len(source_bytes),
        },
        "defaults_snapshot": defaults,
        "review_gates": {
            "smoke_review": "not_ready",
            "full_review": "not_ready",
        },
        "external_actions": {
            "gmail_drafts": "not_authorized",
            "send_email": False,
            "submit_forms": False,
        },
        "counts": counts,
    }
    write_json(cdir / "state/campaign.json", state)
    event(cdir, "campaign_bootstrapped", campaign_id=campaign_id, counts=counts)
    print(json.dumps({"campaign_id": campaign_id, "resumed": False, **counts}, indent=2))
    return 0


def load_records_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("["):
        value = json.loads(text)
        if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
            raise ValueError("JSON input must be an array of objects")
        return value
    if stripped.startswith("{"):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = None
        if isinstance(value, dict):
            return [value]
    return read_jsonl(path)


def merge_records(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    key_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    order: list[tuple[Any, ...]] = []
    for record in [*existing, *incoming]:
        key = tuple(record.get(field) for field in key_fields)
        if any(value in (None, "") for value in key):
            raise ValueError(f"Missing merge key {key_fields} in record")
        if key not in merged:
            order.append(key)
        merged[key] = record
    return [merged[key] for key in order]


def import_node(args: argparse.Namespace, root: Path) -> int:
    campaign_id = safe_campaign_id(args.campaign)
    cdir = campaign_dir(root, campaign_id)
    state = read_json(cdir / "state/campaign.json")
    if args.node not in NODE_FILES:
        raise ValueError(f"Unsupported node: {args.node}")
    relative, kind, key_fields = NODE_FILES[args.node]
    input_path = Path(args.input).expanduser().resolve()
    records = load_records_file(input_path)
    for record in records:
        if record.get("campaign_id") != campaign_id:
            raise ValueError(
                f"{args.node} record has campaign_id {record.get('campaign_id')!r}; expected {campaign_id!r}"
            )
    destination = cdir / relative
    if kind == "object":
        if len(records) != 1:
            raise ValueError(f"{args.node} requires exactly one object")
        write_json(destination, records[0])
    else:
        existing = [] if args.replace else read_jsonl(destination)
        write_jsonl(destination, merge_records(existing, records, key_fields))
    event(
        cdir,
        "node_imported",
        campaign_id=campaign_id,
        node=args.node,
        imported_count=len(records),
        replace=args.replace,
    )
    state["updated_at"] = now_iso()
    write_json(cdir / "state/campaign.json", state)
    print(json.dumps({"node": args.node, "imported": len(records)}, indent=2))
    return 0


def stage_requirements(cdir: Path, target: str) -> list[str]:
    requirements = {
        "provider_profile_ready": ("state/provider_profile.json",),
        "candidates_classified": ("state/classifications.jsonl",),
        "accounts_consolidated": ("state/accounts.jsonl",),
        "waiting_smoke_review": ("reviews/smoke/review.json",),
        "smoke_approved": ("reviews/smoke/feedback.json",),
        "waiting_full_review": ("reviews/full/review.json",),
        "full_review_approved": ("reviews/full/feedback.json",),
        "actions_complete": ("outputs/action_results.jsonl",),
    }
    return [
        relative
        for relative in requirements.get(target, ())
        if not (cdir / relative).is_file()
    ]


def advance(args: argparse.Namespace, root: Path) -> int:
    campaign_id = safe_campaign_id(args.campaign)
    cdir = campaign_dir(root, campaign_id)
    state_path = cdir / "state/campaign.json"
    state = read_json(state_path)
    current = state["stage"]
    target = args.to
    if target not in STAGE_ORDER and target != "blocked":
        raise ValueError(f"Unknown target stage: {target}")
    if current == target:
        print(json.dumps(state, indent=2))
        return 0
    if current != "blocked":
        current_index = STAGE_ORDER.index(current)
        target_index = STAGE_ORDER.index(target)
        if target_index != current_index + 1:
            raise ValueError(f"Invalid transition {current!r} -> {target!r}")
    missing = stage_requirements(cdir, target)
    if missing:
        raise ValueError(f"Cannot advance to {target}; missing: {', '.join(missing)}")
    errors, _warnings = validate_campaign(root, campaign_id, write_result=False)
    if errors and target not in {"provider_profile_ready", "candidates_classified"}:
        raise ValueError("Cannot advance while campaign validation has errors")
    state["stage"] = target
    state["updated_at"] = now_iso()
    write_json(state_path, state)
    event(cdir, "stage_advanced", campaign_id=campaign_id, from_stage=current, to=target)
    print(json.dumps({"campaign_id": campaign_id, "stage": target}, indent=2))
    return 0


def select_smoke(args: argparse.Namespace, root: Path) -> int:
    campaign_id = safe_campaign_id(args.campaign)
    cdir = campaign_dir(root, campaign_id)
    state = read_json(cdir / "state/campaign.json")
    accounts = read_jsonl(cdir / "state/accounts.jsonl")
    active = [record for record in accounts if record.get("disposition_status") == "active"]
    size = int(state["defaults_snapshot"]["outreach"]["smoke_test_accounts"])
    if len(active) < size:
        raise ValueError(f"Need at least {size} active accounts for the smoke test")
    selected: list[dict[str, Any]] = []
    highest = max(active, key=lambda item: int(item.get("max_monthly_pageviews") or 0))
    selected.append(highest)
    portfolio = next(
        (
            item
            for item in sorted(
                active,
                key=lambda value: len(value.get("portfolio_domains", [])),
                reverse=True,
            )
            if item["account_id"] != highest["account_id"]
            and len(item.get("portfolio_domains", [])) > 1
        ),
        None,
    )
    if portfolio:
        selected.append(portfolio)
    boundary = next(
        (
            item
            for item in sorted(
                active,
                key=lambda value: (
                    value.get("ownership_status") not in {"unresolved", "probable"},
                    int(value.get("max_monthly_pageviews") or 0),
                ),
            )
            if item["account_id"] not in {row["account_id"] for row in selected}
        ),
        None,
    )
    if boundary:
        selected.append(boundary)
    for item in active:
        if len(selected) >= size:
            break
        if item["account_id"] not in {row["account_id"] for row in selected}:
            selected.append(item)
    selected_ids = {row["account_id"] for row in selected[:size]}
    for account in accounts:
        account["smoke_selected"] = account["account_id"] in selected_ids
    write_jsonl(cdir / "state/accounts.jsonl", accounts)
    write_json(
        cdir / "state/smoke_account_ids.json",
        {"campaign_id": campaign_id, "account_ids": sorted(selected_ids)},
    )
    event(cdir, "smoke_selected", campaign_id=campaign_id, account_ids=sorted(selected_ids))
    print(json.dumps({"campaign_id": campaign_id, "account_ids": sorted(selected_ids)}, indent=2))
    return 0


def first_name(name: str | None) -> str | None:
    if not name:
        return None
    token = re.split(r"\s+", name.strip())[0]
    return token if token else None


def build_message(
    provider: str,
    brand: str,
    contact_name: str | None,
    provider_status: str,
    route_type: str,
) -> tuple[str, str, str]:
    greeting = "Hello," if route_type not in {"direct_email", "role_email"} else (
        f"Hi {first_name(contact_name)}," if first_name(contact_name) else "Hello,"
    )
    subject = f"{brand} advertising"
    if provider_status in {"current_signal", "recent_signal"}:
        opening = (
            f"Regarding the on-page advertising on {brand}, is {provider} involved in that setup?"
        )
        branch = "provider_current"
    else:
        opening = (
            f"Regarding the on-page advertising on {brand}, do you manage it directly or does another company handle it?"
        )
        branch = "provider_removed_or_unknown"
    ask = (
        "Is this something you handle, or could you point me to the right person?"
        if route_type in {"direct_email", "role_email"}
        else "Could you point me to the right person?"
    )
    body = (
        f"{greeting}\n\n"
        f"{opening}\n\n"
        "TIKI works directly with tourism boards and global travel brands. "
        f"We would like to discuss two possible ways to share some of that budget with {brand}: "
        "through the advertising setup already in place, or through a separate TIKI format alongside it.\n\n"
        f"{ask}\n\n"
        "Thank you,\n\n"
        "Dean"
    )
    return branch, subject, body


def generate_copy(args: argparse.Namespace, root: Path) -> int:
    campaign_id = safe_campaign_id(args.campaign)
    cdir = campaign_dir(root, campaign_id)
    state = read_json(cdir / "state/campaign.json")
    provider = state["target_provider"]
    accounts = read_jsonl(cdir / "state/accounts.jsonl")
    research = {
        record["account_id"]: record
        for record in read_jsonl(cdir / "state/research.jsonl")
    }
    selected_ids: set[str] | None = None
    if args.stage == "smoke":
        selected_ids = set(read_json(cdir / "state/smoke_account_ids.json")["account_ids"])
    rows: list[dict[str, Any]] = []
    for account in accounts:
        account_id = account["account_id"]
        if selected_ids is not None and account_id not in selected_ids:
            continue
        result = research.get(account_id)
        publisher_name = account["publisher_name"]
        publisher_brand = account.get("publisher_brand") or natural_brand(
            account["canonical_domain"]
        )
        copy_record_id = stable_id(
            "copy", campaign_id, account_id, args.stage
        )
        base = {
            "campaign_id": campaign_id,
            "account_id": account_id,
            "publisher_name": publisher_name,
            "publisher_brand": publisher_brand,
            "publisher_url": account.get("publisher_url")
            or f"https://{account['canonical_domain']}",
            "parent_company": account.get("parent_company"),
            "portfolio_domains": account.get("portfolio_domains", []),
            "contact_name": result.get("contact_name") if result else None,
            "contact_email": result.get("contact_email") if result else None,
            "route_type": result.get("route_type", "none") if result else "none",
            "route_url": result.get("route_url") if result else None,
            "provider_status": result.get("provider_status", "unknown")
            if result
            else "unknown",
            "provider_evidence_url": result.get("provider_evidence_url")
            if result
            else None,
            "evidence_urls": result.get("evidence_urls", []) if result else [],
            "evidence_summary": result.get("provider_evidence", "") if result else "",
            "gaps": result.get("research_gaps", ["No research result"]) if result else ["No research result"],
            "copy_record_id": copy_record_id,
            "copy_format": "plain_text_paragraphs",
            "gmail_history_status": "not_checked"
            if args.stage == "full"
            else "not_applicable",
            "review_stage": args.stage,
        }
        actionable = (
            account.get("disposition_status") == "active"
            and result is not None
            and result.get("completion_status") == "completed"
            and result.get("route_status") == "actionable"
        )
        if actionable:
            route_type = result["route_type"]
            copy_branch, subject, body = build_message(
                provider,
                publisher_brand,
                result.get("contact_name"),
                result.get("provider_status", "unknown"),
                route_type,
            )
            proposed_action = (
                "create_gmail_draft"
                if route_type in {"direct_email", "role_email"}
                else "queue_manual_route"
            )
            workflow_status = "actionable"
            status_reason = None
        else:
            copy_branch, subject, body = "none", "", ""
            proposed_action = "none"
            workflow_status = (
                account.get("disposition_status")
                if account.get("disposition_status") in {"excluded", "held", "failed"}
                else "held"
            )
            status_reason = account.get("disposition_reason") or (
                "No current actionable public commercial route"
            )
        rows.append(
            {
                **base,
                "copy_branch": copy_branch,
                "subject": subject,
                "body": body,
                "proposed_action": proposed_action,
                "workflow_status": workflow_status,
                "status_reason": status_reason,
            }
        )
    existing = read_jsonl(cdir / "state/outreach.jsonl")
    merged = merge_records(existing, rows, ("account_id", "review_stage"))
    write_jsonl(cdir / "state/outreach.jsonl", merged)
    event(
        cdir,
        "copy_generated",
        campaign_id=campaign_id,
        review_stage=args.stage,
        count=len(rows),
    )
    print(json.dumps({"campaign_id": campaign_id, "stage": args.stage, "count": len(rows)}, indent=2))
    return 0


def apply_suppressions(args: argparse.Namespace, root: Path) -> int:
    campaign_id = safe_campaign_id(args.campaign)
    cdir = campaign_dir(root, campaign_id)
    suppressions = {
        item["account_id"]: item
        for item in read_jsonl(cdir / "state/gmail_suppressions.jsonl")
    }
    rows = read_jsonl(cdir / "state/outreach.jsonl")
    updated = 0
    for row in rows:
        if row.get("review_stage") != "full":
            continue
        if row.get("proposed_action") != "create_gmail_draft":
            row["gmail_history_status"] = "not_applicable"
            continue
        result = suppressions.get(row["account_id"])
        if not result:
            row["gmail_history_status"] = "not_checked"
            continue
        row["gmail_history_status"] = result["status"]
        if result["status"] != "clear":
            row["workflow_status"] = "held"
            row["proposed_action"] = "none"
            row["status_reason"] = result.get("reason") or "Suppressed by Gmail history"
        updated += 1
    write_jsonl(cdir / "state/outreach.jsonl", rows)
    event(cdir, "gmail_suppressions_applied", campaign_id=campaign_id, count=updated)
    print(json.dumps({"campaign_id": campaign_id, "updated": updated}, indent=2))
    return 0


def word_count(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value))


def validate_campaign(
    root: Path, campaign_id: str, write_result: bool = True
) -> tuple[list[str], list[str]]:
    cdir = campaign_dir(root, campaign_id)
    errors: list[str] = []
    warnings: list[str] = []
    state_path = cdir / "state/campaign.json"
    if not state_path.is_file():
        return ["Missing state/campaign.json"], warnings
    state = read_json(state_path)
    if state.get("campaign_id") != campaign_id:
        errors.append("Campaign state ID does not match folder")
    if state.get("external_actions", {}).get("send_email") is not False:
        errors.append("send_email safeguard must remain false")
    if state.get("external_actions", {}).get("submit_forms") is not False:
        errors.append("submit_forms safeguard must remain false")

    candidates = read_jsonl(cdir / "state/candidates.jsonl")
    candidate_ids = [item.get("candidate_id") for item in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        errors.append("Duplicate candidate IDs")
    for relative in (
        "state/candidates.jsonl",
        "state/classifications.jsonl",
        "state/accounts.jsonl",
        "state/research.jsonl",
        "state/outreach.jsonl",
        "state/gmail_suppressions.jsonl",
    ):
        for line, record in enumerate(read_jsonl(cdir / relative), 1):
            if record.get("campaign_id") != campaign_id:
                errors.append(f"{relative}:{line} has the wrong campaign_id")

    classifications = read_jsonl(cdir / "state/classifications.jsonl")
    eligible_ids = {item["candidate_id"] for item in candidates if item["status"] == "eligible"}
    classified_ids = {item.get("candidate_id") for item in classifications}
    if classifications and eligible_ids != classified_ids:
        missing = eligible_ids - classified_ids
        extra = classified_ids - eligible_ids
        if missing:
            errors.append(f"{len(missing)} eligible candidates lack classification")
        if extra:
            errors.append(f"{len(extra)} classifications do not map to eligible candidates")

    accounts = read_jsonl(cdir / "state/accounts.jsonl")
    account_ids = [item.get("account_id") for item in accounts]
    if len(account_ids) != len(set(account_ids)):
        errors.append("Duplicate canonical account IDs")
    for account in accounts:
        brand = str(account.get("publisher_brand") or "").strip()
        if not brand:
            errors.append(
                f"{account.get('account_id')} lacks a natural publisher_brand"
            )
        elif re.search(r"https?://|www\.|/|@[a-z0-9.-]+", brand, re.I):
            errors.append(
                f"{account.get('account_id')} publisher_brand contains URL components"
            )
    configured_verticals = set(
        state.get("defaults_snapshot", {})
        .get("selection", {})
        .get("target_verticals", [])
    )
    retained_candidate_ids = {
        item["candidate_id"]
        for item in classifications
        if item.get("classification") in configured_verticals | {"unresolved"}
        and item.get("completion_status") != "excluded"
    }
    mapped_candidate_ids = {
        candidate_id
        for account in accounts
        for candidate_id in account.get("candidate_ids", [])
    }
    if accounts and retained_candidate_ids - mapped_candidate_ids:
        errors.append(
            f"{len(retained_candidate_ids - mapped_candidate_ids)} retained candidates lack a canonical account"
        )

    outreach = read_jsonl(cdir / "state/outreach.jsonl")
    seen_outreach: set[tuple[str, str]] = set()
    minimum = int(state.get("defaults_snapshot", {}).get("outreach", {}).get("word_count_min", 60))
    maximum = int(state.get("defaults_snapshot", {}).get("outreach", {}).get("word_count_max", 120))
    for row in outreach:
        key = (str(row.get("account_id")), str(row.get("review_stage")))
        if key in seen_outreach:
            errors.append(f"Duplicate outreach row {key}")
        seen_outreach.add(key)
        if row.get("workflow_status") != "actionable":
            continue
        brand = str(row.get("publisher_brand") or "").strip()
        if not brand:
            errors.append(f"{row.get('account_id')} outreach lacks publisher_brand")
        if not row.get("copy_record_id"):
            errors.append(f"{row.get('account_id')} outreach lacks copy_record_id")
        if row.get("copy_format") != "plain_text_paragraphs":
            errors.append(
                f"{row.get('account_id')} copy_format must be plain_text_paragraphs"
            )
        body = str(row.get("body") or "")
        if "\r" in body or "\n\n" not in body:
            errors.append(
                f"{row.get('account_id')} body must preserve plain-text paragraph breaks"
            )
        count = word_count(body)
        if not minimum <= count <= maximum:
            errors.append(
                f"{row.get('account_id')} body has {count} words; expected {minimum}-{maximum}"
            )
        lowered = body.casefold()
        for term in PROHIBITED_COLD_COPY:
            if re.search(rf"\b{re.escape(term)}\b", lowered, re.I):
                errors.append(f"{row.get('account_id')} body contains prohibited term {term!r}")
        if body.count("?") > 2:
            errors.append(f"{row.get('account_id')} body contains more than two questions")
        if re.search(r"https?://|www\.", str(row.get("subject") or ""), re.I):
            errors.append(f"{row.get('account_id')} subject contains a URL")
        if row.get("proposed_action") == "create_gmail_draft":
            if not row.get("contact_email"):
                errors.append(f"{row.get('account_id')} email action lacks contact_email")
            if row.get("review_stage") == "full" and row.get("gmail_history_status") != "clear":
                errors.append(
                    f"{row.get('account_id')} full email action lacks clear Gmail history"
                )
        if row.get("proposed_action") == "queue_manual_route" and not row.get("route_url"):
            errors.append(f"{row.get('account_id')} manual action lacks route_url")

    canonical_copy = {
        row.get("copy_record_id"): row
        for row in outreach
        if row.get("copy_record_id")
    }
    for derived_path, body_field in (
        (cdir / "outputs/draft_intents.jsonl", "body"),
        (cdir / "outputs/manual_actions.jsonl", "message"),
    ):
        for derived in read_jsonl(derived_path):
            source = canonical_copy.get(derived.get("copy_record_id"))
            if not source:
                errors.append(
                    f"{derived.get('action_id')} lacks a canonical copy record"
                )
                continue
            if (
                derived.get("publisher_brand") != source.get("publisher_brand")
                or derived.get("subject") != source.get("subject")
                or derived.get(body_field) != source.get("body")
            ):
                errors.append(
                    f"{derived.get('action_id')} drifted from canonical copy "
                    f"{derived.get('copy_record_id')}"
                )

    smoke_rows = [row for row in outreach if row.get("review_stage") == "smoke"]
    if smoke_rows and len(smoke_rows) != 3:
        errors.append(f"Smoke review requires exactly 3 rows; found {len(smoke_rows)}")
    full_rows = [row for row in outreach if row.get("review_stage") == "full"]
    if full_rows and accounts and {row["account_id"] for row in full_rows} != set(account_ids):
        errors.append("Full review does not represent every canonical account")

    result = {
        "campaign_id": campaign_id,
        "stage": state.get("stage"),
        "passed": not errors,
        "expected_count": len(accounts) if accounts else len(eligible_ids),
        "accounted_count": len(full_rows) if full_rows else len(accounts),
        "errors": errors,
        "warnings": warnings,
        "validated_at": now_iso(),
    }
    if write_result:
        write_json(cdir / "run/last_validation.json", result)
    return errors, warnings


def safe_link(url: str | None) -> bool:
    if not url:
        return False
    return urlparse(url).scheme.casefold() in {"http", "https", "mailto"}


def build_review_item(
    row: dict[str, Any],
    account: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    stage: str,
) -> dict[str, Any]:
    links = []
    if safe_link(row.get("provider_evidence_url")):
        links.append(
            {"label": "Provider evidence", "url": row["provider_evidence_url"], "kind": "evidence"}
        )
    for index, url in enumerate(row.get("evidence_urls", []), 1):
        if safe_link(url) and url != row.get("provider_evidence_url"):
            links.append({"label": f"Evidence {index}", "url": url, "kind": "evidence"})
    if safe_link(row.get("route_url")):
        links.append({"label": "Contact route", "url": row["route_url"], "kind": "form"})
    if row.get("contact_email"):
        links.append(
            {
                "label": "Email recipient",
                "url": f"mailto:{row['contact_email']}",
                "kind": "contact",
            }
        )
    actionable = row.get("workflow_status") == "actionable"
    action_labels = {
        "create_gmail_draft": "Create the exact displayed Gmail draft",
        "queue_manual_route": "Add to the manual follow-up list",
        "none": "No external or manual action",
    }
    account_candidates = [
        candidates[candidate_id]
        for candidate_id in account.get("candidate_ids", [])
        if candidate_id in candidates
    ]
    primary_candidate = next(
        (
            candidate
            for candidate in account_candidates
            if candidate.get("hostname") == account.get("canonical_domain")
        ),
        account_candidates[0] if account_candidates else {},
    )
    site_traffic = primary_candidate.get("input_monthly_pageviews")
    verified_group = (
        account.get("ownership_status") == "verified"
        and len(account.get("portfolio_domains", [])) > 1
    )
    group_values = [
        candidate.get("input_monthly_pageviews") for candidate in account_candidates
    ]
    data = {
        "Account ID": row["account_id"],
        "Publisher brand": row.get("publisher_brand") or row["publisher_name"],
        "Site traffic estimate": (
            f"{site_traffic:,} estimated monthly pageviews"
            if isinstance(site_traffic, int)
            else "Unknown"
        ),
        **(
            {
                "Group traffic estimate": (
                    f"{sum(group_values):,} estimated monthly pageviews"
                    if group_values and all(isinstance(value, int) for value in group_values)
                    else "Incomplete source estimates"
                )
            }
            if verified_group
            else {}
        ),
        "Owner": row.get("parent_company") or "Not separately verified",
        "Portfolio": " | ".join(row.get("portfolio_domains", [])) or "None recorded",
        "Provider status": row.get("provider_status") or "unknown",
        "Contact": row.get("contact_name") or "Team route",
        "Recipient": row.get("contact_email") or row.get("route_url") or "None",
        "Gmail history": row.get("gmail_history_status") or "not checked",
        "Proposed action": action_labels.get(row.get("proposed_action"), "No action"),
    }
    if actionable:
        data["Copy record"] = row.get("copy_record_id") or ""
        data["Subject"] = row.get("subject") or ""
        data["Email or form copy"] = row.get("body") or ""
    details = row.get("evidence_summary") or "No compact evidence summary recorded."
    gaps = row.get("gaps", [])
    if gaps:
        details += "\n\nGaps: " + " | ".join(str(gap) for gap in gaps)
    summary = (
        f"{action_labels.get(row.get('proposed_action'), 'Review the proposed action')}. "
        f"Provider signal: {row.get('provider_status', 'unknown')}."
        if actionable
        else row.get("status_reason") or "No actionable route is proposed."
    )
    badges = [
        row.get("route_type", "none"),
        row.get("provider_status", "unknown"),
        row.get("workflow_status", "unknown"),
    ]
    return {
        "id": row["account_id"],
        "title": row.get("publisher_brand") or row["publisher_name"],
        "summary": summary,
        "details": details,
        "category": row.get("route_type") or "none",
        "priority": "P1" if actionable else "P3",
        "severity": "action" if actionable else ("warn" if row.get("workflow_status") == "failed" else "info"),
        "status": row.get("workflow_status") or "unknown",
        "recommended_action": action_labels.get(row.get("proposed_action"), "No action"),
        "website": {
            "label": row.get("publisher_brand") or row["publisher_name"],
            "url": row["publisher_url"],
        },
        "links": links,
        "data": data,
        "badges": badges,
        "fields": [
            {
                "id": "review-note",
                "label": "Specific change or context",
                "type": "textarea",
                "placeholder": "Optional note for Codex",
            }
        ],
    }


def build_review(args: argparse.Namespace, root: Path) -> int:
    campaign_id = safe_campaign_id(args.campaign)
    cdir = campaign_dir(root, campaign_id)
    errors, warnings = validate_campaign(root, campaign_id)
    if errors:
        raise ValueError("Campaign validation failed: " + "; ".join(errors))
    state = read_json(cdir / "state/campaign.json")
    accounts = {row["account_id"]: row for row in read_jsonl(cdir / "state/accounts.jsonl")}
    candidates = {
        row["candidate_id"]: row for row in read_jsonl(cdir / "state/candidates.jsonl")
    }
    rows = [
        row
        for row in read_jsonl(cdir / "state/outreach.jsonl")
        if row.get("review_stage") == args.stage
    ]
    if args.stage == "smoke" and len(rows) != 3:
        raise ValueError(f"Smoke review requires exactly 3 items; found {len(rows)}")
    if args.stage == "full" and set(accounts) != {row["account_id"] for row in rows}:
        raise ValueError("Full review must include every canonical account")
    review_id = f"{campaign_id}-{args.stage}-review"
    actionable = sum(row.get("workflow_status") == "actionable" for row in rows)
    failed = sum(row.get("workflow_status") == "failed" for row in rows)
    excluded = sum(row.get("workflow_status") == "excluded" for row in rows)
    if args.stage == "smoke":
        title = f"{state['target_provider']} three-publisher calibration"
        scope = (
            "Approve direction authorizes Codex to freeze the campaign research and copy rules "
            "and continue automatically to the full queue. It authorizes no Gmail or manual-route action."
        )
        approve_label = "Approve direction"
        tagline = "Check evidence, route safety, tone, claim strength, and the ask."
    else:
        title = f"{state['target_provider']} complete outreach and action review"
        scope = (
            "Approve shown action authorizes creation of the exact displayed Gmail draft for an email route, "
            "or addition of the displayed non-email route to the local manual follow-up list. "
            "Nothing is sent, scheduled, submitted, posted, or called."
        )
        approve_label = "Approve shown action"
        tagline = "Review every account, exact recipient or route, final copy, Gmail history, and proposed action."
    review = {
        "review_id": review_id,
        "title": title,
        "eyebrow": f"TIKI · {state['target_provider'].upper()} · {args.stage.upper()}",
        "tagline": tagline,
        "scope_note": scope,
        "generated_at": now_iso(),
        "metrics": [
            {"label": "Accounts", "value": len(rows), "detail": "Every item in this review"},
            {"label": "Actionable", "value": actionable, "detail": "Exact proposed actions"},
            {"label": "Excluded", "value": excluded, "detail": "Retained for audit"},
            {"label": "Failed", "value": failed, "detail": "Explicitly visible"},
        ],
        "decision_options": [
            {"value": "approved", "label": approve_label, "tone": "positive"},
            {"value": "needs_changes", "label": "Needs changes", "tone": "warning"},
            {"value": "hold", "label": "Hold", "tone": "neutral"},
            {"value": "excluded", "label": "Exclude", "tone": "negative"},
        ],
        "items": [
            build_review_item(
                row,
                accounts.get(row["account_id"], {}),
                candidates,
                args.stage,
            )
            for row in sorted(rows, key=lambda item: (item.get("workflow_status") != "actionable", item["publisher_name"]))
        ],
    }
    campaign_review_dir = cdir / "reviews" / args.stage
    public_review_dir = root / "02_REVIEW" / campaign_id / args.stage
    write_json(campaign_review_dir / "review.json", review)
    write_json(public_review_dir / "review.json", review)
    state["stage"] = f"waiting_{args.stage}_review"
    state["review_gates"][f"{args.stage}_review"] = "waiting"
    state["updated_at"] = now_iso()
    write_json(cdir / "state/campaign.json", state)
    event(cdir, "review_built", campaign_id=campaign_id, review_stage=args.stage, count=len(rows))
    print(
        json.dumps(
            {
                "campaign_id": campaign_id,
                "stage": args.stage,
                "review": str(public_review_dir / "review.json"),
                "feedback": str(public_review_dir / "feedback.json"),
                "warnings": warnings,
            },
            indent=2,
        )
    )
    return 0


def apply_feedback(args: argparse.Namespace, root: Path) -> int:
    campaign_id = safe_campaign_id(args.campaign)
    cdir = campaign_dir(root, campaign_id)
    feedback_path = Path(args.feedback).expanduser().resolve()
    feedback = read_json(feedback_path)
    expected_review_id = f"{campaign_id}-{args.stage}-review"
    if feedback.get("review_id") != expected_review_id:
        raise ValueError(
            f"Feedback review_id {feedback.get('review_id')!r} does not match {expected_review_id!r}"
        )
    if feedback.get("status") != "submitted":
        raise ValueError("VisualizeMe feedback has not been submitted")
    review = read_json(cdir / "reviews" / args.stage / "review.json")
    outreach_records = read_jsonl(cdir / "state/outreach.jsonl")
    rows = {
        (row["account_id"], row["review_stage"]): row
        for row in outreach_records
    }
    accounts = read_jsonl(cdir / "state/accounts.jsonl")
    account_by_id = {row["account_id"]: row for row in accounts}
    decisions = {item["id"]: item for item in feedback.get("items", [])}
    approvals: list[dict[str, Any]] = []
    unresolved: list[str] = []
    draft_intents: list[dict[str, Any]] = []
    manual_actions: list[dict[str, Any]] = []
    action_results: list[dict[str, Any]] = []
    for item in review["items"]:
        account_id = item["id"]
        response = decisions.get(account_id, {"decision": "pending", "comment": ""})
        decision = response.get("decision", "pending")
        if decision in {"pending", "needs_changes"}:
            unresolved.append(account_id)
        outreach = rows[(account_id, args.stage)]
        comment = response.get("comment") or response.get("fields", {}).get(
            "review-note", ""
        )
        if decision in {"hold", "excluded"}:
            disposition = "held" if decision == "hold" else "excluded"
            reason = comment or f"User marked this item {disposition} in {args.stage} review"
            outreach["workflow_status"] = disposition
            outreach["proposed_action"] = "none"
            outreach["status_reason"] = reason
            account = account_by_id.get(account_id)
            if account:
                account["disposition_status"] = disposition
                account["disposition_reason"] = reason
        authorized_action = "none"
        if args.stage == "full" and decision == "approved" and outreach.get("workflow_status") == "actionable":
            if (
                outreach.get("proposed_action") == "create_gmail_draft"
                and outreach.get("gmail_history_status") == "clear"
            ):
                authorized_action = "create_gmail_draft"
            elif outreach.get("proposed_action") == "queue_manual_route":
                authorized_action = "queue_manual_route"
        approval_id = stable_id(
            "approval", campaign_id, args.stage, account_id, feedback.get("submitted_at", now_iso())
        )
        approval = {
            "approval_id": approval_id,
            "campaign_id": campaign_id,
            "review_stage": args.stage,
            "account_id": account_id,
            "decision": decision,
            "authorized_action": authorized_action,
            "comment": comment,
            "review_id": expected_review_id,
            "recorded_at": feedback.get("submitted_at") or now_iso(),
        }
        approvals.append(approval)
        if authorized_action == "create_gmail_draft":
            draft_intents.append(
                {
                    "action_id": stable_id("action", campaign_id, account_id, "gmail_draft"),
                    "campaign_id": campaign_id,
                    "account_id": account_id,
                    "approval_id": approval_id,
                    "copy_record_id": outreach["copy_record_id"],
                    "publisher_brand": outreach["publisher_brand"],
                    "recipient": outreach["contact_email"],
                    "subject": outreach["subject"],
                    "body": outreach["body"],
                    "status": "authorized",
                }
            )
        elif authorized_action == "queue_manual_route":
            action_id = stable_id("action", campaign_id, account_id, "manual_route")
            queued_at = now_iso()
            manual_actions.append(
                {
                    "action_id": action_id,
                    "campaign_id": campaign_id,
                    "account_id": account_id,
                    "approval_id": approval_id,
                    "copy_record_id": outreach["copy_record_id"],
                    "publisher_brand": outreach["publisher_brand"],
                    "route_type": outreach["route_type"],
                    "route_url": outreach["route_url"],
                    "subject": outreach["subject"],
                    "message": outreach["body"],
                    "message_format": "plain_text_paragraphs",
                    "status": "queued",
                    "queued_at": queued_at,
                    "updated_at": queued_at,
                    "completed_at": None,
                    "hold_reason": None,
                }
            )
            action_results.append(
                {
                    "action_id": action_id,
                    "campaign_id": campaign_id,
                    "account_id": account_id,
                    "action_type": "manual_route",
                    "status": "queued",
                    "authorized_by_approval_id": approval_id,
                    "external_id": None,
                    "external_url": outreach["route_url"],
                    "hold_reason": None,
                    "completed_at": None,
                    "error": None,
                    "updated_at": now_iso(),
                }
            )
    write_jsonl(cdir / f"reviews/{args.stage}/approvals.jsonl", approvals)
    write_jsonl(cdir / "state/accounts.jsonl", accounts)
    write_jsonl(cdir / "state/outreach.jsonl", outreach_records)
    shutil.copy2(feedback_path, cdir / f"reviews/{args.stage}/feedback.json")
    state = read_json(cdir / "state/campaign.json")
    if unresolved:
        state["review_gates"][f"{args.stage}_review"] = "changes_requested"
        state["stage"] = f"waiting_{args.stage}_review"
        if args.stage == "full":
            draft_intents = []
            manual_actions = []
            action_results = []
    else:
        state["review_gates"][f"{args.stage}_review"] = "approved"
        state["stage"] = (
            "full_review_approved" if args.stage == "full" else "smoke_approved"
        )
    if args.stage == "full":
        write_jsonl(cdir / "outputs/draft_intents.jsonl", draft_intents)
        write_jsonl(cdir / "outputs/manual_actions.jsonl", manual_actions)
        write_jsonl(cdir / "outputs/action_results.jsonl", action_results)
        state["external_actions"]["gmail_drafts"] = (
            "item_review_required" if draft_intents else "complete"
        )
    state["updated_at"] = now_iso()
    write_json(cdir / "state/campaign.json", state)
    event(
        cdir,
        "feedback_applied",
        campaign_id=campaign_id,
        review_stage=args.stage,
        unresolved=len(unresolved),
        draft_intents=len(draft_intents),
        manual_actions=len(manual_actions),
    )
    print(
        json.dumps(
            {
                "campaign_id": campaign_id,
                "stage": args.stage,
                "unresolved": unresolved,
                "draft_intents": len(draft_intents),
                "manual_actions": len(manual_actions),
            },
            indent=2,
        )
    )
    return 0


def record_action(args: argparse.Namespace, root: Path) -> int:
    campaign_id = safe_campaign_id(args.campaign)
    cdir = campaign_dir(root, campaign_id)
    intents = {
        item["account_id"]: item for item in read_jsonl(cdir / "outputs/draft_intents.jsonl")
    }
    intent = intents.get(args.account)
    if not intent:
        raise ValueError("No authorized Gmail draft intent exists for this account")
    results = read_jsonl(cdir / "outputs/action_results.jsonl")
    result = {
        "action_id": intent["action_id"],
        "campaign_id": campaign_id,
        "account_id": args.account,
        "action_type": "gmail_draft",
        "status": args.status,
        "authorized_by_approval_id": intent["approval_id"],
        "external_id": args.external_id,
        "external_url": args.external_url,
        "error": args.error,
        "updated_at": now_iso(),
    }
    write_jsonl(
        cdir / "outputs/action_results.jsonl",
        merge_records(results, [result], ("action_id",)),
    )
    reconcile_state(root, campaign_id)
    event(cdir, "action_recorded", campaign_id=campaign_id, account_id=args.account, status=args.status)
    print(json.dumps(result, indent=2))
    return 0


def reconcile_state(root: Path, campaign_id: str) -> dict[str, Any]:
    cdir = campaign_dir(root, campaign_id)
    state = read_json(cdir / "state/campaign.json")
    intents = read_jsonl(cdir / "outputs/draft_intents.jsonl")
    results = read_jsonl(cdir / "outputs/action_results.jsonl")
    result_ids = {item["action_id"] for item in results}
    pending = [item for item in intents if item["action_id"] not in result_ids]
    if intents and pending:
        state["external_actions"]["gmail_drafts"] = "partially_complete"
    else:
        state["external_actions"]["gmail_drafts"] = "complete"
        if state["review_gates"]["full_review"] == "approved":
            state["stage"] = "actions_complete"
    state["updated_at"] = now_iso()
    write_json(cdir / "state/campaign.json", state)
    return {"pending_drafts": len(pending), "stage": state["stage"]}


def reconcile(args: argparse.Namespace, root: Path) -> int:
    result = reconcile_state(root, safe_campaign_id(args.campaign))
    print(json.dumps(result, indent=2))
    return 0


def status(args: argparse.Namespace, root: Path) -> int:
    if args.campaign:
        state = read_json(campaign_dir(root, args.campaign) / "state/campaign.json")
        print(json.dumps(state, indent=2))
        return 0
    states = []
    for path in sorted((root / "01_CAMPAIGNS").glob("*/state/campaign.json")):
        states.append(read_json(path))
    print(json.dumps(states, indent=2))
    return 0


def validate_command(args: argparse.Namespace, root: Path) -> int:
    errors, warnings = validate_campaign(root, safe_campaign_id(args.campaign))
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS: 0 errors, {len(warnings)} warning(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Override the Codex SSP project root")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser("bootstrap")
    bootstrap_parser.add_argument("--source", required=True)
    bootstrap_parser.add_argument("--provider", required=True)
    bootstrap_parser.add_argument("--note", default="")
    bootstrap_parser.add_argument("--label")
    bootstrap_parser.set_defaults(handler=bootstrap, mutates=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--campaign")
    status_parser.set_defaults(handler=status, mutates=False)

    import_parser = subparsers.add_parser("import-node")
    import_parser.add_argument("--campaign", required=True)
    import_parser.add_argument("--node", choices=sorted(NODE_FILES), required=True)
    import_parser.add_argument("--input", required=True)
    import_parser.add_argument("--replace", action="store_true")
    import_parser.set_defaults(handler=import_node, mutates=True)

    advance_parser = subparsers.add_parser("advance")
    advance_parser.add_argument("--campaign", required=True)
    advance_parser.add_argument("--to", required=True)
    advance_parser.set_defaults(handler=advance, mutates=True)

    smoke_parser = subparsers.add_parser("select-smoke")
    smoke_parser.add_argument("--campaign", required=True)
    smoke_parser.set_defaults(handler=select_smoke, mutates=True)

    copy_parser = subparsers.add_parser("generate-copy")
    copy_parser.add_argument("--campaign", required=True)
    copy_parser.add_argument("--stage", choices=("smoke", "full"), required=True)
    copy_parser.set_defaults(handler=generate_copy, mutates=True)

    suppression_parser = subparsers.add_parser("apply-suppressions")
    suppression_parser.add_argument("--campaign", required=True)
    suppression_parser.set_defaults(handler=apply_suppressions, mutates=True)

    review_parser = subparsers.add_parser("build-review")
    review_parser.add_argument("--campaign", required=True)
    review_parser.add_argument("--stage", choices=("smoke", "full"), required=True)
    review_parser.set_defaults(handler=build_review, mutates=True)

    feedback_parser = subparsers.add_parser("apply-feedback")
    feedback_parser.add_argument("--campaign", required=True)
    feedback_parser.add_argument("--stage", choices=("smoke", "full"), required=True)
    feedback_parser.add_argument("--feedback", required=True)
    feedback_parser.set_defaults(handler=apply_feedback, mutates=True)

    action_parser = subparsers.add_parser("record-action")
    action_parser.add_argument("--campaign", required=True)
    action_parser.add_argument("--account", required=True)
    action_parser.add_argument("--status", choices=("created", "failed", "suppressed"), required=True)
    action_parser.add_argument("--external-id")
    action_parser.add_argument("--external-url")
    action_parser.add_argument("--error")
    action_parser.set_defaults(handler=record_action, mutates=True)

    reconcile_parser = subparsers.add_parser("reconcile")
    reconcile_parser.add_argument("--campaign", required=True)
    reconcile_parser.set_defaults(handler=reconcile, mutates=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--campaign", required=True)
    validate_parser.set_defaults(handler=validate_command, mutates=False)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        root = discover_root(args.root)
        if args.mutates:
            with project_lock(root):
                return int(args.handler(args, root))
        return int(args.handler(args, root))
    except (OSError, ValueError, json.JSONDecodeError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
