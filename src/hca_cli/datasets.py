from __future__ import annotations

import json
import re
from hashlib import sha1
from typing import Any, Iterable

from hca_cli.atlas import MODALITY_PATTERNS
from hca_cli.formatting import format_bytes

FORMAT_MODALITY_HINTS: dict[str, tuple[str, ...]] = {
    "h5": ("transcriptomics",),
    "h5ad": ("transcriptomics",),
    "loom": ("transcriptomics",),
    "mtx": ("transcriptomics",),
    "mtx.gz": ("transcriptomics",),
    "rds": ("transcriptomics",),
    "csv": ("transcriptomics",),
    "csv.gz": ("transcriptomics",),
    "tsv": ("transcriptomics",),
    "tsv.gz": ("transcriptomics",),
    "fcs": ("proteomics",),
}

MODALITY_ORDER = ("transcriptomics", "proteomics", "spatial", "epigenomics", "imaging")


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def _unique_strings(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _flatten_age(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        raw_value = value.get("value")
        unit = value.get("unit")
        if raw_value is None:
            return None
        if unit:
            return f"{raw_value} {unit}"
        return str(raw_value)
    return str(value)


def summarize_age(donor_organisms: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    ages: list[str] = []
    development_stages: list[str] = []
    for donor in donor_organisms:
        for item in donor.get("organismAge", []):
            flattened = _flatten_age(item)
            if flattened is not None:
                ages.append(flattened)
        development_stages.extend(donor.get("developmentStage", []))
    return _unique_strings(ages), _unique_strings(development_stages)


def infer_modalities(*signal_groups: Iterable[Any]) -> list[str]:
    signals = []
    for group in signal_groups:
        for item in group:
            if item is None:
                continue
            signals.append(str(item))
    matches: set[str] = set()
    for signal in signals:
        lowered = signal.casefold()
        for modality, patterns in MODALITY_PATTERNS.items():
            if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in patterns):
                matches.add(modality)
        if lowered in FORMAT_MODALITY_HINTS:
            matches.update(FORMAT_MODALITY_HINTS[lowered])
    return [modality for modality in MODALITY_ORDER if modality in matches]


def _content_descriptions(files: list[dict[str, Any]]) -> list[str]:
    descriptions: list[str] = []
    for file_entry in files:
        descriptions.extend(file_entry.get("contentDescription", []) or [])
    return _unique_strings(descriptions)


def _formats(files: list[dict[str, Any]]) -> list[str]:
    return _unique_strings(file_entry.get("format") for file_entry in files)


def _total_size(files: list[dict[str, Any]]) -> int:
    return int(sum(int(file_entry.get("size") or 0) for file_entry in files))


def _matrix_cell_count(files: list[dict[str, Any]]) -> int | None:
    values: list[int] = []
    for file_entry in files:
        raw_value = file_entry.get("matrixCellCount")
        if raw_value is None:
            continue
        values.append(int(raw_value))
    if not values:
        return None
    return sum(values)


def _dataset_key(source: str, path: list[tuple[str, str]]) -> str:
    signature = json.dumps({"source": source, "path": path}, sort_keys=True)
    digest = sha1(signature.encode("utf-8")).hexdigest()[:8]
    human = "-".join(_slugify(value) for _, value in path if value)
    prefix = _slugify(source)
    if human:
        return f"{prefix}-{human[:48]}-{digest}"
    return f"{prefix}-{digest}"


def _path_value(path: list[tuple[str, str]], key: str) -> str | None:
    for path_key, value in path:
        if path_key == key:
            return value
    return None


def _listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _leaf_dataset(
    project_detail: dict[str, Any],
    *,
    source: str,
    path: list[tuple[str, str]],
    files: list[dict[str, Any]],
) -> dict[str, Any]:
    project = project_detail["projects"][0]
    donor_organisms = project_detail.get("donorOrganisms", [])
    ages, development_stages = summarize_age(donor_organisms)
    species = _path_value(path, "genusSpecies")
    development_stage = _path_value(path, "developmentStage")
    organ = _path_value(path, "organ")
    library_construction = _path_value(path, "libraryConstructionApproach")
    formats = _formats(files)
    descriptions = _content_descriptions(files)
    modalities = infer_modalities(
        [library_construction, species, development_stage, organ],
        descriptions,
        formats,
    )
    dataset = {
        "project_id": project["projectId"],
        "project_title": project["projectTitle"],
        "dataset_key": _dataset_key(source, path),
        "dataset_label": " / ".join(value for _, value in path if value) or project["projectTitle"],
        "source": source,
        "species": species,
        "organ": organ,
        "development_stage": development_stage,
        "library_construction_approach": library_construction,
        "ages": ages,
        "development_stages": development_stages,
        "modalities": modalities,
        "primary_modality": modalities[0] if modalities else "unknown",
        "formats": formats,
        "content_descriptions": descriptions,
        "file_count": len(files),
        "size_bytes": _total_size(files),
        "size": format_bytes(_total_size(files)),
        "matrix_cell_count": _matrix_cell_count(files),
        "files": [
            {
                "name": file_entry.get("name"),
                "format": file_entry.get("format"),
                "size_bytes": int(file_entry.get("size") or 0),
                "size": format_bytes(file_entry.get("size")),
                "content_descriptions": _unique_strings(
                    file_entry.get("contentDescription", []) or []
                ),
                "uuid": file_entry.get("uuid"),
                "version": file_entry.get("version"),
                "drs_uri": file_entry.get("drs_uri"),
                "azul_url": file_entry.get("azul_url"),
                "accessible": file_entry.get("accessible"),
            }
            for file_entry in files
        ],
    }
    dataset["age_summary"] = (
        "; ".join(dataset["ages"][:3])
        if dataset["ages"]
        else "; ".join(dataset["development_stages"][:3])
    )
    return dataset


def _walk_grouped_file_tree(
    node: Any, path: list[tuple[str, str]] | None = None
) -> list[tuple[list[tuple[str, str]], list[dict[str, Any]]]]:
    path = path or []
    if (
        isinstance(node, list)
        and node
        and all(isinstance(item, dict) and "name" in item for item in node)
    ):
        return [(path, node)]
    results: list[tuple[list[tuple[str, str]], list[dict[str, Any]]]] = []
    if isinstance(node, dict):
        for dimension, options in node.items():
            if not isinstance(options, dict):
                continue
            for option, child in options.items():
                results.extend(
                    _walk_grouped_file_tree(child, path + [(str(dimension), str(option))])
                )
    return results


def _fallback_dataset(project_detail: dict[str, Any]) -> dict[str, Any]:
    project = project_detail["projects"][0]
    donor_organisms = project_detail.get("donorOrganisms", [])
    ages, development_stages = summarize_age(donor_organisms)
    formats = _unique_strings(
        summary.get("format") for summary in project_detail.get("fileTypeSummaries", [])
    )
    descriptions: list[str] = []
    size_bytes = 0
    matrix_cell_count = 0
    for summary in project_detail.get("fileTypeSummaries", []):
        descriptions.extend(summary.get("contentDescription", []) or [])
        size_bytes += int(summary.get("totalSize") or 0)
        matrix_cell_count += int(summary.get("matrixCellCount") or 0)
    organ_values = []
    for sample in project_detail.get("samples", []):
        organ_values.extend(_listify(sample.get("organ")))
        organ_values.extend(_listify(sample.get("effectiveOrgan")))
    modalities = infer_modalities(descriptions, formats)
    return {
        "project_id": project["projectId"],
        "project_title": project["projectTitle"],
        "dataset_key": _dataset_key("project-summary", [("project", project["projectTitle"])]),
        "dataset_label": project["projectTitle"],
        "source": "project-summary",
        "species": ", ".join(
            _unique_strings(
                value for donor in donor_organisms for value in donor.get("genusSpecies", [])
            )
        )
        or None,
        "organ": ", ".join(_unique_strings(organ_values)) or None,
        "development_stage": development_stages[0] if development_stages else None,
        "library_construction_approach": None,
        "ages": ages,
        "development_stages": development_stages,
        "modalities": modalities,
        "primary_modality": modalities[0] if modalities else "unknown",
        "formats": formats,
        "content_descriptions": _unique_strings(descriptions),
        "file_count": int(
            sum(
                int(summary.get("count") or 0)
                for summary in project_detail.get("fileTypeSummaries", [])
            )
        ),
        "size_bytes": size_bytes,
        "size": format_bytes(size_bytes),
        "matrix_cell_count": matrix_cell_count or None,
        "files": [],
        "age_summary": "; ".join(ages[:3]) if ages else "; ".join(development_stages[:3]),
    }


def derive_datasets(project_detail: dict[str, Any]) -> list[dict[str, Any]]:
    datasets: list[dict[str, Any]] = []
    for source_name in ("contributedAnalyses", "matrices"):
        grouped = project_detail.get("projects", [{}])[0].get(source_name, {})
        for path, files in _walk_grouped_file_tree(grouped):
            datasets.append(
                _leaf_dataset(project_detail, source=source_name, path=path, files=files)
            )
    if datasets:
        return datasets
    return [_fallback_dataset(project_detail)]


def filter_datasets(
    datasets: list[dict[str, Any]],
    *,
    modality: str | None = None,
) -> list[dict[str, Any]]:
    if modality is None:
        return datasets
    filtered = [dataset for dataset in datasets if modality in dataset.get("modalities", [])]
    return filtered


def dataset_format_rows(datasets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated: dict[tuple[str, str], dict[str, Any]] = {}
    for dataset in datasets:
        modality = dataset.get("primary_modality", "unknown")
        for fmt in dataset.get("formats", []):
            key = (modality, fmt)
            row = aggregated.setdefault(
                key,
                {"modality": modality, "format": fmt, "datasets": 0, "total_size_bytes": 0},
            )
            row["datasets"] += 1
            row["total_size_bytes"] += int(dataset.get("size_bytes") or 0)
    rows = list(aggregated.values())
    for row in rows:
        row["total_size"] = format_bytes(row["total_size_bytes"])
    rows.sort(key=lambda row: (row["modality"], row["format"]))
    return rows


def dataset_text_rows(datasets: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for dataset in datasets:
        modalities = ", ".join(dataset["modalities"]) if dataset["modalities"] else "unknown"
        formats = ", ".join(dataset["formats"][:4]) if dataset["formats"] else "-"
        if len(dataset["formats"]) > 4:
            formats += ", ..."
        lines.extend(
            [
                f"{dataset['project_id']}  {dataset['dataset_key']}",
                f"  {dataset['project_title']}",
                f"  modality={modalities}  organ={dataset.get('organ') or '-'}  age={dataset.get('age_summary') or '-'}  formats={formats}  size={dataset['size']}",
            ]
        )
    return lines


def dataset_detail_text(dataset: dict[str, Any]) -> str:
    lines = [
        f"Project: {dataset['project_title']} ({dataset['project_id']})",
        f"Dataset: {dataset['dataset_key']}",
        f"Label: {dataset['dataset_label']}",
        f"Source: {dataset['source']}",
        f"Modality: {', '.join(dataset['modalities']) if dataset['modalities'] else 'unknown'}",
        f"Species: {dataset.get('species') or '-'}",
        f"Organ: {dataset.get('organ') or '-'}",
        f"Development stage: {dataset.get('development_stage') or '-'}",
        f"Age: {dataset.get('age_summary') or '-'}",
        f"Library construction approach: {dataset.get('library_construction_approach') or '-'}",
        f"Formats: {', '.join(dataset['formats']) if dataset['formats'] else '-'}",
        f"Content descriptions: {', '.join(dataset['content_descriptions']) if dataset['content_descriptions'] else '-'}",
        f"Files: {dataset['file_count']}",
        f"Total size: {dataset['size']}",
        f"Matrix cells: {dataset.get('matrix_cell_count') or '-'}",
    ]
    return "\n".join(lines)
