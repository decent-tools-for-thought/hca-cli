from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast


@dataclass(frozen=True)
class Parameter:
    name: str
    location: str
    required: bool
    description: str
    schema: dict[str, Any] | None = None
    content_type: str | None = None
    content_schema: dict[str, Any] | None = None

    @property
    def enum(self) -> list[Any]:
        if not self.schema:
            return []
        return list(self.schema.get("enum", []))

    @property
    def type_name(self) -> str:
        if self.schema and self.schema.get("type"):
            return str(self.schema["type"])
        if self.content_schema:
            return "json"
        return "unknown"


@dataclass(frozen=True)
class Operation:
    method: str
    path: str
    tags: tuple[str, ...]
    summary: str
    description: str
    parameters: tuple[Parameter, ...]
    request_body: dict[str, Any] | None = None

    @property
    def id(self) -> str:
        return f"{self.method} {self.path}"


@lru_cache(maxsize=1)
def _summary() -> dict[str, Any]:
    raw = files("hca_cli.data").joinpath("openapi_summary.json").read_text(encoding="utf-8")
    return cast(dict[str, Any], json.loads(raw))


@lru_cache(maxsize=1)
def operations() -> tuple[Operation, ...]:
    items: list[Operation] = []
    for raw_op in _summary()["operations"]:
        params = tuple(
            Parameter(
                name=raw_param["name"],
                location=raw_param["in"],
                required=raw_param["required"],
                description=raw_param.get("description", ""),
                schema=raw_param.get("schema"),
                content_type=raw_param.get("content_type"),
                content_schema=raw_param.get("content_schema"),
            )
            for raw_param in raw_op["parameters"]
        )
        items.append(
            Operation(
                method=raw_op["method"],
                path=raw_op["path"],
                tags=tuple(raw_op.get("tags", [])),
                summary=raw_op.get("summary", ""),
                description=raw_op.get("description", ""),
                parameters=params,
                request_body=raw_op.get("requestBody"),
            )
        )
    return tuple(items)


@lru_cache(maxsize=1)
def operation_map() -> dict[tuple[str, str], Operation]:
    return {(operation.method, operation.path): operation for operation in operations()}


def get_operation(method: str, path: str) -> Operation:
    key = (method.upper(), path)
    try:
        return operation_map()[key]
    except KeyError as exc:
        raise KeyError(f"Unknown operation: {method.upper()} {path}") from exc


def api_info() -> dict[str, Any]:
    summary = _summary()
    return {
        "title": summary["title"],
        "version": summary["version"],
        "description": summary["description"],
        "server_url": summary["server_url"],
    }


def catalogs() -> list[str]:
    return list(_summary()["catalogs"])


def entity_types() -> list[str]:
    return list(_summary()["entity_types"])


def manifest_formats() -> list[str]:
    return list(_summary()["manifest_formats"])


def sort_fields() -> list[str]:
    return list(_summary()["sort_fields"])


def filter_fields() -> dict[str, dict[str, Any]]:
    return dict(_summary()["filter_fields"])
