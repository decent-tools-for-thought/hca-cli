from hca_cli.filters import merge_filters


def test_merge_filters_supports_exact_and_range() -> None:
    payload = merge_filters(
        filter_assignments=["effectiveOrgan=lung,brain", "selectedCellType=T cell"],
        within_assignments=["cellCount=10..20"],
    )
    assert payload == {
        "effectiveOrgan": {"is": ["lung", "brain"]},
        "selectedCellType": {"is": ["T cell"]},
        "cellCount": {"within": [[10, 20]]},
    }
