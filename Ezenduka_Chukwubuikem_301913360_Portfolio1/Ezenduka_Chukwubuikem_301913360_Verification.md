# Portfolio 1: Executed verification

Initial build and source reconciliation: **2 October 2026, 08:50:16 UTC**. See the machine-readable validation file for the full timestamp and counts. This report describes actual execution, not expected output.

| Check | Observed result |
|---|---|
| Source resources verified by SHA-256 | 11 |
| Monthly publications | 12, January-December 2025 |
| Distinct item labels | 43 |
| Geographies | 7: Nigeria and 6 zones |
| Imported observations | 3,528 |
| Observations per month | 294 in every month |
| Source values and cell provenance reconciled | 3,528 of 3,528 |
| SQLite integrity check | `ok` |
| Foreign-key violations | 0 |
| Synthetic price observations in the database | 0 |
| Fictional demo accounts | 2 |
| Review tasks at initial build | 0 |
| Offline automated tests | 20 passed |

Environment: Python 3.12.14, SQLite 3.53.1, openpyxl 3.1.5. The test suite ran in 0.060 seconds in the recorded run; this is a test-run duration, not a query-performance benchmark.

## What the tests establish

The SQL schema rejects orphan references, duplicate natural keys and source cells, nonpositive and noninteger prices, missing prices, invalid reporting months and unsupported geographies. It prevents deleting a referenced item and prevents changes to imported price observations. Review tasks require an existing user and a supported status. The version test rejects an update without a version increment and demonstrates that a stale version condition updates zero rows. A failed two-statement batch leaves no partially inserted task.

Importer tests check month parsing from the current-period header, malformed headers, decimal half-up rounding, invalid numeric inputs and cosmetic label cleanup without merging the distinct fish descriptions. Test fixtures are fictional and isolated in memory; they are never inserted into the official-source database.

## Evidence files

- `Ezenduka_Chukwubuikem_301913360_Validation.json`: actual database counts, engine versions, reconciliation outcome and source issues.
- `Ezenduka_Chukwubuikem_301913360_Test_Log.txt`: actual output of all 20 tests.
- `Ezenduka_Chukwubuikem_301913360_Sources.json`: download URLs, expected reporting months and source checksums.
- `Ezenduka_Chukwubuikem_301913360_Schema.sql`: executed relational schema.
- `Ezenduka_Chukwubuikem_301913360_ER_Diagram.png`: diagram checked against the schema and visually inspected.

No complete source tables or populated database are included in Git or this report. Source and database reconstruction is documented in the student-prefixed README. The original local commits were published to the private GitHub repository on 2 October 2026 with their commit IDs preserved. Student review remains pending. Subsequent query optimisation, transactions/concurrency, NoSQL and local distributed/cloud exercise evidence are documented separately in Portfolios 2–5.
