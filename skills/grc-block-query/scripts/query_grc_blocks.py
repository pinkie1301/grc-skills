#!/usr/bin/env python3
"""Query GNU Radio GRC block field data with strict source order.

Query order:
1) local-db
2) radioconda
3) gnuradio-github
4) gnuradio-wiki
5) ettus
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

QUERY_ORDER = [
    "local-db",
    "radioconda",
    "gnuradio-github",
    "gnuradio-wiki",
    "ettus",
]

ALLOWED_SOURCE_IDS = set(QUERY_ORDER)
ALLOWED_STATUSES = {"verified", "pending", "conflict"}
ALLOWED_URL_PREFIXES = (
    "https://api.github.com/repos/gnuradio/gnuradio/",
    "https://api.github.com/search/code",
    "https://github.com/gnuradio/gnuradio",
    "https://wiki.gnuradio.org/",
    "https://www.ettus.com/",
)

DEFAULT_SHARED_ROOT = (pathlib.Path.home() / "Documents" / "grc-block-query").expanduser().resolve()
DEFAULT_DB_ROOT = (DEFAULT_SHARED_ROOT / "db").resolve()
DEFAULT_RADIOCONDA = pathlib.Path(
    os.environ.get("GRC_RADIOCONDA_PATH") or pathlib.Path.home() / "radioconda" / "Library" / "share" / "gnuradio"
).expanduser()


class QueryError(RuntimeError):
    """Error raised for invalid query operations."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def infer_value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, (dict, list)):
        return "json"
    return "string"


def block_file_path(db_root: pathlib.Path, block_name: str) -> pathlib.Path:
    return db_root / "blocks" / f"{canonical_id(block_name)}.json"


def read_json_file(path: pathlib.Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json_file(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def append_audit_log(db_root: pathlib.Path, record: dict[str, Any]) -> None:
    audit_path = db_root / "audit-log.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def path_to_posix(path: pathlib.Path) -> str:
    return path.expanduser().resolve().as_posix()


def initialize_db_root(db_root: pathlib.Path, radioconda_path: pathlib.Path) -> None:
    # First-run bootstrap: enforce shared root and create minimum DB layout.
    DEFAULT_SHARED_ROOT.mkdir(parents=True, exist_ok=True)

    db_root.mkdir(parents=True, exist_ok=True)
    (db_root / "blocks").mkdir(parents=True, exist_ok=True)
    (db_root / "conflicts").mkdir(parents=True, exist_ok=True)
    (db_root / "sources").mkdir(parents=True, exist_ok=True)

    index_path = db_root / "index.json"
    if not index_path.exists():
        write_json_file(
            index_path,
            {
                "version": "0.1.0",
                "query_order": QUERY_ORDER,
                "last_updated": None,
                "blocks": {},
            },
        )

    manifest_path = db_root / "sources" / "sources-manifest.json"
    if not manifest_path.exists():
        write_json_file(
            manifest_path,
            {
                "version": "0.1.0",
                "allowed_sources": [
                    {
                        "id": "local-db",
                        "kind": "workspace",
                        "location": path_to_posix(db_root / "blocks"),
                    },
                    {
                        "id": "radioconda",
                        "kind": "local-path",
                        "location": path_to_posix(radioconda_path),
                    },
                    {
                        "id": "gnuradio-github",
                        "kind": "web",
                        "location": "https://github.com/gnuradio/gnuradio",
                    },
                    {
                        "id": "gnuradio-wiki",
                        "kind": "web",
                        "location": "https://wiki.gnuradio.org/",
                    },
                    {
                        "id": "ettus",
                        "kind": "web",
                        "location": "https://www.ettus.com/",
                    },
                ],
                "query_order": QUERY_ORDER,
            },
        )

    audit_path = db_root / "audit-log.jsonl"
    if not audit_path.exists():
        audit_path.touch()

    init_info_path = db_root / "init-info.json"
    if not init_info_path.exists():
        write_json_file(
            init_info_path,
            {
                "version": "0.1.0",
                "initialized_at": utc_now(),
                "shared_root": path_to_posix(DEFAULT_SHARED_ROOT),
                "db_root": path_to_posix(db_root),
            },
        )


def resolve_db_root(raw_db_root: str) -> pathlib.Path:
    requested_root = pathlib.Path(raw_db_root).expanduser().resolve()
    if requested_root != DEFAULT_DB_ROOT:
        raise QueryError(
            f"--db-root must be fixed to {DEFAULT_DB_ROOT} for cross-project shared storage."
        )
    return requested_root


def load_local_match(db_root: pathlib.Path, block_name: str, field_name: Optional[str]) -> Optional[dict[str, Any]]:
    block_path = block_file_path(db_root, block_name)
    block_data = read_json_file(block_path)
    if block_data is None:
        return None

    if field_name:
        query_key = canonical_id(field_name)
        for field in block_data.get("fields", []):
            name_candidates = [str(field.get("name", ""))]
            aliases = field.get("aliases", [])
            if isinstance(aliases, list):
                name_candidates.extend(str(alias) for alias in aliases)

            if any(canonical_id(candidate) == query_key for candidate in name_candidates if candidate):
                return {
                    "status": "found",
                    "source": "local-db",
                    "source_location": str(block_path),
                    "block_name": block_data.get("block_name", block_name),
                    "field_name": field.get("name", field_name),
                    "field_value": field.get("value"),
                    "evidence": field.get("evidence", ""),
                    "fetched_at": utc_now(),
                    "query_order": QUERY_ORDER,
                }
        return None

    return {
        "status": "found",
        "source": "local-db",
        "source_location": str(block_path),
        "block_name": block_data.get("block_name", block_name),
        "entry": block_data,
        "query_order": QUERY_ORDER,
    }


def safe_read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="ignore")


def extract_yaml_or_xml_value(text: str, field_name: str) -> Optional[str]:
    escaped = re.escape(field_name)
    yaml_match = re.search(rf"^\s*{escaped}\s*:\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
    if yaml_match:
        return yaml_match.group(1).strip()

    xml_match = re.search(rf"<{escaped}>(.*?)</{escaped}>", text, flags=re.IGNORECASE | re.DOTALL)
    if xml_match:
        return re.sub(r"\s+", " ", xml_match.group(1)).strip()

    return None


def extract_matching_line(text: str, keyword: str) -> str:
    for line in text.splitlines():
        if keyword.lower() in line.lower():
            return line.strip()[:500]
    return ""


def strip_wrapping_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def parse_yaml_scalar(raw_value: str) -> Any:
    text = raw_value.strip()
    if not text:
        return ""

    lowered = text.lower()
    if lowered in {"none", "null"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return strip_wrapping_quotes(text)

    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [strip_wrapping_quotes(part.strip()) for part in inner.split(",")]

    return text


def extract_top_level_yaml_value(text: str, key: str) -> Optional[Any]:
    pattern = re.compile(rf"^{re.escape(key)}\s*:\s*(.+)$", flags=re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    return parse_yaml_scalar(match.group(1))


def parse_grc_yaml_parameters(text: str) -> list[dict[str, Any]]:
    try:
        import yaml

        yaml_data = yaml.safe_load(text)
    except Exception:
        yaml_data = None

    if isinstance(yaml_data, dict) and isinstance(yaml_data.get("parameters"), list):
        normalized_from_yaml: list[dict[str, Any]] = []
        for parameter in yaml_data["parameters"]:
            if not isinstance(parameter, dict):
                continue
            parameter_id = parameter.get("id")
            if not isinstance(parameter_id, str) or not parameter_id.strip():
                continue
            normalized_parameter = dict(parameter)
            if "label" not in normalized_parameter or not str(normalized_parameter.get("label", "")).strip():
                normalized_parameter["label"] = parameter_id
            normalized_from_yaml.append(normalized_parameter)
        return normalized_from_yaml

    lines = text.splitlines()
    in_parameters = False
    current: Optional[dict[str, Any]] = None
    parameters: list[dict[str, Any]] = []

    for line in lines:
        if not in_parameters:
            if re.match(r"^parameters\s*:\s*$", line.strip()):
                in_parameters = True
            continue

        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", line):
            if current is not None:
                parameters.append(current)
                current = None
            break

        item_match = re.match(r"^\s*-\s+id\s*:\s*(.+)$", line)
        if item_match:
            if current is not None:
                parameters.append(current)
            current = {"id": parse_yaml_scalar(item_match.group(1))}
            continue

        if current is None:
            continue

        key_match = re.match(r"^\s{2,}([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if key_match:
            key = key_match.group(1)
            raw_value = key_match.group(2)
            current[key] = parse_yaml_scalar(raw_value)

    if current is not None:
        parameters.append(current)

    normalized: list[dict[str, Any]] = []
    for parameter in parameters:
        parameter_id = parameter.get("id")
        if not isinstance(parameter_id, str) or not parameter_id.strip():
            continue
        parameter = dict(parameter)
        if "label" not in parameter or not str(parameter.get("label", "")).strip():
            parameter["label"] = parameter_id
        normalized.append(parameter)

    return normalized


def parameter_field_payload(parameter: dict[str, Any]) -> dict[str, Any]:
    parameter_id = str(parameter.get("id", "")).strip()
    parameter_label = str(parameter.get("label", parameter_id)).strip() or parameter_id

    aliases: list[str] = []
    for candidate in (parameter_label, parameter_id):
        if candidate and candidate not in aliases:
            aliases.append(candidate)

    value_payload = dict(parameter)
    value_payload["id"] = parameter_id
    value_payload["label"] = parameter_label

    return {
        "name": parameter_label,
        "aliases": aliases,
        "value": value_payload,
        "evidence": f"parameter id={parameter_id} label={parameter_label}",
    }


def find_matching_parameter_payload(parameters: list[dict[str, Any]], field_name: str) -> Optional[dict[str, Any]]:
    query_key = canonical_id(field_name)
    payloads = [parameter_field_payload(parameter) for parameter in parameters]

    for payload in payloads:
        candidates = [payload.get("name", "")]
        aliases = payload.get("aliases", [])
        if isinstance(aliases, list):
            candidates.extend(str(alias) for alias in aliases)

        if any(canonical_id(candidate) == query_key for candidate in candidates if candidate):
            return payload

    field_lc = field_name.lower()
    for payload in payloads:
        if field_lc in str(payload.get("name", "")).lower():
            return payload

    return None


def is_allowed_url(url: str) -> bool:
    if not url.startswith(ALLOWED_URL_PREFIXES):
        return False

    if url.startswith("https://api.github.com/search/code"):
        decoded = urllib.parse.unquote(url)
        return "repo:gnuradio/gnuradio" in decoded

    if url.startswith("https://api.github.com/repos/"):
        return url.startswith("https://api.github.com/repos/gnuradio/gnuradio/")

    if url.startswith("https://github.com/"):
        return url.startswith("https://github.com/gnuradio/gnuradio")

    return True


def fetch_url(url: str, headers: Optional[dict[str, str]] = None, timeout: int = 10) -> str:
    if not is_allowed_url(url):
        raise QueryError(f"URL is not in allowlist: {url}")

    request_headers = {"User-Agent": "grc-block-query/0.1"}
    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(url=url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def resolve_radioconda_block_roots(radioconda_path: pathlib.Path) -> list[pathlib.Path]:
    base_path = radioconda_path.expanduser()
    candidate_roots = [
        base_path / "grc" / "blocks",
        base_path / "share" / "gnuradio" / "grc" / "blocks",
        base_path / "Library" / "share" / "gnuradio" / "grc" / "blocks",
    ]

    conda_root: Optional[pathlib.Path] = None
    if (base_path / "envs").exists():
        conda_root = base_path
    else:
        for ancestor in base_path.parents:
            if (ancestor / "envs").exists():
                conda_root = ancestor
                break

    if conda_root is not None:
        envs_dir = conda_root / "envs"
        for env_dir in envs_dir.iterdir():
            candidate_roots.append(env_dir / "grc" / "blocks")
            candidate_roots.append(env_dir / "share" / "gnuradio" / "grc" / "blocks")
            candidate_roots.append(env_dir / "Library" / "share" / "gnuradio" / "grc" / "blocks")

    unique_roots: list[pathlib.Path] = []
    seen: set[str] = set()
    for root in candidate_roots:
        key = str(root.resolve(strict=False)).lower()
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(root)

    return unique_roots


def search_radioconda(
    radioconda_path: pathlib.Path,
    block_name: str,
    field_name: Optional[str],
    max_files: int,
) -> Optional[dict[str, Any]]:
    candidate_roots = resolve_radioconda_block_roots(radioconda_path)

    terms = [token for token in canonical_id(block_name).split("-") if token]
    block_query_key = canonical_id(block_name)

    best_match: Optional[dict[str, Any]] = None
    best_score = -1

    scanned_files = 0

    for root in candidate_roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if scanned_files >= max_files:
                return best_match
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".yml", ".yaml"}:
                continue
            if ".block." not in path.name.lower():
                continue
            if path.stat().st_size > 2 * 1024 * 1024:
                continue

            scanned_files += 1

            path_lc = str(path).lower()
            text = safe_read_text(path)
            text_lc = text.lower()
            block_label = extract_top_level_yaml_value(text, "label")
            block_id = extract_top_level_yaml_value(text, "id")
            label_str = str(block_label) if isinstance(block_label, str) else ""
            id_str = str(block_id) if isinstance(block_id, str) else ""

            label_key = canonical_id(label_str)
            id_key = canonical_id(id_str)
            path_key = canonical_id(path.name.replace(".block.yml", "").replace(".block.yaml", ""))
            suffix_key = f"-{block_query_key}" if block_query_key else ""
            exact_label_match = bool(block_query_key and block_query_key == label_key)
            exact_id_match = bool(
                block_query_key
                and (block_query_key == id_key or (suffix_key and id_key.endswith(suffix_key)))
            )
            exact_path_match = bool(
                block_query_key
                and (block_query_key == path_key or (suffix_key and path_key.endswith(suffix_key)))
            )

            score = 0
            if exact_label_match:
                score += 100
            if exact_id_match:
                score += 80
            if exact_path_match:
                score += 60
            score += sum(1 for token in terms if token in path_lc or token in label_key or token in id_key)

            if score == 0 and block_name.lower() not in text_lc and block_name.lower() not in path_lc:
                continue

            parameters = parse_grc_yaml_parameters(text)
            if not parameters:
                continue

            field_records: list[dict[str, Any]] = []
            output_field_name = ""
            output_field_value: Any = None
            evidence = ""

            if field_name:
                matched_payload = find_matching_parameter_payload(parameters, field_name)
                if matched_payload is None:
                    continue
                field_records = [matched_payload]
                output_field_name = matched_payload["name"]
                output_field_value = matched_payload["value"]
                evidence = matched_payload["evidence"]
                score += 10
            else:
                field_records = [parameter_field_payload(parameter) for parameter in parameters]
                output_field_name = "__grc_parameters__"
                output_field_value = [record["value"] for record in field_records]
                evidence = f"parameters_count={len(field_records)}"
                score += min(len(field_records), 20)

            if score > best_score:
                best_score = score
                best_match = {
                    "source": "radioconda",
                    "source_location": str(path),
                    "field_name": output_field_name,
                    "field_value": output_field_value,
                    "field_records": field_records,
                    "evidence": evidence,
                    "fetched_at": utc_now(),
                }

            if exact_label_match or exact_id_match or exact_path_match:
                return best_match

    return best_match


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def search_github(
    block_name: str,
    field_name: Optional[str],
    timeout: int,
    max_items: int,
) -> Optional[dict[str, Any]]:
    query_terms = [
        f'repo:gnuradio/gnuradio "{block_name}"',
        "path:grc/blocks",
        "filename:.block.yml",
    ]
    if field_name:
        query_terms.append(f'"{field_name}"')
    search_query = " ".join(query_terms)

    search_url = (
        "https://api.github.com/search/code?q="
        + urllib.parse.quote(search_query)
        + f"&per_page={max(1, max_items)}"
    )

    try:
        payload = fetch_url(search_url, headers=github_headers(), timeout=timeout)
    except (QueryError, urllib.error.URLError, urllib.error.HTTPError):
        return None

    try:
        search_result = json.loads(payload)
    except json.JSONDecodeError:
        return None

    for item in search_result.get("items", [])[: max(1, max_items)]:
        content_api_url = item.get("url", "")
        html_url = item.get("html_url", "")
        if html_url and not html_url.lower().endswith((".block.yml", ".block.yaml")):
            continue
        if not content_api_url or not is_allowed_url(content_api_url):
            continue

        try:
            content_payload = fetch_url(content_api_url, headers=github_headers(), timeout=timeout)
            content_obj = json.loads(content_payload)
        except (QueryError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            continue

        encoded_content = content_obj.get("content", "")
        if not encoded_content:
            continue

        try:
            decoded = base64.b64decode(encoded_content).decode("utf-8", errors="ignore")
        except ValueError:
            continue

        parameters = parse_grc_yaml_parameters(decoded)
        if not parameters:
            continue

        field_records: list[dict[str, Any]] = []
        output_field_name = ""
        output_field_value: Any = None
        evidence = ""

        if field_name:
            matched_payload = find_matching_parameter_payload(parameters, field_name)
            if matched_payload is None:
                continue
            field_records = [matched_payload]
            output_field_name = matched_payload["name"]
            output_field_value = matched_payload["value"]
            evidence = matched_payload["evidence"]
        else:
            field_records = [parameter_field_payload(parameter) for parameter in parameters]
            output_field_name = "__grc_parameters__"
            output_field_value = [record["value"] for record in field_records]
            evidence = f"parameters_count={len(field_records)}"

        return {
            "source": "gnuradio-github",
            "source_location": html_url or content_api_url,
            "field_name": output_field_name,
            "field_value": output_field_value,
            "field_records": field_records,
            "evidence": evidence,
            "fetched_at": utc_now(),
        }

    return None


def search_wiki(block_name: str, field_name: Optional[str], timeout: int) -> Optional[dict[str, Any]]:
    search_url = "https://wiki.gnuradio.org/index.php?search=" + urllib.parse.quote(block_name)
    try:
        search_html = fetch_url(search_url, timeout=timeout)
    except (QueryError, urllib.error.URLError, urllib.error.HTTPError):
        return None

    page_url = search_url
    match = re.search(r'href="(/index\.php/[^"#?]+)"', search_html, flags=re.IGNORECASE)
    if match:
        candidate = urllib.parse.urljoin("https://wiki.gnuradio.org", match.group(1))
        if candidate.startswith("https://wiki.gnuradio.org/"):
            page_url = candidate

    try:
        page_html = fetch_url(page_url, timeout=timeout)
    except (QueryError, urllib.error.URLError, urllib.error.HTTPError):
        return None

    keyword = field_name or block_name
    evidence = extract_matching_line(page_html, keyword)
    if not evidence:
        return None

    return {
        "source": "gnuradio-wiki",
        "source_location": page_url,
        "field_name": field_name or "__block_definition__",
        "field_value": evidence,
        "evidence": evidence,
        "fetched_at": utc_now(),
    }


def search_ettus(block_name: str, field_name: Optional[str], timeout: int) -> Optional[dict[str, Any]]:
    search_url = "https://www.ettus.com/?s=" + urllib.parse.quote(block_name)
    try:
        search_html = fetch_url(search_url, timeout=timeout)
    except (QueryError, urllib.error.URLError, urllib.error.HTTPError):
        return None

    page_url = search_url
    match = re.search(r'href="(https://www\.ettus\.com/[^"#]+)"', search_html, flags=re.IGNORECASE)
    if match:
        page_url = match.group(1)

    try:
        page_html = fetch_url(page_url, timeout=timeout)
    except (QueryError, urllib.error.URLError, urllib.error.HTTPError):
        return None

    keyword = field_name or block_name
    evidence = extract_matching_line(page_html, keyword)
    if not evidence:
        return None

    return {
        "source": "ettus",
        "source_location": page_url,
        "field_name": field_name or "__block_definition__",
        "field_value": evidence,
        "evidence": evidence,
        "fetched_at": utc_now(),
    }


def upsert_block_entry(db_root: pathlib.Path, block_name: str, hit: dict[str, Any]) -> pathlib.Path:
    if hit.get("source") not in ALLOWED_SOURCE_IDS:
        raise QueryError(f"Unexpected source id: {hit.get('source')}")

    block_path = block_file_path(db_root, block_name)
    existing = read_json_file(block_path)

    if existing is None:
        existing = {
            "block_name": block_name,
            "canonical_id": canonical_id(block_name),
            "updated_at": utc_now(),
            "query_order": QUERY_ORDER,
            "sources": [],
            "fields": [],
        }

    source_record = {
        "id": hit["source"],
        "location": hit["source_location"],
        "fetched_at": hit["fetched_at"],
    }

    source_updated = False
    existing_sources = existing.setdefault("sources", [])
    for current_source in existing_sources:
        same_source = (
            current_source.get("id") == source_record["id"]
            and current_source.get("location") == source_record["location"]
        )
        if same_source:
            current_source["fetched_at"] = source_record["fetched_at"]
            source_updated = True
            break

    if not source_updated:
        existing_sources.append(source_record)

    dedup_sources: dict[tuple[str, str], dict[str, Any]] = {}
    for current_source in existing_sources:
        key = (str(current_source.get("id", "")), str(current_source.get("location", "")))
        previous = dedup_sources.get(key)
        if previous is None:
            dedup_sources[key] = current_source
            continue

        prev_ts = str(previous.get("fetched_at", ""))
        current_ts = str(current_source.get("fetched_at", ""))
        if current_ts >= prev_ts:
            dedup_sources[key] = current_source

    existing["sources"] = list(dedup_sources.values())

    input_fields = hit.get("field_records")
    normalized_fields: list[dict[str, Any]] = []

    if isinstance(input_fields, list) and input_fields:
        for input_field in input_fields:
            if not isinstance(input_field, dict):
                continue

            field_name = str(input_field.get("name", "")).strip()
            if not field_name:
                continue

            aliases: list[str] = []
            raw_aliases = input_field.get("aliases", [])
            if isinstance(raw_aliases, list):
                for alias in raw_aliases:
                    alias_text = str(alias).strip()
                    if alias_text and alias_text not in aliases:
                        aliases.append(alias_text)

            normalized_fields.append(
                {
                    "name": field_name,
                    "value": input_field.get("value"),
                    "aliases": aliases,
                    "evidence": str(input_field.get("evidence", "")),
                }
            )
    else:
        normalized_fields.append(
            {
                "name": str(hit["field_name"]),
                "value": hit["field_value"],
                "aliases": [],
                "evidence": str(hit.get("evidence", "")),
            }
        )

    replace_source_fields = bool(hit.get("field_records")) and hit.get("field_name") == "__grc_parameters__"
    if replace_source_fields:
        existing["sources"] = [
            source
            for source in existing.get("sources", [])
            if source.get("id") != hit["source"] or source.get("location") == hit["source_location"]
        ]
    if replace_source_fields:
        existing["fields"] = [
            field for field in existing.get("fields", []) if field.get("source") != hit["source"]
        ]

    for normalized_field in normalized_fields:
        field_record: dict[str, Any] = {
            "name": normalized_field["name"],
            "value": normalized_field["value"],
            "value_type": infer_value_type(normalized_field["value"]),
            "source": hit["source"],
            "reference": hit["source_location"],
            "fetched_at": hit["fetched_at"],
            "status": "verified",
            "evidence": normalized_field.get("evidence", ""),
        }

        aliases = normalized_field.get("aliases", [])
        if isinstance(aliases, list) and aliases:
            field_record["aliases"] = aliases

        target_keys = {canonical_id(field_record["name"])}
        if isinstance(field_record.get("aliases"), list):
            target_keys.update(canonical_id(alias) for alias in field_record["aliases"] if alias)

        replaced = False
        for index, current in enumerate(existing.get("fields", [])):
            if current.get("source") != field_record["source"]:
                continue

            current_keys = {canonical_id(str(current.get("name", "")))}
            current_aliases = current.get("aliases", [])
            if isinstance(current_aliases, list):
                current_keys.update(canonical_id(str(alias)) for alias in current_aliases)

            if target_keys & current_keys:
                existing["fields"][index] = field_record
                replaced = True
                break

        if not replaced:
            existing.setdefault("fields", []).append(field_record)

    existing["updated_at"] = utc_now()

    write_json_file(block_path, existing)
    return block_path


def update_index(db_root: pathlib.Path, block_name: str, block_path: pathlib.Path) -> None:
    index_path = db_root / "index.json"
    index_data = read_json_file(index_path)

    if index_data is None:
        index_data = {
            "version": "0.1.0",
            "query_order": QUERY_ORDER,
            "last_updated": None,
            "blocks": {},
        }

    entry = read_json_file(block_path) or {}
    fields = entry.get("fields", [])

    relative_path = block_path.relative_to(db_root).as_posix()
    index_data.setdefault("blocks", {})[canonical_id(block_name)] = {
        "block_name": entry.get("block_name", block_name),
        "file": relative_path,
        "updated_at": entry.get("updated_at", utc_now()),
        "field_count": len(fields),
    }
    index_data["last_updated"] = utc_now()

    write_json_file(index_path, index_data)


def validate_status(value: str) -> str:
    if value not in ALLOWED_STATUSES:
        raise QueryError(f"Unsupported status value: {value}")
    return value


def execute_query(
    db_root: pathlib.Path,
    radioconda_path: pathlib.Path,
    block_name: str,
    field_name: Optional[str],
    update_db: bool,
    offline: bool,
    network_timeout: int,
    max_github_items: int,
    max_radioconda_files: int,
    refresh: bool,
) -> dict[str, Any]:
    searched_sources: list[str] = []

    if not refresh:
        searched_sources.append("local-db")
        local_result = load_local_match(db_root, block_name, field_name)
        if local_result:
            append_audit_log(
                db_root,
                {
                    "timestamp": utc_now(),
                    "block_name": block_name,
                    "field_name": field_name,
                    "result": "found",
                    "source": "local-db",
                },
            )
            return local_result

    search_functions = [
        (
            "radioconda",
            lambda: search_radioconda(
                radioconda_path,
                block_name,
                field_name,
                max_files=max_radioconda_files,
            ),
        ),
    ]

    if not offline:
        search_functions.extend(
            [
                (
                    "gnuradio-github",
                    lambda: search_github(
                        block_name,
                        field_name,
                        timeout=network_timeout,
                        max_items=max_github_items,
                    ),
                ),
                (
                    "gnuradio-wiki",
                    lambda: search_wiki(block_name, field_name, timeout=network_timeout),
                ),
                (
                    "ettus",
                    lambda: search_ettus(block_name, field_name, timeout=network_timeout),
                ),
            ]
        )

    for source_id, source_search in search_functions:
        searched_sources.append(source_id)
        hit = source_search()
        if hit is None:
            continue

        validate_status("verified")

        block_path = None
        if update_db:
            block_path = upsert_block_entry(db_root, block_name, hit)
            update_index(db_root, block_name, block_path)

        result = {
            "status": "found",
            "source": source_id,
            "source_location": hit["source_location"],
            "block_name": block_name,
            "field_name": hit["field_name"],
            "field_value": hit["field_value"],
            "evidence": hit["evidence"],
            "fetched_at": hit["fetched_at"],
            "query_order": QUERY_ORDER,
        }
        if block_path is not None:
            result["db_file"] = str(block_path)

        append_audit_log(
            db_root,
            {
                "timestamp": utc_now(),
                "block_name": block_name,
                "field_name": field_name,
                "result": "found",
                "source": source_id,
                "source_location": hit["source_location"],
                "db_updated": bool(update_db),
            },
        )
        return result

    not_found = {
        "status": "not_found",
        "block_name": block_name,
        "field_name": field_name,
        "searched_sources": searched_sources,
        "message": "No verifiable data found in allowed sources.",
    }

    append_audit_log(
        db_root,
        {
            "timestamp": utc_now(),
            "block_name": block_name,
            "field_name": field_name,
            "result": "not_found",
            "searched_sources": searched_sources,
        },
    )
    return not_found


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query GRC block field data.")
    parser.add_argument("--block", required=True, help="Block name, e.g. 'Constellation Object'.")
    parser.add_argument("--field", default=None, help="Optional field name.")
    parser.add_argument(
        "--db-root",
        default=str(DEFAULT_DB_ROOT),
        help="Database root path. Fixed to ~/Documents/grc-block-query/db.",
    )
    parser.add_argument(
        "--radioconda-path",
        default=str(DEFAULT_RADIOCONDA),
        help="radioconda base path. Defaults to GRC_RADIOCONDA_PATH or ~/radioconda/Library/share/gnuradio.",
    )
    parser.add_argument(
        "--no-update-db",
        action="store_true",
        help="Do not write lookup results back into local database.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip web sources and only use local-db plus radioconda.",
    )
    parser.add_argument(
        "--network-timeout",
        type=int,
        default=8,
        help="Per-request timeout in seconds for web sources.",
    )
    parser.add_argument(
        "--max-github-items",
        type=int,
        default=2,
        help="Maximum GitHub code search items to inspect.",
    )
    parser.add_argument(
        "--max-radioconda-files",
        type=int,
        default=2500,
        help="Maximum radioconda candidate files to scan.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Bypass local-db cache and force querying external sources in priority order.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    block_name = args.block.strip()
    if not block_name:
        raise QueryError("--block cannot be empty.")

    field_name = args.field.strip() if args.field else None
    db_root = resolve_db_root(args.db_root)
    radioconda_path = pathlib.Path(args.radioconda_path).expanduser()

    initialize_db_root(db_root, radioconda_path)

    result = execute_query(
        db_root=db_root,
        radioconda_path=radioconda_path,
        block_name=block_name,
        field_name=field_name,
        update_db=not args.no_update_db,
        offline=bool(args.offline),
        network_timeout=max(1, args.network_timeout),
        max_github_items=max(1, args.max_github_items),
        max_radioconda_files=max(100, args.max_radioconda_files),
        refresh=bool(args.refresh),
    )

    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except QueryError as error:
        print(json.dumps({"status": "error", "message": str(error)}), file=sys.stderr)
        sys.exit(1)
