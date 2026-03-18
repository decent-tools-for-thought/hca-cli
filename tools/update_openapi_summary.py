from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen


OPENAPI_URL = "https://service.azul.data.humancellatlas.org/openapi.json"
OUTPUT_PATH = Path("src/hca_cli/data/openapi_summary.json")


def main() -> None:
    spec = json.load(urlopen(OPENAPI_URL))
    method_names = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}

    operations = []
    for path, item in spec["paths"].items():
        path_parameters = item.get("parameters", [])
        for method, operation in item.items():
            if method.lower() not in method_names:
                continue
            parameters = []
            for parameter in [*path_parameters, *operation.get("parameters", [])]:
                payload = {
                    "name": parameter["name"],
                    "in": parameter["in"],
                    "required": parameter.get("required", False),
                    "description": parameter.get("description", "").strip(),
                }
                if "schema" in parameter:
                    payload["schema"] = {
                        key: parameter["schema"][key]
                        for key in ("type", "format", "enum", "default", "nullable")
                        if key in parameter["schema"]
                    }
                if "content" in parameter:
                    content_type, media = next(iter(parameter["content"].items()))
                    payload["content_type"] = content_type
                    payload["content_schema"] = media.get("schema", {})
                parameters.append(payload)
            request_body = None
            if "requestBody" in operation:
                request_body = {
                    "required": operation["requestBody"].get("required", False),
                    "description": operation["requestBody"].get("description", "").strip(),
                    "content": {
                        content_type: {"schema": media.get("schema", {})}
                        for content_type, media in operation["requestBody"].get("content", {}).items()
                    },
                }
            operations.append(
                {
                    "id": f"{method.upper()} {path}",
                    "method": method.upper(),
                    "path": path,
                    "tags": operation.get("tags", []),
                    "summary": (operation.get("summary") or "").strip(),
                    "description": (operation.get("description") or "").strip(),
                    "parameters": parameters,
                    "requestBody": request_body,
                }
            )

    filters_schema = spec["paths"]["/index/{entity_type}"]["get"]["parameters"][1]["content"]["application/json"]["schema"]
    filter_summary = {}
    for name, schema in filters_schema["properties"].items():
        operators = []
        if "oneOf" in schema:
            for variant in schema["oneOf"]:
                operators.extend(variant.get("properties", {}).keys())
        else:
            operators.extend(schema.get("properties", {}).keys())
        filter_summary[name] = {
            "schema_kind": "oneOf" if "oneOf" in schema else "object",
            "operators": sorted(set(operators)),
        }

    output = {
        "title": spec["info"]["title"],
        "version": spec["info"]["version"],
        "description": spec["info"]["description"].strip(),
        "server_url": spec["servers"][0]["url"],
        "operations": operations,
        "catalogs": ["dcp57", "dcp57-it", "dcp58", "dcp58-it", "lm10", "lm10-it"],
        "entity_types": ["bundles", "files", "projects", "samples"],
        "manifest_formats": ["compact", "terra.pfb", "curl", "verbatim.jsonl", "verbatim.pfb"],
        "sort_fields": spec["paths"]["/index/{entity_type}"]["get"]["parameters"][4]["schema"]["enum"],
        "filter_fields": filter_summary,
    }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
