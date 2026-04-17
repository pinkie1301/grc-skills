#!/usr/bin/env python3
"""Validate local GRC block files for field-format correctness.

This validator only checks schema/type/required-field format.
It does not validate source trustworthiness or semantic truth.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
from typing import Any

DEFAULT_SHARED_ROOT = (pathlib.Path.home() / "Documents" / "grc-block-query").expanduser().resolve()
DEFAULT_DB_ROOT = (DEFAULT_SHARED_ROOT / "db").resolve()
ALLOWED_SOURCES = {"local-db", "radioconda", "gnuradio-github", "gnuradio-wiki", "ettus"}
ALLOWED_FIELD_STATUSES = {"verified", "pending", "conflict"}
ALLOWED_VALUE_TYPES = {"string", "number", "boolean", "json", "null"}


def parse_iso8601(value: Any, field_name: str, path: pathlib.Path, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{path}: {field_name} must be a string timestamp")
        return

    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{path}: {field_name} is not valid ISO8601: {value}")


def expect_type(value: Any, expected_type: type, label: str, path: pathlib.Path, errors: list[str]) -> None:
    if not isinstance(value, expected_type):
        errors.append(f"{path}: {label} must be {expected_type.__name__}")


def validate_source_records(sources: Any, path: pathlib.Path, errors: list[str]) -> None:
    if not isinstance(sources, list):
        errors.append(f"{path}: sources must be a list")
        return

    for idx, source in enumerate(sources):
        label = f"sources[{idx}]"
        if not isinstance(source, dict):
            errors.append(f"{path}: {label} must be an object")
            continue

        for required in ("id", "location", "fetched_at"):
            if required not in source:
                errors.append(f"{path}: {label}.{required} is required")

        source_id = source.get("id")
        if isinstance(source_id, str) and source_id not in ALLOWED_SOURCES:
            errors.append(f"{path}: {label}.id is not allowed: {source_id}")

        expect_type(source.get("location"), str, f"{label}.location", path, errors)
        parse_iso8601(source.get("fetched_at"), f"{label}.fetched_at", path, errors)


def validate_field_records(fields: Any, path: pathlib.Path, errors: list[str]) -> None:
    if not isinstance(fields, list):
        errors.append(f"{path}: fields must be a list")
        return

    for idx, field in enumerate(fields):
        label = f"fields[{idx}]"
        if not isinstance(field, dict):
            errors.append(f"{path}: {label} must be an object")
            continue

        required_keys = (
            "name",
            "value",
            "value_type",
            "source",
            "reference",
            "fetched_at",
            "status",
            "evidence",
        )
        for required in required_keys:
            if required not in field:
                errors.append(f"{path}: {label}.{required} is required")

        expect_type(field.get("name"), str, f"{label}.name", path, errors)
        expect_type(field.get("reference"), str, f"{label}.reference", path, errors)
        expect_type(field.get("evidence"), str, f"{label}.evidence", path, errors)

        value_type = field.get("value_type")
        if not isinstance(value_type, str):
            errors.append(f"{path}: {label}.value_type must be string")
        elif value_type not in ALLOWED_VALUE_TYPES:
            errors.append(f"{path}: {label}.value_type is invalid: {value_type}")

        source_id = field.get("source")
        if not isinstance(source_id, str):
            errors.append(f"{path}: {label}.source must be string")
        elif source_id not in ALLOWED_SOURCES:
            errors.append(f"{path}: {label}.source is not allowed: {source_id}")

        status = field.get("status")
        if not isinstance(status, str):
            errors.append(f"{path}: {label}.status must be string")
        elif status not in ALLOWED_FIELD_STATUSES:
            errors.append(f"{path}: {label}.status is invalid: {status}")

        parse_iso8601(field.get("fetched_at"), f"{label}.fetched_at", path, errors)


def validate_block_entry(data: Any, path: pathlib.Path) -> list[str]:
    errors: list[str] = []

    if not isinstance(data, dict):
        return [f"{path}: root must be an object"]

    for key in ("block_name", "canonical_id", "updated_at", "query_order", "sources", "fields"):
        if key not in data:
            errors.append(f"{path}: {key} is required")

    expect_type(data.get("block_name"), str, "block_name", path, errors)
    expect_type(data.get("canonical_id"), str, "canonical_id", path, errors)
    parse_iso8601(data.get("updated_at"), "updated_at", path, errors)

    query_order = data.get("query_order")
    if not isinstance(query_order, list):
        errors.append(f"{path}: query_order must be a list")
    else:
        for idx, source_id in enumerate(query_order):
            if not isinstance(source_id, str):
                errors.append(f"{path}: query_order[{idx}] must be string")
            elif source_id not in ALLOWED_SOURCES:
                errors.append(f"{path}: query_order[{idx}] is not allowed: {source_id}")

    validate_source_records(data.get("sources"), path, errors)
    validate_field_records(data.get("fields"), path, errors)

    return errors


def validate_all_block_files(db_root: pathlib.Path) -> list[str]:
    block_dir = db_root / "blocks"
    if not block_dir.exists():
        return [f"{block_dir}: directory does not exist"]

    errors: list[str] = []
    for json_file in sorted(block_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            errors.append(f"{json_file}: invalid JSON - {err}")
            continue

        errors.extend(validate_block_entry(data, json_file))

    return errors


def emit_hook_response(continue_run: bool, message: str, errors: list[str]) -> None:
    payload: dict[str, Any] = {
        "continue": continue_run,
        "systemMessage": message,
    }
    if not continue_run:
        payload.update(
            {
                "decision": "block",
                "stopReason": "GRC field format validation failed",
                "errors": errors,
            }
        )

    print(json.dumps(payload, ensure_ascii=True))


def main() -> int:
    if not sys.stdin.isatty():
        _ = sys.stdin.read()

    db_root = DEFAULT_DB_ROOT
    errors = validate_all_block_files(db_root)

    if errors:
        emit_hook_response(
            continue_run=False,
            message="GRC field format validation failed.",
            errors=errors[:50],
        )
        return 2

    emit_hook_response(
        continue_run=True,
        message="GRC field format validation passed.",
        errors=[],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
