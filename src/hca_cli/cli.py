from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Callable, cast

from hca_cli.atlas import (
    atlas_project_filters,
    summarize_cell_types,
    summarize_modalities,
    summarize_tissues,
)
from hca_cli.client import ApiClient
from hca_cli.datasets import (
    dataset_detail_text,
    dataset_format_rows,
    dataset_text_rows,
    derive_datasets,
    filter_datasets,
)
from hca_cli.filters import merge_filters, parse_assignment
from hca_cli.formatting import dump_json, format_bytes, render_table, response_to_display
from hca_cli.spec import (
    api_info,
    catalogs,
    entity_types,
    get_operation,
    manifest_formats,
    operations,
    sort_fields,
)

DEFAULT_BASE_URL = "https://service.azul.data.humancellatlas.org"


class CliError(RuntimeError):
    pass


def add_transport_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL.")
    parser.add_argument(
        "--token", default=os.environ.get("HCA_API_BEARER_TOKEN"), help="Bearer token."
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")


def add_render_options(parser: argparse.ArgumentParser, *, default_output: str = "json") -> None:
    parser.add_argument(
        "--output", choices=("json", "text"), default=default_output, help="Output format."
    )
    parser.add_argument(
        "--full", action="store_true", help="Disable default elision and show the full response."
    )
    parser.add_argument(
        "--include-headers",
        action="store_true",
        help="Include selected response headers in the rendered output.",
    )
    parser.add_argument(
        "--follow-redirects",
        action="store_true",
        help="Follow HTTP redirects instead of showing redirect responses.",
    )


def add_catalog_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--catalog", choices=catalogs(), default="dcp57", help="Catalog to query.")


def add_filter_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--filter",
        action="append",
        default=[],
        metavar="FIELD=VALUE[,VALUE...]",
        help="Exact-match filter. Repeatable.",
    )
    parser.add_argument(
        "--within",
        action="append",
        default=[],
        metavar="FIELD=LOW..HIGH",
        help="Range filter. Repeatable.",
    )
    parser.add_argument("--filters-json", help="Raw JSON object for API filters.")
    parser.add_argument("--filters-file", help="Path to a JSON file containing API filters.")


def build_client(args: argparse.Namespace) -> ApiClient:
    return ApiClient(
        base_url=args.base_url,
        bearer_token=args.token,
        timeout=args.timeout,
        follow_redirects=args.follow_redirects,
    )


def merged_filters(args: argparse.Namespace) -> dict[str, Any]:
    return merge_filters(
        filter_assignments=getattr(args, "filter", None),
        within_assignments=getattr(args, "within", None),
        filters_json=getattr(args, "filters_json", None),
        filters_file=getattr(args, "filters_file", None),
    )


def print_payload(payload: Any, output: str) -> None:
    if output == "json":
        print(dump_json(payload))
    else:
        if isinstance(payload, str):
            print(payload)
        else:
            print(dump_json(payload))


def invoke_operation(
    args: argparse.Namespace,
    *,
    method: str,
    path: str,
    path_params: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    json_body: Any | None = None,
) -> int:
    client = build_client(args)
    response = client.request(
        method, path, path_params=path_params, query=query, json_body=json_body
    )
    display = response_to_display(response, full=args.full, include_headers=args.include_headers)
    print_payload(display, args.output)
    return 0 if response.status < 400 else 1


def cmd_explain(args: argparse.Namespace) -> int:
    info = api_info()
    lines = [
        f"{info['title']} v{info['version']}",
        "",
        "Mental model:",
        "  1. Catalogs are atlas spaces. The live service currently exposes HCA catalogs and LungMAP catalogs.",
        "  2. Indices are the main browse/search surfaces: bundles, files, projects, samples.",
        "  3. Filters are JSON objects. Use --filter for simple exact matches, --within for ranges, or --filters-json for full control.",
        "  4. Manifests and repository endpoints are download-oriented and often respond with redirects or XHR-style redirect metadata.",
        "  5. The atlas commands turn the raw facets and summaries into tissue, cell-type, and modality views.",
        "  6. The dataset commands derive dataset-like downloadable units from project detail metadata and are better suited to modality-first workflows.",
        "",
        "Useful examples:",
        "  hca index catalogs",
        "  hca index query projects --filter effectiveOrgan=lung --size 5",
        "  hca index summary --filter effectiveOrgan=brain",
        "  hca atlas tissues",
        "  hca dataset query --tissue lung --modality transcriptomics --limit 5",
        "  hca dataset formats --modality transcriptomics --project-limit 10",
        "  hca api describe GET /manifest/files/{token}",
    ]
    print("\n".join(lines))
    return 0


def cmd_api_operations(args: argparse.Namespace) -> int:
    rows = []
    for operation in operations():
        if args.tag and args.tag not in operation.tags:
            continue
        rows.append(
            {
                "method": operation.method,
                "path": operation.path,
                "tag": ",".join(operation.tags),
                "summary": operation.summary or "-",
            }
        )
    print(
        render_table(
            rows, [("method", "METHOD"), ("path", "PATH"), ("tag", "TAG"), ("summary", "SUMMARY")]
        )
    )
    return 0


def _describe_operation(method: str, path: str) -> dict[str, Any]:
    operation = get_operation(method, path)
    return {
        "operation": operation.id,
        "summary": operation.summary,
        "description": operation.description,
        "tags": list(operation.tags),
        "parameters": [
            {
                "name": parameter.name,
                "location": parameter.location,
                "required": parameter.required,
                "type": parameter.type_name,
                "enum": parameter.enum,
                "description": parameter.description,
            }
            for parameter in operation.parameters
        ],
        "request_body": operation.request_body,
    }


def cmd_api_describe(args: argparse.Namespace) -> int:
    print_payload(_describe_operation(args.method, args.path), args.output)
    return 0


def _pairs_to_dict(items: list[str]) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    for item in items:
        key, value = parse_assignment(item)
        pairs[key] = value
    return pairs


def _json_body_from_args(args: argparse.Namespace) -> Any | None:
    if getattr(args, "body_json", None):
        import json

        return json.loads(args.body_json)
    if getattr(args, "body_file", None):
        import json
        from pathlib import Path

        return json.loads(Path(args.body_file).read_text(encoding="utf-8"))
    return None


def cmd_api_call(args: argparse.Namespace) -> int:
    get_operation(args.method, args.path)
    return invoke_operation(
        args,
        method=args.method,
        path=args.path,
        path_params=_pairs_to_dict(args.path_param),
        query=_pairs_to_dict(args.query_param),
        json_body=_json_body_from_args(args),
    )


def cmd_aux_root(args: argparse.Namespace) -> int:
    return invoke_operation(args, method="GET", path="/")


def cmd_aux_swagger_ui(args: argparse.Namespace) -> int:
    return invoke_operation(args, method="GET", path="/swagger/index.html")


def cmd_aux_swagger_init(args: argparse.Namespace) -> int:
    return invoke_operation(args, method="GET", path="/swagger/swagger-initializer.js")


def cmd_aux_swagger_file(args: argparse.Namespace) -> int:
    return invoke_operation(
        args, method="GET", path="/swagger/{file}", path_params={"file": args.file}
    )


def cmd_aux_openapi(args: argparse.Namespace) -> int:
    return invoke_operation(args, method="GET", path="/openapi.json")


def cmd_aux_version(args: argparse.Namespace) -> int:
    return invoke_operation(args, method="GET", path="/version")


def cmd_aux_robots(args: argparse.Namespace) -> int:
    return invoke_operation(args, method="GET", path="/robots.txt")


def cmd_health(args: argparse.Namespace) -> int:
    if args.kind == "complete":
        path = "/health"
        path_params = None
    elif args.kind == "selective":
        path = "/health/{keys}"
        path_params = {"keys": args.keys}
    else:
        path = f"/health/{args.kind}"
        path_params = None
    return invoke_operation(args, method="GET", path=path, path_params=path_params)


def cmd_index_catalogs(args: argparse.Namespace) -> int:
    return invoke_operation(args, method="GET", path="/index/catalogs")


def cmd_index_get(args: argparse.Namespace) -> int:
    return invoke_operation(
        args,
        method="GET",
        path="/index/{entity_type}/{entity_id}",
        path_params={"entity_type": args.entity_type, "entity_id": args.entity_id},
        query={"catalog": args.catalog},
    )


def cmd_index_query(args: argparse.Namespace) -> int:
    query = {
        "catalog": args.catalog,
        "size": args.size,
        "sort": args.sort,
        "order": args.order,
        "search_before": args.search_before,
        "search_before_uid": args.search_before_uid,
        "search_after": args.search_after,
        "search_after_uid": args.search_after_uid,
    }
    filters = merged_filters(args)
    if args.method in {"GET", "HEAD"} and filters:
        query["filters"] = filters
        body = None
    elif args.method == "POST":
        body = filters or None
    else:
        body = None
    return invoke_operation(
        args,
        method=args.method,
        path="/index/{entity_type}",
        path_params={"entity_type": args.entity_type},
        query=query,
        json_body=body,
    )


def cmd_index_summary(args: argparse.Namespace) -> int:
    query = {"catalog": args.catalog}
    filters = merged_filters(args)
    if filters:
        query["filters"] = filters
    return invoke_operation(args, method=args.method, path="/index/summary", query=query)


def cmd_manifest_prepare(args: argparse.Namespace) -> int:
    query = {"catalog": args.catalog, "format": args.format}
    filters = merged_filters(args)
    path = "/fetch/manifest/files" if args.xhr else "/manifest/files"
    body = None
    if args.body_mode == "body":
        body = {"catalog": args.catalog, "format": args.format}
        if filters:
            body["filters"] = filters
    elif filters:
        query["filters"] = filters
    return invoke_operation(args, method="PUT", path=path, query=query, json_body=body)


def cmd_manifest_status(args: argparse.Namespace) -> int:
    path = "/fetch/manifest/files/{token}" if args.xhr else "/manifest/files/{token}"
    return invoke_operation(args, method="GET", path=path, path_params={"token": args.token_value})


def cmd_repository_file_url(args: argparse.Namespace) -> int:
    query = {
        "catalog": args.catalog,
        "version": args.version,
        "fileName": args.file_name,
        "wait": args.wait,
        "replica": args.replica,
        "requestIndex": args.request_index,
        "drsUri": args.drs_uri,
        "token": args.reserved_token,
    }
    path = "/fetch/repository/files/{file_uuid}" if args.xhr else "/repository/files/{file_uuid}"
    return invoke_operation(
        args,
        method="GET",
        path=path,
        path_params={"file_uuid": args.file_uuid},
        query=query,
    )


def cmd_repository_sources(args: argparse.Namespace) -> int:
    return invoke_operation(
        args, method="GET", path="/repository/sources", query={"catalog": args.catalog}
    )


def _projects_facets_response(client: ApiClient, catalog: str) -> dict[str, Any]:
    response = client.request("GET", "/index/projects", query={"catalog": catalog, "size": 1})
    payload = response.json()
    if not isinstance(payload, dict):
        raise CliError("Expected JSON from /index/projects")
    return payload


def _summary_response(client: ApiClient, catalog: str) -> dict[str, Any]:
    response = client.request("GET", "/index/summary", query={"catalog": catalog})
    payload = response.json()
    if not isinstance(payload, dict):
        raise CliError("Expected JSON from /index/summary")
    return payload


def _project_detail_response(client: ApiClient, catalog: str, project_id: str) -> dict[str, Any]:
    response = client.request(
        "GET",
        "/index/{entity_type}/{entity_id}",
        path_params={"entity_type": "projects", "entity_id": project_id},
        query={"catalog": catalog},
    )
    payload = response.json()
    if not isinstance(payload, dict):
        raise CliError(f"Expected JSON project detail for {project_id}")
    return payload


def _dataset_query_filters(*, tissue: str | None, cell_type: str | None) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if tissue:
        filters["effectiveOrgan"] = {"is": [tissue]}
    if cell_type:
        filters["selectedCellType"] = {"is": [cell_type]}
    return filters


def _collect_datasets(
    client: ApiClient,
    *,
    catalog: str,
    tissue: str | None,
    cell_type: str | None,
    modality: str | None,
    project_limit: int,
    dataset_limit: int | None,
    sort: str,
    order: str,
) -> tuple[list[dict[str, Any]], int]:
    query = {
        "catalog": catalog,
        "size": project_limit,
        "sort": sort,
        "order": order,
    }
    filters = _dataset_query_filters(tissue=tissue, cell_type=cell_type)
    if filters:
        query["filters"] = filters
    response = client.request("GET", "/index/projects", query=query)
    payload = response.json()
    if not isinstance(payload, dict):
        raise CliError("Expected JSON project query response")
    datasets: list[dict[str, Any]] = []
    examined = 0
    for hit in payload.get("hits", []):
        project_id = hit.get("projects", [{}])[0].get("projectId")
        if not project_id:
            continue
        examined += 1
        detail = _project_detail_response(client, catalog, project_id)
        derived = filter_datasets(derive_datasets(detail), modality=modality)
        for dataset in derived:
            datasets.append(dataset)
            if dataset_limit is not None and len(datasets) >= dataset_limit:
                return datasets, examined
    return datasets, examined


def _find_dataset(
    client: ApiClient, *, catalog: str, project_id: str, dataset_key: str
) -> dict[str, Any]:
    detail = _project_detail_response(client, catalog, project_id)
    for dataset in derive_datasets(detail):
        if dataset["dataset_key"] == dataset_key:
            return dataset
    raise CliError(f"Dataset key {dataset_key!r} not found in project {project_id}")


def cmd_atlas_tissues(args: argparse.Namespace) -> int:
    client = build_client(args)
    summary = _summary_response(client, args.catalog)
    rows = summarize_tissues(summary, limit=args.limit)
    if args.output == "json":
        print_payload(rows, "json")
    else:
        print(
            render_table(
                rows,
                [("tissue", "TISSUE"), ("documents", "PROJECTS"), ("total_cells", "TOTAL CELLS")],
            )
        )
    return 0


def cmd_atlas_cell_types(args: argparse.Namespace) -> int:
    client = build_client(args)
    projects = _projects_facets_response(client, args.catalog)
    rows = summarize_cell_types(projects, limit=args.limit)
    if args.output == "json":
        print_payload(rows, "json")
    else:
        print(render_table(rows, [("cell_type", "CELL TYPE"), ("projects", "PROJECTS")]))
    return 0


def cmd_atlas_modalities(args: argparse.Namespace) -> int:
    client = build_client(args)
    projects = _projects_facets_response(client, args.catalog)
    rows = summarize_modalities(projects)
    if args.output == "json":
        print_payload(rows, "json")
    else:
        print(
            render_table(
                rows,
                [("modality", "MODALITY"), ("signal_count", "SIGNALS"), ("examples", "EXAMPLES")],
            )
        )
    return 0


def cmd_atlas_overview(args: argparse.Namespace) -> int:
    client = build_client(args)
    summary = _summary_response(client, args.catalog)
    projects = _projects_facets_response(client, args.catalog)
    payload = {
        "catalog": args.catalog,
        "counts": {
            "projects": summary.get("projectCount"),
            "specimens": summary.get("specimenCount"),
            "donors": summary.get("donorCount"),
            "files": summary.get("fileCount"),
            "total_file_size": format_bytes(summary.get("totalFileSize")),
        },
        "top_tissues": summarize_tissues(summary, limit=10),
        "top_cell_types": summarize_cell_types(projects, limit=10),
        "modalities": summarize_modalities(projects),
    }
    print_payload(payload, args.output)
    return 0


def cmd_atlas_projects(args: argparse.Namespace) -> int:
    client = build_client(args)
    facets = _projects_facets_response(client, args.catalog)
    filters, note = atlas_project_filters(
        tissue=args.tissue,
        cell_type=args.cell_type,
        modality=args.modality,
        projects_response=facets,
    )
    response = client.request(
        "GET",
        "/index/projects",
        query={
            "catalog": args.catalog,
            "size": args.size,
            "filters": filters,
            "sort": args.sort,
            "order": args.order,
        },
    )
    payload = response_to_display(response, full=args.full, include_headers=args.include_headers)
    if note:
        payload = {"note": note, "result": payload}
    print_payload(payload, args.output)
    return 0 if response.status < 400 else 1


def cmd_dataset_query(args: argparse.Namespace) -> int:
    client = build_client(args)
    datasets, examined = _collect_datasets(
        client,
        catalog=args.catalog,
        tissue=args.tissue,
        cell_type=args.cell_type,
        modality=args.modality,
        project_limit=args.project_limit,
        dataset_limit=args.limit,
        sort=args.sort,
        order=args.order,
    )
    payload = {
        "catalog": args.catalog,
        "query": {"tissue": args.tissue, "cell_type": args.cell_type, "modality": args.modality},
        "projects_examined": examined,
        "datasets": datasets,
    }
    if args.output == "json":
        print_payload(payload, "json")
    else:
        lines = dataset_text_rows(datasets)
        if not lines:
            print("No datasets.")
        else:
            print("\n".join(lines))
    return 0


def cmd_dataset_show(args: argparse.Namespace) -> int:
    client = build_client(args)
    dataset = _find_dataset(
        client, catalog=args.catalog, project_id=args.project_id, dataset_key=args.dataset_key
    )
    if args.output == "json":
        print_payload(dataset, "json")
    else:
        print(dataset_detail_text(dataset))
    return 0


def cmd_dataset_files(args: argparse.Namespace) -> int:
    client = build_client(args)
    dataset = _find_dataset(
        client, catalog=args.catalog, project_id=args.project_id, dataset_key=args.dataset_key
    )
    files = dataset.get("files", [])
    if not files:
        response = client.request(
            "GET",
            "/index/files",
            query={
                "catalog": args.catalog,
                "size": args.limit,
                "filters": {"projectId": {"is": [args.project_id]}},
            },
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise CliError("Expected JSON files query response")
        files = []
        for hit in payload.get("hits", []):
            file_entry = hit.get("files", [{}])[0]
            files.append(
                {
                    "name": file_entry.get("name"),
                    "format": file_entry.get("format"),
                    "size_bytes": int(file_entry.get("size") or 0),
                    "size": format_bytes(file_entry.get("size")),
                    "content_descriptions": file_entry.get("contentDescription") or [],
                    "uuid": file_entry.get("uuid"),
                    "version": file_entry.get("version"),
                    "drs_uri": file_entry.get("drs_uri"),
                    "azul_url": file_entry.get("azul_url"),
                    "accessible": file_entry.get("accessible"),
                }
            )
    if args.output == "json":
        print_payload(files, "json")
    else:
        rows = [
            {
                "name": file_entry.get("name"),
                "format": file_entry.get("format"),
                "size": file_entry.get("size"),
                "description": ", ".join(file_entry.get("content_descriptions", []) or []) or "-",
            }
            for file_entry in files[: args.limit]
        ]
        print(
            render_table(
                rows,
                [
                    ("name", "NAME"),
                    ("format", "FORMAT"),
                    ("size", "SIZE"),
                    ("description", "DESCRIPTION"),
                ],
            )
        )
    return 0


def cmd_dataset_formats(args: argparse.Namespace) -> int:
    client = build_client(args)
    datasets, examined = _collect_datasets(
        client,
        catalog=args.catalog,
        tissue=args.tissue,
        cell_type=args.cell_type,
        modality=args.modality,
        project_limit=args.project_limit,
        dataset_limit=None,
        sort=args.sort,
        order=args.order,
    )
    rows = dataset_format_rows(datasets)
    payload = {
        "catalog": args.catalog,
        "projects_examined": examined,
        "query": {"tissue": args.tissue, "cell_type": args.cell_type, "modality": args.modality},
        "formats": rows,
    }
    if args.output == "json":
        print_payload(payload, "json")
    else:
        print(
            render_table(
                rows,
                [
                    ("modality", "MODALITY"),
                    ("format", "FORMAT"),
                    ("datasets", "DATASETS"),
                    ("total_size", "TOTAL SIZE"),
                ],
            )
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hca",
        description="Self-documenting command line client for the Human Cell Atlas Azul API.",
        epilog="Use `hca explain` for the conceptual model and `hca api operations` for the full raw API surface.",
    )
    add_transport_options(parser)
    subparsers = parser.add_subparsers(dest="command")

    explain = subparsers.add_parser(
        "explain", help="Explain the HCA API mental model and common workflows."
    )
    explain.set_defaults(func=cmd_explain)

    api = subparsers.add_parser(
        "api", help="Inspect or call the raw API surface described by the bundled OpenAPI snapshot."
    )
    api_sub = api.add_subparsers(dest="api_command")

    operations_parser = api_sub.add_parser("operations", help="List all known API operations.")
    add_render_options(operations_parser, default_output="text")
    operations_parser.add_argument(
        "--tag", choices=("Auxiliary", "Index", "Manifests", "Repository")
    )
    operations_parser.set_defaults(func=cmd_api_operations)

    describe_parser = api_sub.add_parser(
        "describe", help="Describe one operation from the bundled OpenAPI metadata."
    )
    add_render_options(describe_parser)
    describe_parser.add_argument("method", help="HTTP method, for example GET or PUT.")
    describe_parser.add_argument(
        "path", help="Exact OpenAPI path, for example /index/{entity_type}."
    )
    describe_parser.set_defaults(func=cmd_api_describe)

    call_parser = api_sub.add_parser(
        "call", help="Call any operation by method and exact OpenAPI path."
    )
    add_render_options(call_parser)
    call_parser.add_argument("method", help="HTTP method.")
    call_parser.add_argument("path", help="Exact OpenAPI path.")
    call_parser.add_argument(
        "--path-param", action="append", default=[], metavar="NAME=VALUE", help="Path parameter."
    )
    call_parser.add_argument(
        "--query-param", action="append", default=[], metavar="NAME=VALUE", help="Query parameter."
    )
    call_parser.add_argument("--body-json", help="Raw JSON request body.")
    call_parser.add_argument("--body-file", help="Path to a JSON request body.")
    call_parser.set_defaults(func=cmd_api_call)

    aux = subparsers.add_parser("aux", help="Auxiliary service endpoints.")
    aux_sub = aux.add_subparsers(dest="aux_command")
    for name, handler, help_text in (
        ("root", cmd_aux_root, "Call GET /."),
        ("swagger-ui", cmd_aux_swagger_ui, "Fetch the Swagger UI HTML."),
        ("swagger-init", cmd_aux_swagger_init, "Fetch the Swagger UI initializer JS."),
        ("openapi", cmd_aux_openapi, "Fetch the live OpenAPI document."),
        ("version", cmd_aux_version, "Fetch the live service version."),
        ("robots", cmd_aux_robots, "Fetch robots.txt."),
    ):
        command_parser = aux_sub.add_parser(name, help=help_text)
        add_render_options(command_parser)
        command_parser.set_defaults(func=handler)
    swagger_file = aux_sub.add_parser(
        "swagger-file", help="Fetch a static Swagger asset by filename."
    )
    add_render_options(swagger_file)
    swagger_file.add_argument("file")
    swagger_file.set_defaults(func=cmd_aux_swagger_file)

    health = subparsers.add_parser("health", help="Health checks.")
    health_sub = health.add_subparsers(dest="kind")
    for kind in ("complete", "basic", "cached", "fast"):
        health_parser = health_sub.add_parser(kind, help=f"Run the {kind} health check.")
        add_render_options(health_parser)
        health_parser.set_defaults(func=cmd_health)
    selective = health_sub.add_parser("selective", help="Run selective health checks by key list.")
    add_render_options(selective)
    selective.add_argument("keys", help="Comma-separated health check keys.")
    selective.set_defaults(func=cmd_health)

    index = subparsers.add_parser("index", help="Browse the indexed HCA entities.")
    index_sub = index.add_subparsers(dest="index_command")

    index_catalogs = index_sub.add_parser("catalogs", help="List available catalogs.")
    add_render_options(index_catalogs)
    index_catalogs.set_defaults(func=cmd_index_catalogs)

    index_get = index_sub.add_parser("get", help="Fetch one entity by type and identifier.")
    add_render_options(index_get)
    add_catalog_option(index_get)
    index_get.add_argument("entity_type", choices=entity_types())
    index_get.add_argument("entity_id")
    index_get.set_defaults(func=cmd_index_get)

    index_query = index_sub.add_parser("query", help="Query bundles, files, projects, or samples.")
    add_render_options(index_query)
    add_catalog_option(index_query)
    add_filter_options(index_query)
    index_query.add_argument("entity_type", choices=entity_types())
    index_query.add_argument("--method", choices=("GET", "POST", "HEAD"), default="GET")
    index_query.add_argument("--size", type=int, default=10)
    index_query.add_argument("--sort", choices=sort_fields(), default=None)
    index_query.add_argument("--order", choices=("asc", "desc"), default=None)
    index_query.add_argument("--search-before")
    index_query.add_argument("--search-before-uid")
    index_query.add_argument("--search-after")
    index_query.add_argument("--search-after-uid")
    index_query.set_defaults(func=cmd_index_query)

    index_summary = index_sub.add_parser(
        "summary", help="Fetch global summary statistics, optionally filtered."
    )
    add_render_options(index_summary)
    add_catalog_option(index_summary)
    add_filter_options(index_summary)
    index_summary.add_argument("--method", choices=("GET", "HEAD"), default="GET")
    index_summary.set_defaults(func=cmd_index_summary)

    manifest = subparsers.add_parser("manifest", help="Manifest preparation endpoints.")
    manifest_sub = manifest.add_subparsers(dest="manifest_command")

    manifest_prepare = manifest_sub.add_parser("prepare", help="Start manifest preparation.")
    add_render_options(manifest_prepare)
    add_catalog_option(manifest_prepare)
    add_filter_options(manifest_prepare)
    manifest_prepare.add_argument("--format", choices=manifest_formats(), default="compact")
    manifest_prepare.add_argument(
        "--xhr", action="store_true", help="Use the XHR /fetch endpoint instead of redirects."
    )
    manifest_prepare.add_argument(
        "--body-mode",
        choices=("query", "body"),
        default="query",
        help="Send manifest parameters as query params or JSON body.",
    )
    manifest_prepare.set_defaults(func=cmd_manifest_prepare)

    manifest_status = manifest_sub.add_parser(
        "status", help="Check the status of a manifest job token."
    )
    add_render_options(manifest_status)
    manifest_status.add_argument("token_value", metavar="TOKEN")
    manifest_status.add_argument(
        "--xhr", action="store_true", help="Use the XHR /fetch endpoint instead of redirects."
    )
    manifest_status.set_defaults(func=cmd_manifest_status)

    repository = subparsers.add_parser("repository", help="Repository-backed file access.")
    repository_sub = repository.add_subparsers(dest="repository_command")

    file_url = repository_sub.add_parser(
        "file-url", help="Get the redirect or XHR metadata for a file download URL."
    )
    add_render_options(file_url)
    add_catalog_option(file_url)
    file_url.add_argument("file_uuid")
    file_url.add_argument(
        "--xhr", action="store_true", help="Use the XHR /fetch endpoint instead of redirects."
    )
    file_url.add_argument("--version")
    file_url.add_argument("--file-name")
    file_url.add_argument("--wait", type=int)
    file_url.add_argument("--replica")
    file_url.add_argument("--request-index", type=int)
    file_url.add_argument("--drs-uri")
    file_url.add_argument("--reserved-token")
    file_url.set_defaults(func=cmd_repository_file_url)

    repository_sources = repository_sub.add_parser(
        "sources", help="List repository sources for a catalog."
    )
    add_render_options(repository_sources)
    add_catalog_option(repository_sources)
    repository_sources.set_defaults(func=cmd_repository_sources)

    atlas = subparsers.add_parser("atlas", help="Atlas-oriented views built on top of the raw API.")
    atlas_sub = atlas.add_subparsers(dest="atlas_command")
    for name, handler, help_text in (
        ("overview", cmd_atlas_overview, "Summarize tissues, cell types, and modalities together."),
        ("tissues", cmd_atlas_tissues, "List top tissues by aggregated cell counts."),
        ("cell-types", cmd_atlas_cell_types, "List top selected cell types from project facets."),
        ("modalities", cmd_atlas_modalities, "Group live facet terms into modality families."),
    ):
        atlas_parser = atlas_sub.add_parser(name, help=help_text)
        add_render_options(atlas_parser, default_output="text")
        add_catalog_option(atlas_parser)
        if name in {"tissues", "cell-types"}:
            atlas_parser.add_argument("--limit", type=int, default=18 if name == "tissues" else 20)
        atlas_parser.set_defaults(func=handler)

    atlas_projects = atlas_sub.add_parser(
        "projects", help="Browse projects through the atlas mental model."
    )
    add_render_options(atlas_projects)
    add_catalog_option(atlas_projects)
    atlas_projects.add_argument("--tissue")
    atlas_projects.add_argument("--cell-type")
    atlas_projects.add_argument(
        "--modality",
        choices=tuple(
            sorted({"transcriptomics", "proteomics", "spatial", "epigenomics", "imaging"})
        ),
    )
    atlas_projects.add_argument("--size", type=int, default=10)
    atlas_projects.add_argument("--sort", choices=sort_fields(), default="projectTitle")
    atlas_projects.add_argument("--order", choices=("asc", "desc"), default="asc")
    atlas_projects.set_defaults(func=cmd_atlas_projects)

    dataset = subparsers.add_parser(
        "dataset", help="Derived dataset-centric views built on top of project detail metadata."
    )
    dataset_sub = dataset.add_subparsers(dest="dataset_command")

    dataset_query = dataset_sub.add_parser(
        "query", help="Find derived datasets by tissue, cell type, and modality."
    )
    add_render_options(dataset_query, default_output="text")
    add_catalog_option(dataset_query)
    dataset_query.add_argument("--tissue")
    dataset_query.add_argument("--cell-type")
    dataset_query.add_argument(
        "--modality",
        choices=tuple(
            sorted({"transcriptomics", "proteomics", "spatial", "epigenomics", "imaging"})
        ),
    )
    dataset_query.add_argument(
        "--project-limit", type=int, default=10, help="How many matching projects to inspect."
    )
    dataset_query.add_argument(
        "--limit", type=int, default=10, help="Maximum derived datasets to return."
    )
    dataset_query.add_argument("--sort", choices=sort_fields(), default="projectTitle")
    dataset_query.add_argument("--order", choices=("asc", "desc"), default="asc")
    dataset_query.set_defaults(func=cmd_dataset_query)

    dataset_show = dataset_sub.add_parser(
        "show", help="Show detailed metadata for one derived dataset."
    )
    add_render_options(dataset_show, default_output="text")
    add_catalog_option(dataset_show)
    dataset_show.add_argument("project_id")
    dataset_show.add_argument("dataset_key")
    dataset_show.set_defaults(func=cmd_dataset_show)

    dataset_files = dataset_sub.add_parser("files", help="List files for one derived dataset.")
    add_render_options(dataset_files, default_output="text")
    add_catalog_option(dataset_files)
    dataset_files.add_argument("project_id")
    dataset_files.add_argument("dataset_key")
    dataset_files.add_argument("--limit", type=int, default=20)
    dataset_files.set_defaults(func=cmd_dataset_files)

    dataset_formats = dataset_sub.add_parser(
        "formats", help="Summarize which file formats correspond to observed modalities."
    )
    add_render_options(dataset_formats, default_output="text")
    add_catalog_option(dataset_formats)
    dataset_formats.add_argument("--tissue")
    dataset_formats.add_argument("--cell-type")
    dataset_formats.add_argument(
        "--modality",
        choices=tuple(
            sorted({"transcriptomics", "proteomics", "spatial", "epigenomics", "imaging"})
        ),
    )
    dataset_formats.add_argument("--project-limit", type=int, default=10)
    dataset_formats.add_argument("--sort", choices=sort_fields(), default="projectTitle")
    dataset_formats.add_argument("--order", choices=("asc", "desc"), default="asc")
    dataset_formats.set_defaults(func=cmd_dataset_formats)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    command_help_attr = {
        "api": "api_command",
        "aux": "aux_command",
        "health": "kind",
        "index": "index_command",
        "manifest": "manifest_command",
        "repository": "repository_command",
        "atlas": "atlas_command",
        "dataset": "dataset_command",
    }
    help_attr = command_help_attr.get(args.command)
    if help_attr and getattr(args, help_attr) is None:
        next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        ).choices[args.command].print_help()
        return 0
    try:
        func = cast(Callable[[argparse.Namespace], int], args.func)
        return func(args)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
