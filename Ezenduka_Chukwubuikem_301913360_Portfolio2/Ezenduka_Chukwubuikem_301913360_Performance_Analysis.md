# Portfolio 2: Query processing and optimisation

Ezenduka Chukwubuikem | 301913360 | MIT 8103

## 1. Purpose and executed dataset

This phase extends the Nigeria Food Price Observatory designed in Portfolio 1. It demonstrates practical SQL analysis, examines the database engine's access paths and measures two covering indexes and a predicate rewrite. The dataset contains **3,528 published NBS price observations** covering January-December 2025. No synthetic rows were added to make the performance gains appear larger.

The recorded experiment is `20261003T212336269310Z`, run on 3 October 2026. Source data and the original database remain unchanged. All timings below refer to this captured run; a fresh run can produce different values.

## 2. SQL implementation and query results

The eight parameterised statements in `Ezenduka_Chukwubuikem_301913360_Queries.sql` use joins, grouping, conditional aggregation, a calendar-month self-join, a common table expression, a window function and an anti-join. The default focus is `Rice Local, short-Grained`, with Nigeria as the national comparison geography.

| Query | Operation and purpose | Actual output |
|---|---|---|
| Q01 coverage | Join publications and geographies; group monthly counts | 12 rows, each with 294 observations: 42 national and 252 zonal |
| Q02 availability | Conditional counts by source item label | 43 rows; the two smoked-fish descriptions have different geographic coverage |
| Q03 monthly change | Join each observation to its preceding calendar month | 11 national rice changes; January has no prior month in this imported dataset |
| Q04 regional spread | `(maximum - minimum) / minimum` for the same item within a month | 12 rows, each requiring all six zones |
| Q05 regional ranking | CTE plus `DENSE_RANK`; compare each zone with the official national figure | Six December rice rankings, retaining ties if present |
| Q06 endpoint change | Join January and December observations by item and geography | Ten largest national January-to-December percentage changes |
| Q07 unmatched labels | `NOT EXISTS` cross-level match | 72 zonal `Smoked fish` records and 12 national `Smoked fish (Mackerel)` records lack an exact-label counterpart |
| Q08 spread ranking | Group one month's zonal values per item and rank relative spread | Ten December item spreads, using six zones for every included item |

Full derived result tables are in [Query Results](Ezenduka_Chukwubuikem_301913360_Query_Results.md), with machine-readable equivalents in the matching JSON file. There are **106 analytical result rows** in total. Raw-price rows returned by the benchmark-only statements stay in the local run directory and are not redistributed.

### Selected analytical findings

- National `Rice Local, short-Grained` increased **1.01%** from January to February, increased **7.36%** from February to March, and decreased **4.40%** from March to April.
- For that item in December, North Central ranked highest and was **9.19% above** the published national figure. South West was **5.11% above** it. These are regional published averages, not individual market prices.
- Among national series, `Cray fish small white` had a January-to-December change of **37.88%**, followed by `Ginger, fresh` at **27.46%** and `Chicken feet` at **20.14%** in the returned ranking.
- `Beans white` had the largest December relative regional spread in the returned results: **128.30%** above its lowest regional average at the highest region. This is not a 128.30% change over time.

These findings are calculations over the imported 2025 NBS tables, after the Portfolio 1 rounding to kobo. They are not an inflation index, a weighted basket calculation or year-on-year estimates. January-to-December compares two endpoints eleven months apart. Comparisons preserve the source item descriptions; unspecified units are not guessed.

## 3. Baseline and tuning decisions

Both database copies retain all ten indexes originally created by primary-key/unique constraints that appear in `sqlite_master` as autoindexes. Integer rowid primary keys have their own access mechanism and are not counted as separate named indexes in this number. Both copies are analysed with `ANALYZE`, so the baseline is a normal constrained database with available planner statistics.

The first new index is:

```sql
CREATE INDEX idx_p2_series_cover
ON price_observation(item_id, geography_id, publication_id, price_kobo);
```

Item and geography are equality predicates. Publication ID follows in the requested benchmark order; the price is included so SQLite can return the requested columns from the index. Portfolio 1 assigns publication IDs in month order for this snapshot. The analytical time comparison uses the actual `period` field and does not assume that ID order will always mean chronological order in a future import.

The second index is:

```sql
CREATE INDEX idx_p2_price_cover
ON price_observation(item_id, price_kobo DESC, geography_id, publication_id);
```

The item equality narrows the index range; the price threshold and descending order support the top-price query. Geography and publication provide deterministic tie ordering and make the selected columns available in the index. The query searches one item only, so unrelated units are not ranked against one another. Its threshold is 100,000 kobo and its result limit is 10.

These indexes support different orderings. Neither is simply a leading-column duplicate of the other, so retaining both has a defensible purpose for the two tested access patterns. There is no claim that every possible application query benefits.

## 4. Execution-plan evidence

The actual plans are saved in [Execution Plans](Ezenduka_Chukwubuikem_301913360_Execution_Plans.md). The JSON file also captures before/after plans for all eight analytical queries.

**Series lookup:** before tuning, SQLite already uses the natural-key index with `ANY(publication_id)` and equality tests on item and geography. This is a skip-scan style access path, not a full-table scan. After tuning, it searches the covering series index directly using the two leading equality columns. The measured virtual-machine work falls from 202 to 72 callback units.

**Top-price query:** the baseline uses the natural-key index to find the item's records, then reports `USE TEMP B-TREE FOR ORDER BY`. The tuned query searches the covering price index and no longer reports that temporary ordering structure. Callback work falls from 1,231 to 97.

**Predicate rewrite:** both sides use the already tuned database. The deliberately wrapped predicate `CAST(item_id AS TEXT) = :item_text` prevents the direct item equality lookup in this query. Its plan uses `ANY(item_id)` with geography and a temporary sort. Rewriting it as `item_id = :item_id` allows the direct covering-index lookup. Callback work falls from 2,984 to 72. Equivalence is demonstrated only for the canonical integer ID and its string representation, such as integer `29` and text `'29'`; arbitrary strings with leading zeroes are not silently treated as equivalent. The test suite explicitly checks that boundary.

**Coverage control:** the plan remains the same. It scans the small publication index, searches observations by publication, looks up geography rows and uses temporary structures for the distinct count and result ordering. It must still account for the whole dataset. The callback count is 79,550 on both sides.

The progress-handler callback interval is one SQLite virtual-machine instruction. It is collected outside timed runs and is a work indicator, not a count of disk operations, source rows examined or physical page reads. `EXPLAIN QUERY PLAN` text is version-specific and is retained as observed evidence rather than treated as a portable API contract.

## 5. Measured performance

Each side has 20 warm-up executions followed by **31 rounds of 200 executions**, with before/after order alternating by round. Every execution fetches all result rows. The reported median and interquartile range are across the 31 per-round means, in microseconds per query. They are not percentiles of individual request latencies.

| Case | Before median (microseconds) | After median (microseconds) | Before IQR | After IQR | Before / after |
|---|---:|---:|---|---|---:|
| B01 series lookup | 107.612 | 95.395 | 105.427-116.430 | 92.944-97.925 | 1.13x |
| B02 top prices | 189.969 | 135.632 | 186.848-201.227 | 127.963-138.410 | 1.40x |
| B03 predicate rewrite | 203.587 | 95.852 | 194.463-212.782 | 94.669-104.428 | 2.12x |
| B04 coverage control | 1,677.869 | 1,695.345 | 1,651.247-1,724.589 | 1,651.312-1,732.828 | 0.99x |

A ratio above one means the tested after version is faster in this run. The coverage query is slightly slower by its median, with overlapping IQRs and identical plans/work counts. The experiment therefore provides no evidence of a useful improvement for that query. It is not discarded from the results.

The targeted improvements are modest in absolute time: approximately 12, 54 and 108 microseconds per execution. The much larger reduction in virtual-machine work does not translate proportionally into elapsed-time reductions, because the recorded call includes Python execution/fetch overhead and local database access overhead. No statistical significance or production-throughput claim is made.

## 6. Costs and tradeoffs

After `ANALYZE`, the baseline copy occupies 95 pages of 4,096 bytes (**389,120 bytes**). The tuned copy occupies 127 pages (**520,192 bytes**). Each new index occupies 16 pages (**65,536 bytes**), adding **131,072 bytes** overall, approximately **33.68%** of the baseline copy's size. The one observed index-creation-plus-ANALYZE operation took **765.763 ms**; it includes local setup costs and is not a stable deployment estimate.

The indexes improve repeated targeted reads but consume storage and would require maintenance when future observations are inserted. This experiment does not measure insert throughput or write amplification. On only 3,528 records, the decision to retain both indexes in a deployed system would depend on the actual frequency of these access patterns and the expected data growth. For the portfolio they remain in a separate tuned copy, while the original source database is preserved.

## 7. Verification and limitations

- All four benchmark pairs produced exactly equal ordered rows. The evidence includes each result count and SHA-256 digest.
- All eight analytical statements produced the same output before and after tuning.
- All 106 analytical result rows were checked against independently grouped Python data. Percentage calculations use an independent decimal calculation with tolerance of one percentage-point hundredth for two-decimal rounding differences.
- All twelve semantic tests passed. They cover calendar gaps, valid percentage division, tied ranks, incomplete zone coverage, unit-preserving comparisons, distinct source labels, parameter binding, stable ordering, rewrite boundaries, index equivalence and read-only enforcement.
- The original database's SHA-256 hash is unchanged. Database integrity and foreign-key checks passed for the source and both copies.
- Both copies use the same database settings, automatic indexes remain enabled and no index hint forces the outcome. The benchmark records SQLite compile options and all 31 samples for each side.

This is a **warm-cache, single-process local experiment** using Python 3.12.14 and SQLite 3.53.1. It does not test cold storage, server/network latency, concurrent clients, larger data volumes or cloud deployment. Background system activity can affect timings. Future work can test a larger real dataset, but any synthetic scale experiment must be separately labelled and must not be mixed into the real NBS analytical findings.

## 8. References and authorship

1. National Bureau of Statistics, Nigeria. *Selected Food Price Watch*, 2025 tables. https://microdata.nigerianstat.gov.ng/index.php/catalog/162/related-materials. Individual resources and checksums are documented in Portfolio 1.
2. NBS. *Terms & Conditions*. https://www.nigerianstat.gov.ng/page/terms. Source files and populated databases remain local; this phase reports derived statistical analysis and technical evidence.
3. SQLite. *EXPLAIN QUERY PLAN*. https://www.sqlite.org/eqp.html (accessed 3 October 2026).
4. SQLite. *Query Planning*. https://www.sqlite.org/queryplanner.html (accessed 3 October 2026).
5. SQLite. *ANALYZE*. https://www.sqlite.org/lang_analyze.html (accessed 3 October 2026).
6. Python. *sqlite3: Progress handler*. https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.set_progress_handler.

Codex assisted with the SQL, experiment runner, tests, measurements and explanation. The student's personal review and reflection remain pending and are not represented as completed by this report. This detailed phase report will later be condensed into the semester's separate 2-3 page final summary.
