# Advanced Database Systems Portfolio

**Student:** Ezenduka Chukwubuikem  
**Student ID:** 301913360  
**Course:** MIT 8103, 2026/2027 First Semester  
**Repository:** https://github.com/Raphael632/advanced-database-portfolio  
**Deadline:** 15 November 2026; preferred completion during October.

## Case study

**Nigeria Food Price Observatory** is a student-designed research and data-quality system using the National Bureau of Statistics (NBS) Selected Food Price Watch. It is not an NBS production system or an NBS-endorsed project. The data provider is NBS; the application and its workflow are a simulated academic case study.

The system will import monthly published averages, preserve their provenance, compare like-for-like item prices over time and across regions, and support a reviewer workflow. Database users are research analysts, data stewards and an administrator.

## Phases

| Phase | Required work | Status |
|---|---|---|
| 1 | Design, ER diagram, schema, constraints, normalisation and executed validation | Implemented and tested; student review pending |
| 2 | SQL results, query plans, indexing and measured performance | Implemented and tested; student review pending |
| 3 | Commit, rollback, isolation and concurrent reviewer updates | Implemented and verified; student review pending |
| 4 | Implemented NoSQL model of the same case study | Implemented and tested; student review pending |
| 5 | Distributed/cloud architecture or exercise with stated consistency tradeoffs | Local exercise implemented and tested; cloud design proposed; student review pending |
| Final | 2-3 page summary, supporting evidence, personal reflection and AI declaration | Three-page review draft and final audit prepared; personal reflection and submission checks pending |

## Source access and redistribution

Source catalogue: https://microdata.nigerianstat.gov.ng/index.php/catalog/162/related-materials  
NBS terms: https://www.nigerianstat.gov.ng/page/terms

These are publicly downloadable data, not a dataset verified under an unrestricted open licence. NBS terms restrict redistribution without written agreement. Source workbooks, archive files and the populated database are therefore local-only and excluded from Git and the submission package. The code, source URLs, checksums, design and aggregate validation evidence are shareable project outputs. An assessor can reproduce the database by obtaining the data directly from NBS under its terms. Do not attach the full data or populated database without resolving redistribution permission.

The NBS terms also request an electronic copy of publications based on its data. Any correspondence or fulfilment of that requirement is a student action; no report has been sent to NBS.

## Portfolio 1 results

The executed database contains eight tables and one reporting view. It holds **3,528 source observations**, **12 months**, **7 geographies**, and **43 distinct source labels**. All observations reconcile with the downloaded workbook cells after rounding to kobo. Twenty offline tests passed. See the [design explanation](Ezenduka_Chukwubuikem_301913360_Portfolio1/Ezenduka_Chukwubuikem_301913360_Design.md), [ER diagram](Ezenduka_Chukwubuikem_301913360_Portfolio1/Ezenduka_Chukwubuikem_301913360_ER_Diagram.png), and [verification report](Ezenduka_Chukwubuikem_301913360_Portfolio1/Ezenduka_Chukwubuikem_301913360_Verification.md).

## Reproduce Portfolio 1

Requirements: Python 3.12 or later, SQLite 3.37 or later, and openpyxl 3.1.5. The Python standard library supplies SQLite; check its version because builds can differ. No server, paid cloud account or database password is required for this phase.

From a terminal in this folder:

```powershell
python -m pip install -r Ezenduka_Chukwubuikem_301913360_Requirements.txt
python Ezenduka_Chukwubuikem_301913360_Portfolio1/Ezenduka_Chukwubuikem_301913360_Build.py all
python Ezenduka_Chukwubuikem_301913360_Portfolio1/Ezenduka_Chukwubuikem_301913360_Tests.py
```

On this computer, the supplied `Ezenduka_Chukwubuikem_301913360_Run_Portfolio1.ps1` launcher can also use the available bundled Python runtime. Run it from PowerShell with `./Ezenduka_Chukwubuikem_301913360_Run_Portfolio1.ps1`. The launcher validates an existing database rather than rebuilding it, and then runs the tests. If script execution is disabled, use the Python commands above; there is no need to change the computer's security policy.

The `all` Python command downloads the pinned resources into `.local/raw`, verifies their hashes, builds `.local/Ezenduka_Chukwubuikem_301913360_Food_Prices.sqlite3` and writes `.local/validation.json`. Internet access is needed only to fetch missing sources. These local data are ignored by Git. Use `validate` instead of `all` on later runs to check an existing database. `fetch` only downloads/verifies resources; `build` uses already-downloaded files and refuses to overwrite an existing database. `--workspace PATH` selects another local data directory. Source changes require review and an explicit manifest update, not a checksum bypass.

The initially executed database on the development computer is held outside the submission folder in the task's `work/portfolio_runtime` directory. Its aggregate verification evidence has been copied into Portfolio 1. The submission can be reproduced independently with the commands above.

## Portfolio 2 results and reproduction

Eight analytical queries produced 106 independently checked result rows. Two covering indexes and a predicate rewrite were measured against documented baselines; twelve semantic tests passed. The recorded speed ratios were 1.13x for a series lookup, 1.40x for a top-price query and 2.12x for the rewrite. The full-coverage control did not improve. The indexes added 128 KiB. These are warm-cache measurements on this small dataset, not production performance claims.

See the [Portfolio 2 guide](Ezenduka_Chukwubuikem_301913360_Portfolio2/Ezenduka_Chukwubuikem_301913360_Portfolio2_README.md) for reproduction commands and the [performance analysis](Ezenduka_Chukwubuikem_301913360_Portfolio2/Ezenduka_Chukwubuikem_301913360_Performance_Analysis.md) for plans, measurements and limitations. The runner preserves the original database and keeps populated benchmark copies local.

## Portfolio 3 results

Nine executed transaction scenarios passed: commit/reopen, complete rollback after a constraint failure, savepoint rollback, stale-form overwrite, optimistic version checking, WAL reader snapshots, stale-snapshot write rejection, writer contention and error cleanup. Two independent connections operate on a disposable copy with fictional review tasks. The source database remains unchanged.

See the [Portfolio 3 guide](Ezenduka_Chukwubuikem_301913360_Portfolio3/Ezenduka_Chukwubuikem_301913360_Portfolio3_README.md), [analysis](Ezenduka_Chukwubuikem_301913360_Portfolio3/Ezenduka_Chukwubuikem_301913360_Transaction_Analysis.md) and [visual evidence viewer](Ezenduka_Chukwubuikem_301913360_Portfolio3/Ezenduka_Chukwubuikem_301913360_Evidence_Preview.html). The viewer opens locally in a browser; Markdown output is also included for GitHub.

## Portfolio 4 results

The TinyDB document model stores 516 item/month documents and preserves all 3,528 observations and their provenance. Six document queries match independent SQL references. Fictional review CRUD and persistence checks pass, as do twelve semantic tests. This is a single-writer local projection; it does not replace the relational concurrency controls.

See the [Portfolio 4 guide](Ezenduka_Chukwubuikem_301913360_Portfolio4/Ezenduka_Chukwubuikem_301913360_Portfolio4_README.md), [document model and analysis](Ezenduka_Chukwubuikem_301913360_Portfolio4/Ezenduka_Chukwubuikem_301913360_NoSQL_Analysis.md), and [visual evidence page](Ezenduka_Chukwubuikem_301913360_Portfolio4/Ezenduka_Chukwubuikem_301913360_Evidence_Preview.html). Populated document storage remains local-only.

## Portfolio 5 results

Eight local integration scenarios and ten focused tests passed. The exercise implements primary/replica review-event replay, freshness-aware reads, simulated outage refusal, worker recovery, backup restore and two month-range shards of 1,764 observations each. Their union exactly reproduces the 3,528-row source projection. The report distinguishes these local SQLite files and simulated outages from its proposed cloud architecture; no cloud cluster is deployed.

See the [Portfolio 5 guide](Ezenduka_Chukwubuikem_301913360_Portfolio5/Ezenduka_Chukwubuikem_301913360_Portfolio5_README.md), [analysis and architecture](Ezenduka_Chukwubuikem_301913360_Portfolio5/Ezenduka_Chukwubuikem_301913360_Distributed_Analysis.md) and [executed evidence](Ezenduka_Chukwubuikem_301913360_Portfolio5/Ezenduka_Chukwubuikem_301913360_Distributed_Evidence.md). All five technical phase implementations now have evidence; final documentation, student reflection and submission packaging are still pending.

## Summary and final audit

The [three-page summary PDF](Ezenduka_Chukwubuikem_301913360_Final_Documentation/Ezenduka_Chukwubuikem_301913360_Submission_Summary.pdf) and [editable Markdown version](Ezenduka_Chukwubuikem_301913360_Final_Documentation/Ezenduka_Chukwubuikem_301913360_Submission_Summary.md) are review drafts. The [final audit](Ezenduka_Chukwubuikem_301913360_Final_Documentation/Ezenduka_Chukwubuikem_301913360_Final_Audit.md) records 54 passing unit tests, fresh execution of all phases, a complete source rebuild and the limitations of the originality review. No institutional similarity percentage is claimed. Personal reflection, accurate student-verification details, assessor access and final packaging must be completed before submission.

## Student review

Read the design document and explain (1) why a price needs the month, item and geography to identify it, (2) why 42 rows per source table produce 43 distinct labels overall, and (3) why a task update needs both a version condition and an increment. Run the tests and record any observations or requested changes in the AI-use log. This review is still pending; the implementation is not a claim of completed personal reflection.

## Submission naming

The final folder is `Ezenduka_Chukwubuikem_301913360`. Authored submission files use `Ezenduka_Chukwubuikem_301913360_DocumentType.ext`. Git configuration is development infrastructure and must be excluded from the final ZIP. This is a developing portfolio, not a ready-to-submit package.

## Originality and understanding

Record sources and actual test results as work progresses. Never claim tests that were not run, manufacture performance improvements, or backdate commits. The final reflection must describe the student's own review and learning. AI assistance is recorded separately and requires an accurate account of the student's subsequent verification.
