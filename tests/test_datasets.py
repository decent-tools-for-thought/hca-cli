from hca_cli.datasets import dataset_format_rows, derive_datasets, filter_datasets


def test_derive_dataset_from_contributed_analyses() -> None:
    payload = {
        "projects": [
            {
                "projectId": "project-1",
                "projectTitle": "Example Project",
                "contributedAnalyses": {
                    "genusSpecies": {
                        "Homo sapiens": {
                            "organ": {
                                "lung": {
                                    "libraryConstructionApproach": {
                                        "CITE-seq": [
                                            {
                                                "name": "lung.h5ad",
                                                "format": "h5ad",
                                                "size": 1024,
                                                "contentDescription": [
                                                    "Gene expression matrix",
                                                    "cell surface protein profiling",
                                                ],
                                                "uuid": "file-1",
                                                "version": "v1",
                                                "drs_uri": "drs://example",
                                                "azul_url": "https://example",
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                },
                "matrices": {},
            }
        ],
        "donorOrganisms": [
            {
                "organismAge": [{"value": "30-39", "unit": "year"}],
                "developmentStage": ["human adult stage"],
                "genusSpecies": ["Homo sapiens"],
            }
        ],
        "samples": [{"organ": ["lung"]}],
        "fileTypeSummaries": [],
    }
    datasets = derive_datasets(payload)
    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset["project_id"] == "project-1"
    assert dataset["primary_modality"] == "transcriptomics"
    assert "proteomics" in dataset["modalities"]
    assert dataset["formats"] == ["h5ad"]
    assert dataset["size_bytes"] == 1024
    assert dataset["organ"] == "lung"


def test_filter_datasets_by_modality() -> None:
    datasets = [
        {
            "modalities": ["transcriptomics"],
            "primary_modality": "transcriptomics",
            "formats": ["h5"],
            "size_bytes": 10,
        },
        {
            "modalities": ["proteomics"],
            "primary_modality": "proteomics",
            "formats": ["fcs"],
            "size_bytes": 20,
        },
    ]
    filtered = filter_datasets(datasets, modality="proteomics")
    assert filtered == [datasets[1]]


def test_dataset_format_rows_aggregate() -> None:
    rows = dataset_format_rows(
        [
            {"primary_modality": "transcriptomics", "formats": ["h5ad", "loom"], "size_bytes": 100},
            {"primary_modality": "transcriptomics", "formats": ["h5ad"], "size_bytes": 50},
        ]
    )
    assert {
        "modality": "transcriptomics",
        "format": "h5ad",
        "datasets": 2,
        "total_size_bytes": 150,
        "total_size": "150 B",
    } in rows
