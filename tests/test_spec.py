from hca_cli.spec import entity_types, filter_fields, operations


def test_operation_count() -> None:
    assert len(operations()) == 26


def test_entity_types() -> None:
    assert entity_types() == ["bundles", "files", "projects", "samples"]


def test_filter_field_inventory() -> None:
    fields = filter_fields()
    assert "effectiveOrgan" in fields
    assert "selectedCellType" in fields
    assert "libraryConstructionApproach" in fields
