from __future__ import annotations

import json
from typing import Any

from hca_cli.client import ApiResponse


def _endswith(path: tuple[str, ...], suffix: tuple[str, ...]) -> bool:
    return len(path) >= len(suffix) and path[-len(suffix) :] == suffix


def _scalar_list_summary(values: list[Any], limit: int) -> dict[str, Any]:
    return {
        "_summary": f"{len(values)} items; showing first {limit}. Use --full for all items.",
        "items": values[:limit],
    }


def compact_payload(payload: Any, *, full: bool = False, path: tuple[str, ...] = ()) -> Any:
    if full:
        return payload
    if isinstance(payload, dict):
        compacted: dict[str, Any] = {}
        for key, value in payload.items():
            child_path = path + (key,)
            if key == "contributedAnalyses" and isinstance(value, dict):
                compacted[key] = {
                    "_summary": "Large nested contributed analyses omitted by default. Use --full for the raw structure.",
                    "top_level_keys": list(value.keys())[:10],
                    "top_level_key_count": len(value),
                }
                continue
            compacted[key] = compact_payload(value, full=full, path=child_path)
        return compacted
    if isinstance(payload, list):
        if _endswith(path, ("terms",)) and len(payload) > 10:
            return {
                "_summary": f"{len(payload)} facet terms; showing the first 10 sorted terms. Use --full for the full facet.",
                "items": [
                    compact_payload(item, full=full, path=path + ("*",)) for item in payload[:10]
                ],
            }
        if _endswith(path, ("sources",)) and len(payload) > 5:
            return {
                "_summary": f"{len(payload)} repository source identifiers; showing the first 5. Use --full for every source.",
                "items": payload[:5],
            }
        if _endswith(path, ("organTypes",)) and len(payload) > 20:
            return _scalar_list_summary(payload, 20)
        if (
            path
            and path[-1] in {"contributors", "publications", "supplementaryLinks", "accessions"}
            and len(payload) > 6
        ):
            return {
                "_summary": f"{len(payload)} items; showing the first 6. Use --full for the complete list.",
                "items": [
                    compact_payload(item, full=full, path=path + ("*",)) for item in payload[:6]
                ],
            }
        return [compact_payload(item, full=full, path=path + ("*",)) for item in payload]
    return payload


def response_to_display(
    response: ApiResponse,
    *,
    full: bool = False,
    include_headers: bool = False,
) -> Any:
    parsed = response.json()
    if parsed is not None and response.status < 300 and not include_headers:
        return compact_payload(parsed, full=full)

    display: dict[str, Any] = {"status": response.status}
    headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() in {"location", "retry-after", "content-type", "etag"}
    }
    if headers:
        display["headers"] = headers
    if parsed is not None:
        display["body"] = compact_payload(parsed, full=full)
    elif response.body:
        display["body"] = response.text()
    return display


def dump_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True)


def render_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "No rows."
    widths = []
    for key, title in columns:
        width = len(title)
        for row in rows:
            width = max(width, len(str(row.get(key, ""))))
        widths.append(width)
    header = "  ".join(
        title.ljust(width) for (_, title), width in zip(columns, widths, strict=True)
    )
    divider = "  ".join("-" * width for width in widths)
    body = [
        "  ".join(
            str(row.get(key, "")).ljust(width)
            for (key, _), width in zip(columns, widths, strict=True)
        )
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def format_bytes(value: float | int | None) -> str:
    if value is None:
        return "-"
    amount = float(value)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} PB"
