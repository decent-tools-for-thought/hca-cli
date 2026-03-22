from hca_cli.atlas import (
    atlas_project_filters,
    summarize_cell_types,
    summarize_modalities,
    summarize_tissues,
)


def test_summarize_tissues_normalizes_case() -> None:
    payload = {
        "cellCountSummaries": [
            {"organType": ["brain"], "countOfDocsWithOrganType": 2, "totalCellCountByOrgan": 100},
            {"organType": ["Brain"], "countOfDocsWithOrganType": 1, "totalCellCountByOrgan": 50},
            {"organType": [None], "countOfDocsWithOrganType": 9, "totalCellCountByOrgan": 999},
        ]
    }
    rows = summarize_tissues(payload)
    assert rows == [{"tissue": "brain", "documents": 3, "total_cells": 150}]


def test_summarize_cell_types_skips_null() -> None:
    payload = {
        "termFacets": {
            "selectedCellType": {
                "terms": [
                    {"term": None, "count": 10},
                    {"term": "neuron", "count": 4},
                    {"term": "B cell", "count": 8},
                ]
            }
        }
    }
    rows = summarize_cell_types(payload)
    assert rows[0] == {"cell_type": "B cell", "projects": 8}
    assert len(rows) == 2


def test_modality_mapping_prefers_library_construction() -> None:
    payload = {
        "termFacets": {
            "libraryConstructionApproach": {
                "terms": [
                    {"term": "CITE-seq", "count": 7},
                    {"term": "10x 3' transcription profiling", "count": 11},
                ]
            },
            "assayType": {"terms": []},
            "contentDescription": {"terms": []},
        }
    }
    filters, note = atlas_project_filters(
        tissue="lung", cell_type="T cell", modality="proteomics", projects_response=payload
    )
    assert filters["effectiveOrgan"] == {"is": ["lung"]}
    assert filters["selectedCellType"] == {"is": ["T cell"]}
    assert filters["libraryConstructionApproach"] == {"is": ["CITE-seq"]}
    assert "Mapped modality" in note
    modality_rows = summarize_modalities(payload)
    assert modality_rows[0]["signal_count"] >= 7
