# hca-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/hca-cli?sort=semver)](https://github.com/decent-tools-for-thought/hca-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-0BSD-green)

Self-documenting command-line client for the Human Cell Atlas Azul API.

> [!IMPORTANT]
> This codebase is largely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Why This Exists

- Expose the HCA API as a shell-friendly CLI.
- Keep both raw API access and higher-level atlas views available.
- Make common tissue, cell type, and modality workflows easy to script.

## Install

```bash
uv tool install .
hca --help
```

For local development:

```bash
uv sync --group dev
uv run hca --help
```

## Quick Start

Discover the API:

```bash
hca explain
hca api operations
hca api describe GET /index/catalogs
```

Explore the atlas:

```bash
hca index catalogs
hca atlas tissues
hca dataset query --tissue lung --modality transcriptomics --limit 5
```

## Authentication

By default the CLI talks to `https://service.azul.data.humancellatlas.org`.

- Set `HCA_API_BEARER_TOKEN` to send a bearer token.
- Use `--base-url` to override the target service.
- Use `--follow-redirects` when you want manifest or repository redirects followed automatically.

## Development

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest -m "unit or packaging_smoke"
```

## Credits

This client is built on the Human Cell Atlas data platform, especially the Azul API layer. Credit goes to the Human Cell Atlas project and its maintainers for the upstream data service, schema, and documentation.
