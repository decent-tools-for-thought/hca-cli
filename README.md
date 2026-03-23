<div align="center">

# hca-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/hca-cli?sort=semver&color=0f766e)](https://github.com/decent-tools-for-thought/hca-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-0ea5e9)
![License](https://img.shields.io/badge/license-0BSD-14b8a6)

Self-documenting command-line client for exploring the Human Cell Atlas Azul API, atlas views, and derived dataset workflows.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
- [Install](#install)
- [Functionality](#functionality)
- [Authentication And Transport](#authentication-and-transport)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install
$$\color{#0EA5E9}Install \space \color{#14B8A6}Tool$$

```bash
uv tool install .    # install the CLI
hca --help           # inspect available commands
```

## Functionality
$$\color{#0EA5E9}API \space \color{#14B8A6}Discovery$$
- `hca explain`: print the API mental model and common workflows.
- `hca api operations`: list all known operations from the bundled OpenAPI snapshot.
- `hca api describe METHOD PATH`: inspect one exact OpenAPI operation with parameters and request-body metadata.
- `hca api call METHOD PATH`: call any exact OpenAPI path with path parameters, query parameters, and JSON body input.

$$\color{#0EA5E9}Aux \space \color{#14B8A6}Endpoints$$
- `hca aux root`: fetch `GET /`.
- `hca aux swagger-ui`: fetch the live Swagger UI HTML.
- `hca aux swagger-init`: fetch the Swagger initializer JavaScript.
- `hca aux swagger-file <file>`: fetch any named Swagger asset.
- `hca aux openapi`: fetch the live OpenAPI document.
- `hca aux version`: fetch the live service version.
- `hca aux robots`: fetch `robots.txt`.

$$\color{#0EA5E9}Health \space \color{#14B8A6}Checks$$
- `hca health complete`: run the complete health check.
- `hca health basic`: run the basic health check.
- `hca health cached`: run the cached health check.
- `hca health fast`: run the fast health check.
- `hca health selective <keys>`: run a comma-separated subset of health checks.

$$\color{#0EA5E9}Index \space \color{#14B8A6}Browse$$
- `hca index catalogs`: list available catalogs.
- `hca index get <entity-type> <entity-id>`: fetch one bundle, file, project, or sample by identifier.
- `hca index query <entity-type>`: query indexed bundles, files, projects, or samples with exact filters, range filters, JSON filters, paging cursors, size limits, sorting, and `GET`/`POST`/`HEAD` selection.
- `hca index summary`: fetch global summary statistics, optionally filtered.

$$\color{#0EA5E9}File \space \color{#14B8A6}Access$$
- `hca manifest prepare`: start manifest generation with filter input, format selection, and query-vs-body request modes.
- `hca manifest prepare --xhr`: use the XHR-style `/fetch` endpoint instead of redirect-based behavior.
- `hca manifest status <token>`: inspect a manifest job token.
- `hca repository file-url <file-uuid>`: resolve redirect or XHR metadata for a repository-backed file URL.
- `hca repository file-url`: supports version, filename, wait, replica, request index, DRS URI, and reserved-token query parameters.
- `hca repository sources`: list repository sources for a catalog.

$$\color{#0EA5E9}Atlas \space \color{#14B8A6}Views$$
- `hca atlas overview`: summarize counts, tissues, cell types, and modalities together.
- `hca atlas tissues`: list top tissues by aggregated cell counts.
- `hca atlas cell-types`: list top selected cell types from project facets.
- `hca atlas modalities`: group live facet terms into modality families.
- `hca atlas projects`: browse projects through atlas-oriented filters for tissue, cell type, and modality.

$$\color{#0EA5E9}Dataset \space \color{#14B8A6}Views$$
- `hca dataset query`: derive dataset-like units from project metadata and filter them by tissue, cell type, and modality.
- `hca dataset show <project-id> <dataset-key>`: show detailed metadata for one derived dataset.
- `hca dataset files <project-id> <dataset-key>`: list files for one derived dataset, falling back to project-scoped file queries when needed.
- `hca dataset formats`: summarize observed file formats by modality across derived datasets.

$$\color{#0EA5E9}Output \space \color{#14B8A6}Controls$$
- Most commands support `--output json|text`.
- Most fetch/query commands support `--full` to disable response elision.
- Most fetch/query commands support `--include-headers` to include selected response headers.
- Redirect-oriented commands support `--follow-redirects` when you want the client to follow redirects instead of showing redirect metadata.

## Authentication And Transport
$$\color{#0EA5E9}Access \space \color{#14B8A6}Setup$$

By default the CLI targets `https://service.azul.data.humancellatlas.org`.

- Set `HCA_API_BEARER_TOKEN` or pass `--token` to send a bearer token.
- Use `--base-url` to target another Azul deployment.
- Use `--timeout` to control HTTP timeouts.

## Quick Start
$$\color{#0EA5E9}Try \space \color{#14B8A6}Browse$$

```bash
hca explain                                      # print the API mental model
hca api operations                               # list bundled operations
hca api describe GET /index/catalogs             # inspect one raw endpoint

hca index catalogs                               # list live catalogs
hca atlas tissues                                # summarize top tissues
hca dataset query --tissue lung --modality transcriptomics --limit 5    # derive dataset-like views
```

## Credits

This client is built for the Human Cell Atlas data platform and is not affiliated with the Human Cell Atlas project.

Credit goes to the Human Cell Atlas maintainers for the Azul API, schemas, data service design, and upstream documentation this tool builds on.
