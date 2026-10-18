# Portfolio 5: Distributed and cloud database exercise

Status: **local exercise implemented and tested; cloud architecture proposed, not deployed; student reviewed and approved on 18 October 2026**.

Start with the [analysis and architecture](distributed_analysis.md). The [HTML evidence viewer](evidence_preview.html) opens locally in a browser; [Markdown evidence](distributed_evidence.md) is readable on GitHub.

Eight integration scenarios demonstrate asynchronous review-event replication, stale-read routing, simulated outage refusal, replay recovery, backup restoration and month-range shards. Ten focused failure/routing tests pass. These are separate files in one local process, not deployed network nodes.

## Reproduce

Build Portfolio 1 first. Python 3.12 or later with SQLite 3.37 or later is required; this phase uses the standard library only. From the repository root:

```powershell
python portfolio5/run.py
python portfolio5/tests.py
```

The runner reads `.local/Ezenduka_Chukwubuikem_301913360_Food_Prices.sqlite3` by default. It expects the original Portfolio 1 database with no review tasks. For another location, append `--database PATH_TO_DATABASE --workspace PATH_TO_LOCAL_RUNS`.

Each run creates a new `portfolio5_TIMESTAMP` directory containing local-only primary/replica/backup/restore/shard databases and an `evidence` folder. Optional `--evidence-dir PATH` chooses another location for derived evidence. Keep the captured report's outputs together or update the report if replacing them.

## Evidence map

| Requirement | Evidence |
|---|---|
| Replication | Runner event log, apply checkpoint, S01/S02/S04/S05 |
| Availability and consistency | Freshness-aware routing, S02/S03/S08, tradeoff discussion |
| Sharding | Real local range-shard files and exact union verification, S07/S08 |
| Recovery | Snapshot restore and acknowledged-edit loss, S06 |
| Cloud design | Explicitly proposed architecture and PNG diagram |
| Executed checks | Evidence JSON/Markdown/HTML plus test log |

The original source is unchanged. Populated databases, including shard projections, must remain local and outside Git/submission. No cloud resources or costs are incurred. The personal reflection is included in the [submission summary](../final_documentation/submission_summary.md#individual-reflection).
