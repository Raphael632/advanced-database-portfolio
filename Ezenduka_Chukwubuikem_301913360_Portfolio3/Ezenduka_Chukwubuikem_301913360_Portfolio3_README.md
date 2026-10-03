# Portfolio 3: Transactions and concurrency

Status: **implemented and verified; student review pending**.

Start with the [transaction analysis](Ezenduka_Chukwubuikem_301913360_Transaction_Analysis.md). Open the [HTML evidence viewer](Ezenduka_Chukwubuikem_301913360_Evidence_Preview.html) locally in a browser for the process sequence and expandable SQL traces. GitHub displays HTML source; [Markdown evidence](Ezenduka_Chukwubuikem_301913360_Transaction_Evidence.md) can be read directly on GitHub.

| Requirement | Evidence |
|---|---|
| Commit | T01, reopened connection sees saved result |
| Rollback | T02 full rollback; T03 savepoint |
| Isolation | T01 no uncommitted read; T06 WAL snapshot |
| Concurrency | T04 overwrite; T05 version guard; T07 snapshot conflict; T08 writer contention |
| Actual outputs | JSON/Markdown/HTML with nine passing cases |
| Error handling | T09 and helper cleanup |

## Reproduce

Build Portfolio 1 first. Use Python 3.12 or later with SQLite 3.37 or later; the runner uses the standard library only. From the repository root:

```powershell
python Ezenduka_Chukwubuikem_301913360_Portfolio3/Ezenduka_Chukwubuikem_301913360_Run.py
```

Input defaults to `.local/Ezenduka_Chukwubuikem_301913360_Food_Prices.sqlite3`, the original Portfolio 1 database with no review tasks. If stored elsewhere, append `--database PATH_TO_DATABASE --workspace PATH_TO_LOCAL_RUNS`.

Each run creates a fresh `portfolio3_TIMESTAMP` directory containing a local-only database copy and an `evidence` folder. Optional `--evidence-dir PATH` selects another output location. Preserve the captured report's evidence or update the report's run identifier when replacing it.

The runner is also the integration test harness: it checks expected rows, versions, error codes and transaction states, and stops on a mismatch. SQL is embedded in the runner and captured by connection in JSON. All nine scenarios passed in the submitted run. Connections are deterministically interleaved; this is not a load test.

Only fictional review notes are exported. Keep populated databases/WAL files out of Git and the submission. See the root source-use notes and AI-use record. Student explanation and reflection are still pending.
