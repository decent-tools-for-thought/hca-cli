import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "packaging" in item.nodeid:
            item.add_marker(pytest.mark.packaging_smoke)
            continue
        if "contract" in item.nodeid:
            item.add_marker(pytest.mark.contract)
            continue
        item.add_marker(pytest.mark.unit)
