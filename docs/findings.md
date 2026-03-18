# Findings Beyond The Linked Docs

- The live public HCA API is currently the Azul service at `https://service.azul.data.humancellatlas.org`, and the current OpenAPI document exposes 26 operations.
- The live service catalogs are not just one HCA catalog. The current production service exposes `dcp57`, `dcp58`, and `lm10`, plus internal `-it` variants. The LungMAP catalogs also appear through the same service.
- The live catalog metadata shows `atlas` values such as `hca` and `lungmap`, which is useful for an atlas mental model but is not obvious from the linked DSS and Azul README material.
- The live repository plugin is `tdr_hca` with Terra Data Repository source identifiers, not DSS-style storage endpoints. The linked DSS repository therefore reads as historical background, not as the current live backend for the public query API.
- `/index/summary` contains a useful atlas-oriented signal in `cellCountSummaries`, but the raw organ labels are messy: there are duplicated labels with different casing, mixed granularity, and occasional `null` values. A CLI atlas view needs normalization and compaction.
- The `selectedCellType` facet is present and rich, but it is not exposed through `/index/summary`. Cell-type atlas views therefore have to be derived from index facets such as `/index/projects?size=0`.
- In the live service, `/index/projects?size=0` does not currently behave like a harmless facet-only query. The CLI has to use a small positive `size` and ignore the returned hits when it wants live facet terms.
- The `tissueAtlas` facet is populated with atlas labels such as `Lung`, `Gut`, `Heart`, and `Immune`, while `isTissueAtlasProject` is currently entirely `false` in the live project facet response. That mismatch is not obvious from the linked documents alone.
- Large low-value lists show up immediately in live responses, especially repository source lists, long facet term arrays, and `organTypes`. These are the main cases compacted by default in the CLI.
- The closest thing to a dataset in the live API is not a top-level entity but a derived unit inside project detail metadata, especially under `projects[0].contributedAnalyses` and sometimes `projects[0].matrices`.
