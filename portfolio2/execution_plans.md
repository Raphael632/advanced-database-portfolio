# Portfolio 2: Actual execution plans

SQLite 3.53.1. Plans are engine/version-specific. No plan hints were used.

## B01_series_lookup

Before:

```text
  4 parent=  0  SEARCH price_observation USING INDEX sqlite_autoindex_price_observation_1 (ANY(publication_id) AND item_id=? AND geography_id=?)
```

After:

```text
  3 parent=  0  SEARCH price_observation USING COVERING INDEX idx_p2_series_cover (item_id=? AND geography_id=?)
```

## B02_top_prices

Before:

```text
  5 parent=  0  SEARCH price_observation USING INDEX sqlite_autoindex_price_observation_1 (ANY(publication_id) AND item_id=?)
 31 parent=  0  USE TEMP B-TREE FOR ORDER BY
```

After:

```text
  4 parent=  0  SEARCH price_observation USING COVERING INDEX idx_p2_price_cover (item_id=? AND price_kobo>?)
```

## B03_predicate_rewrite

Before:

```text
  3 parent=  0  SEARCH price_observation USING COVERING INDEX idx_p2_series_cover (ANY(item_id) AND geography_id=?)
 23 parent=  0  USE TEMP B-TREE FOR ORDER BY
```

After:

```text
  3 parent=  0  SEARCH price_observation USING COVERING INDEX idx_p2_series_cover (item_id=? AND geography_id=?)
```

## B04_coverage_control

Before:

```text
 10 parent=  0  SCAN p USING COVERING INDEX sqlite_autoindex_publication_1
 12 parent=  0  SEARCH o USING COVERING INDEX sqlite_autoindex_price_observation_1 (publication_id=?)
 16 parent=  0  SEARCH g USING INTEGER PRIMARY KEY (rowid=?)
 65 parent=  0  USE TEMP B-TREE FOR count(DISTINCT)
 68 parent=  0  USE TEMP B-TREE FOR ORDER BY
```

After:

```text
 10 parent=  0  SCAN p USING COVERING INDEX sqlite_autoindex_publication_1
 12 parent=  0  SEARCH o USING COVERING INDEX sqlite_autoindex_price_observation_1 (publication_id=?)
 16 parent=  0  SEARCH g USING INTEGER PRIMARY KEY (rowid=?)
 65 parent=  0  USE TEMP B-TREE FOR count(DISTINCT)
 68 parent=  0  USE TEMP B-TREE FOR ORDER BY
```
