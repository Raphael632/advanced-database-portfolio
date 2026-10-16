# Portfolio 2 experiment protocol

This protocol is written before the recorded benchmark. It fixes the comparisons so the report does not select only favourable timings.

**Case study:** Nigeria Food Price Observatory. **Source:** the verified Portfolio 1 database with 3,528 actual NBS observations for 2025. No synthetic enlargement is used.

## Analytical questions

1. Is monthly national and zonal coverage complete?
2. Which source item labels are available at each level?
3. How did the national price of Rice Local, short-Grained change from the preceding calendar month?
4. How wide was this item's regional price spread each month?
5. Which zones ranked highest for this item in December, and how did they compare with the published national average?
6. Which national item series had the largest January-to-December percentage changes?
7. Which item labels cannot be matched across national and zonal tables?
8. Which items had the widest relative regional spread in December?

## Predefined benchmark cases

| Case | Before | After | Change isolated |
|---|---|---|---|
| B01 series lookup | Original required indexes | Two additional covering indexes | Same SQL and parameters; index tuning |
| B02 top prices for one item | Original required indexes | Two additional covering indexes | Same SQL and parameters; filter/order/limit access |
| B03 predicate rewrite | `CAST(item_id AS TEXT) = :item_text` on the tuned copy | `item_id = :item_id` on the same tuned copy | Predicate rewrite only; canonical integer item IDs |
| B04 coverage control | Monthly coverage on baseline | Same query on tuned copy | Full-workload control; improvement not assumed |

Default parameters are resolved from the source labels, not guessed IDs: `Rice Local, short-Grained`, `Nigeria`, January 2025 and December 2025. The top-price query uses a predeclared floor of 100,000 kobo (NGN 1,000) and a limit of 10. These are query parameters, not invented observations. B02 includes both national and zonal published averages; it is a catalogue retrieval exercise, not a ranking of retail outlets.

## Measurement

- Open the source database read-only and use SQLite backup to create a baseline and a tuned copy in a new local run directory.
- Retain all uniqueness/primary-key indexes. Do not force plans, disable automatic indexes, or remove constraints to make the baseline look worse.
- Run `ANALYZE` on both copies. Add only the two declared indexes to the tuned copy.
- Use the same SQLite settings and connection options. Record engine/build details, schema hashes, source database hash, row count, page usage and index definitions.
- Verify exact ordered result equality before timing. Also compare every analytical query before and after tuning.
- Warm each statement 20 times. Run 31 rounds of 200 executions per side, alternating which side runs first. Fetch all rows on every execution. Record every per-round mean in microseconds per query, plus median, quartiles and min/max. Values are batch means, not individual-request latency percentiles.
- Time only execution and fetching with a monotonic high-resolution timer. Exclude copying, index creation, `ANALYZE`, file export, explanation and SQL preparation after warm-up. Normal Python call/fetch overhead remains included.
- Separately count SQLite progress-handler callbacks at a one-instruction interval, outside timing. This is a virtual-machine work indicator, not disk reads or rows examined.
- Capture actual `EXPLAIN QUERY PLAN` trees for both states. Do not make correctness depend on a particular plan string across SQLite versions.
- Measure index creation time once, and record index bytes where `dbstat` is available. Indexes consume storage and add maintenance work; this read experiment does not measure write throughput.
- Hash the original database again after the experiment to confirm it was not changed.

## Reporting boundaries

Publish SQL, plans, derived percentage/ranking/count results, test output and benchmark measurements. Keep source workbooks, populated database copies and raw-price benchmark rows local. The NBS data-access terms remain those documented in Portfolio 1.

This is a warm-cache, single-process, local experiment on a small fixed dataset. Speed ratios are descriptive for this run, not production capacity estimates. A slow or unchanged control result is retained. Do not call January-to-December changes year-on-year inflation, treat a simple spread as a weighted index, or merge the distinct smoked-fish labels.
