from __future__ import annotations

import re
from typing import Any

MODALITY_PATTERNS: dict[str, tuple[str, ...]] = {
    "transcriptomics": (
        r"\brna\b",
        r"gene expression",
        r"transcription",
        r"smart-?seq",
        r"drop-?seq",
        r"whole transcriptome",
        r"\bvisium\b",
    ),
    "proteomics": (
        r"cite",
        r"protein",
        r"antibody",
        r"feature barcode",
        r"abseq",
    ),
    "spatial": (
        r"spatial",
        r"visium",
        r"merfish",
        r"xenium",
        r"seqfish",
    ),
    "epigenomics": (
        r"atac",
        r"chromatin",
    ),
    "imaging": (
        r"microscopy",
        r"\bimage\b",
    ),
}


def _normalize_label(label: str | None) -> str | None:
    if label is None:
        return None
    clean = str(label).strip()
    if not clean:
        return None
    return clean.casefold()


def summarize_tissues(summary_response: dict[str, Any], *, limit: int = 18) -> list[dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}
    for item in summary_response.get("cellCountSummaries", []):
        raw_label = None
        if item.get("organType"):
            raw_label = item["organType"][0]
        normalized = _normalize_label(raw_label)
        if normalized is None:
            continue
        existing = aggregated.setdefault(
            normalized,
            {
                "tissue": str(raw_label),
                "documents": 0,
                "total_cells": 0,
            },
        )
        existing["documents"] += int(item.get("countOfDocsWithOrganType") or 0)
        existing["total_cells"] += int(item.get("totalCellCountByOrgan") or 0)
    rows = sorted(
        aggregated.values(),
        key=lambda row: (-row["total_cells"], -row["documents"], row["tissue"].lower()),
    )
    return rows[:limit]


def summarize_cell_types(
    projects_response: dict[str, Any], *, limit: int = 20
) -> list[dict[str, Any]]:
    rows = []
    for term in (
        projects_response.get("termFacets", {}).get("selectedCellType", {}).get("terms", [])
    ):
        label = term.get("term")
        if label is None:
            continue
        rows.append({"cell_type": label, "projects": term.get("count", 0)})
    rows.sort(key=lambda row: (-row["projects"], row["cell_type"].lower()))
    return rows[:limit]


def _facet_terms(projects_response: dict[str, Any], facet_name: str) -> list[dict[str, Any]]:
    return list(projects_response.get("termFacets", {}).get(facet_name, {}).get("terms", []))


def modality_matches(
    projects_response: dict[str, Any], category: str
) -> dict[str, list[dict[str, Any]]]:
    patterns = MODALITY_PATTERNS.get(category.lower())
    if not patterns:
        raise ValueError(f"Unsupported modality category: {category}")
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    matches: dict[str, list[dict[str, Any]]] = {}
    for facet_name in ("libraryConstructionApproach", "assayType", "contentDescription"):
        facet_matches = []
        for term in _facet_terms(projects_response, facet_name):
            label = term.get("term")
            if label is None:
                continue
            if any(pattern.search(str(label)) for pattern in compiled):
                facet_matches.append({"term": label, "count": int(term.get("count", 0))})
        if facet_matches:
            facet_matches.sort(key=lambda row: (-row["count"], str(row["term"]).lower()))
            matches[facet_name] = facet_matches
    return matches


def summarize_modalities(
    projects_response: dict[str, Any], *, limit_terms: int = 6
) -> list[dict[str, Any]]:
    rows: list[dict[str, str | int]] = []
    for category in MODALITY_PATTERNS:
        matches = modality_matches(projects_response, category)
        total = 0
        top_terms = []
        for facet_name, items in matches.items():
            total += sum(int(item["count"]) for item in items)
            for item in items[:limit_terms]:
                top_terms.append(f"{facet_name}:{item['term']}")
        rows.append(
            {
                "modality": category,
                "matched_terms": len(top_terms),
                "signal_count": total,
                "examples": ", ".join(top_terms[:limit_terms]) or "-",
            }
        )

    def sort_key(row: dict[str, str | int]) -> tuple[int, str]:
        return (-int(row["signal_count"]), str(row["modality"]))

    rows.sort(key=sort_key)
    return rows


def atlas_project_filters(
    *,
    tissue: str | None,
    cell_type: str | None,
    modality: str | None,
    projects_response: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    filters: dict[str, Any] = {}
    note = None
    if tissue:
        filters["effectiveOrgan"] = {"is": [tissue]}
    if cell_type:
        filters["selectedCellType"] = {"is": [cell_type]}
    if modality:
        matches = modality_matches(projects_response, modality)
        for field_name in ("libraryConstructionApproach", "assayType", "contentDescription"):
            if matches.get(field_name):
                filters[field_name] = {"is": [item["term"] for item in matches[field_name]]}
                note = f"Mapped modality {modality!r} to {field_name} values discovered from live facet terms."
                break
        if note is None:
            note = (
                f"No live facet terms matched modality {modality!r}; modality filter was skipped."
            )
    return filters, note
