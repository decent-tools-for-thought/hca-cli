from hca_cli.formatting import compact_payload


def test_compacts_repository_sources() -> None:
    payload = {
        "catalogs": {
            "dcp57": {
                "plugins": {
                    "repository": {
                        "sources": [f"source-{index}" for index in range(8)]
                    }
                }
            }
        }
    }
    compacted = compact_payload(payload)
    sources = compacted["catalogs"]["dcp57"]["plugins"]["repository"]["sources"]
    assert sources["_summary"].startswith("8 repository source identifiers")
    assert len(sources["items"]) == 5


def test_compacts_term_facets() -> None:
    payload = {"termFacets": {"organ": {"terms": [{"term": str(index), "count": index} for index in range(25)]}}}
    compacted = compact_payload(payload)
    terms = compacted["termFacets"]["organ"]["terms"]
    assert terms["_summary"].startswith("25 facet terms")
    assert len(terms["items"]) == 10
