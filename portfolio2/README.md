# Portfolio 2: Query processing and optimisation

**Status:** implemented and tested; student reviewed and approved on 18 October 2026.
**Case study:** Nigeria Food Price Observatory, using the Portfolio 1 NBS database.

Start with the [performance analysis](performance_analysis.md). The phase contains eight analytical queries, two covering indexes, an equivalent-predicate rewrite, measured execution plans/timings, 106 checked analytical output rows and twelve passing semantic tests.

## Evidence map

| Requirement | File |
|---|---|
| SQL statements | `queries.sql` |
| Query results | `query_results.md` and `.json` |
| Benchmark statements and index definitions | `benchmark_queries.sql`, `indexes.sql` |
| Experiment design fixed before measurement | `method.md` |
| Actual execution plans | `execution_plans.md` and `.json` |
| Timings, all round samples, work counts, storage and environment | `benchmark_results.json` |
| Explanation and limitations | `performance_analysis.md` |
| Reproducible runner | `run.py` |
| Semantic checks and actual output | `tests.py`, `test_log.txt` |

## Reproduce

Build Portfolio 1 first. From the repository root, using Python 3.12 or later with SQLite 3.37 or later:

```powershell
python portfolio2/run.py
python portfolio2/tests.py
```

The runner uses the standard library only. It reads `.local/Ezenduka_Chukwubuikem_301913360_Food_Prices.sqlite3` by default and creates a new timestamped run directory under `.local`. It never writes to the source database. The run contains baseline/tuned database copies, raw-price benchmark rows marked `LOCAL_ONLY`, and an `evidence` directory of derived outputs. These local data must remain excluded from the submission and Git.

If Portfolio 1 was built elsewhere, pass `--database PATH_TO_DATABASE --workspace PATH_TO_LOCAL_RUNS`. An optional `--evidence-dir PATH` writes the derived evidence to a chosen folder. The submitted report describes one fixed captured run; a new run does not automatically rewrite its narrative. Preserve the old evidence or refresh the narrative consistently when capturing a replacement run.

Defaults: 31 rounds, 200 executions per side per round and 20 warm-ups per side. The `--rounds`, `--repetitions` and `--warmups` options are for explicitly labelled alternative runs. No fresh source download is required after Portfolio 1 is available.

## Student review

Explain why the original natural-key index already helps some lookups, why the covering indexes avoid table lookups or a temporary sort, why converting the indexed item column to text changes the access path, and why the coverage query did not improve. Compare elapsed time with the work counters and discuss the 128 KiB storage cost. Record your own checks and learning in the technology overview before writing the final personal reflection.
