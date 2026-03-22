# hca-cli

`hca-cli` is a self-documenting command line client for the Human Cell Atlas Azul API.

It exposes the raw API, adds command help sourced from a bundled OpenAPI snapshot, and provides atlas-oriented views for tissues, cell types, and major data modalities.

## Install

```bash
uv tool install .
```

To install from PyPI once published:

```bash
uv tool install hca-cli
```

For local development:

```bash
uv sync --dev
uv run hca --help
```

## Auth And Config

By default the CLI talks to `https://service.azul.data.humancellatlas.org`.

- Set `HCA_API_BEARER_TOKEN` to send an `Authorization: Bearer ...` header on every request.
- Override the target service with `--base-url`.
- Adjust request timing with `--timeout`.
- Pass `--follow-redirects` when you want the CLI to follow manifest or repository redirects instead of showing the redirect response metadata.

Examples:

```bash
export HCA_API_BEARER_TOKEN="..."
hca --timeout 30 index catalogs
hca --base-url https://service.azul.data.humancellatlas.org health basic
```

## Smoke Usage

These commands are the intended quick checks after install:

```bash
hca --help
hca explain
hca index catalogs
hca api describe GET /index/catalogs
```

## Releases

Tagging `v<version>` publishes Python distribution artifacts built from the tagged commit on GitHub.

## Start Here

```bash
hca explain
hca api operations
hca index catalogs
hca index query projects --filter effectiveOrgan=lung --size 5
hca atlas tissues
hca dataset query --tissue lung --modality transcriptomics --limit 5
hca dataset formats --modality transcriptomics --project-limit 10
```

## Design Notes

- The full raw API is reachable through `hca api call METHOD PATH`.
- Common workflows have dedicated commands under `index`, `manifest`, `repository`, `health`, and `atlas`.
- Dataset-first workflows are available under `dataset`.
- Large low-value lists are compacted by default.
  Use `--full` to disable compaction.
- Complex filters can be passed with `--filters-json` or `--filters-file`.
- Every command can emit JSON, while the higher-level `atlas` and `dataset` commands default to human-readable text.

## Atlas Layer

The raw HCA API is index-oriented. The `atlas` commands add the mental model from the HCA body/biological-network view:

- `hca atlas tissues` uses `/index/summary` cell-count summaries.
- `hca atlas cell-types` derives cell types from live project facets.
- `hca atlas modalities` groups live facet terms into modality families such as transcriptomics and proteomics.
- `hca atlas projects` maps tissue, cell type, and modality choices back onto raw project filters.

## Dataset Layer

The live HCA API does not expose a first-class dataset entity, so the CLI derives one from project detail metadata.

- `hca dataset query` finds dataset-like units for a modality-first workflow.
- `hca dataset show PROJECT_ID DATASET_KEY` assembles metadata such as size, age, formats, and modality before download.
- `hca dataset files PROJECT_ID DATASET_KEY` lists the concrete files for a dataset-like unit.
- `hca dataset formats` summarizes which file formats are observed for which modalities.

## Updating the OpenAPI Snapshot

```bash
uv run python tools/update_openapi_summary.py
```

This refreshes the bundled metadata snapshot used for help text and raw-operation discovery.

## Quality Checks

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest -m "unit or packaging_smoke"
```
