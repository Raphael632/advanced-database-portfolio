# Portfolio 4: NoSQL and advanced data models

Status: **implemented and tested; student review pending**.

Start with the [NoSQL analysis](nosql_analysis.md). The [visual evidence page](evidence_preview.html) opens locally in a browser; [Markdown results](nosql_evidence.md) can be read directly on GitHub.

The real TinyDB implementation persists 516 item/month documents with all 3,528 source observations reconciled after reopening. Six queries match SQL reference results, review CRUD passes, and twelve fictional-data tests pass. TinyDB is an embedded, single-writer demonstration, not a concurrent production service.

## Reproduce

Build Portfolio 1 first. Using Python 3.12 or later, run from the repository root:

```powershell
python -m pip install -r portfolio4/requirements.txt
python portfolio4/run.py
python portfolio4/tests.py
```

The default source is `.local/Ezenduka_Chukwubuikem_301913360_Food_Prices.sqlite3`. For another location, append `--database PATH_TO_DATABASE --workspace PATH_TO_LOCAL_RUNS` to the runner. It reads the source without changing it and creates `portfolio4_TIMESTAMP/food_price_documents_LOCAL_ONLY.json` and an `evidence` folder. Never publish the populated JSON database. `--evidence-dir PATH` optionally selects another derived-output folder.

The captured report describes one specific run. Keep its evidence together, or update the narrative and identifiers when replacing it. The runner checks reconciliation/query/CRUD outcomes; the test script separately checks invalid values, duplicate imports, array semantics, source-label separation and persistence.

## Evidence map

| Requirement | File |
|---|---|
| Document model, diagram and suitability | `nosql_analysis.md` |
| Complete fictional document example | `fictional_document_example.json` |
| Real engine implementation | `run.py` |
| Query/CRUD/reconciliation outputs | `nosql_evidence.json` and `.md` |
| Visual inspection | `evidence_preview.html` |
| Semantic tests and results | `tests.py`, `test_log.txt` |

Personal review and reflection remain pending. See the AI-use record and root source-use restrictions.
