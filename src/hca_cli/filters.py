from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_scalar(text: str) -> Any:
    candidate = text.strip()
    if candidate == "":
        return ""
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return candidate


def parse_assignment(text: str) -> tuple[str, str]:
    if "=" not in text:
        raise ValueError(f"Expected NAME=VALUE, got {text!r}")
    name, value = text.split("=", 1)
    name = name.strip()
    value = value.strip()
    if not name:
        raise ValueError(f"Expected NAME=VALUE, got {text!r}")
    return name, value


def parse_filter_assignment(text: str) -> tuple[str, dict[str, Any]]:
    field, raw_value = parse_assignment(text)
    if raw_value.startswith("[") or raw_value.startswith("{"):
        values = json.loads(raw_value)
        if not isinstance(values, list):
            values = [values]
    else:
        values = [parse_scalar(part) for part in raw_value.split(",")]
    return field, {"is": values}


def parse_within_assignment(text: str) -> tuple[str, dict[str, Any]]:
    field, raw_value = parse_assignment(text)
    if ".." not in raw_value:
        raise ValueError(f"Expected NAME=LOW..HIGH, got {text!r}")
    low, high = raw_value.split("..", 1)
    return field, {"within": [[parse_scalar(low), parse_scalar(high)]]}


def merge_filters(
    *,
    filter_assignments: list[str] | None = None,
    within_assignments: list[str] | None = None,
    filters_json: str | None = None,
    filters_file: str | None = None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if filters_json:
        parsed = json.loads(filters_json)
        if not isinstance(parsed, dict):
            raise ValueError("--filters-json must decode to a JSON object")
        merged.update(parsed)
    if filters_file:
        parsed = json.loads(Path(filters_file).read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("--filters-file must contain a JSON object")
        merged.update(parsed)
    for assignment in filter_assignments or []:
        field, payload = parse_filter_assignment(assignment)
        merged[field] = payload
    for assignment in within_assignments or []:
        field, payload = parse_within_assignment(assignment)
        merged[field] = payload
    return merged
