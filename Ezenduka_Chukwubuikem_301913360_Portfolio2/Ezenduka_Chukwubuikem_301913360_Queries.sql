-- All statements are parameterised and read-only.
-- Results are analytical summaries, not a re-export of NBS price tables.

-- name: Q01_COVERAGE
SELECT p.period, COUNT(*) AS observations,
       COUNT(DISTINCT o.item_id) AS distinct_labels,
       SUM(g.level = 'national') AS national_observations,
       SUM(g.level = 'zone') AS zonal_observations
FROM price_observation o
JOIN publication p ON p.publication_id = o.publication_id
JOIN geography g ON g.geography_id = o.geography_id
GROUP BY p.publication_id, p.period
ORDER BY p.period;

-- name: Q02_ITEM_AVAILABILITY
SELECT i.label AS item, COUNT(DISTINCT p.period) AS months,
       SUM(g.level = 'national') AS national_observations,
       SUM(g.level = 'zone') AS zonal_observations
FROM price_observation o
JOIN item i ON i.item_id = o.item_id
JOIN publication p ON p.publication_id = o.publication_id
JOIN geography g ON g.geography_id = o.geography_id
GROUP BY i.item_id, i.label
ORDER BY i.label;

-- name: Q03_MONTHLY_CHANGE
-- Match the actual preceding calendar month, not merely the preceding available row.
SELECT p.period, previous.period AS preceding_month,
       ROUND(100.0 * (o.price_kobo - old.price_kobo) / old.price_kobo, 2) AS change_percent
FROM price_observation o
JOIN publication p ON p.publication_id = o.publication_id
JOIN publication previous
  ON previous.period = strftime('%Y-%m', date(p.period || '-01', '-1 month'))
JOIN price_observation old
  ON old.publication_id = previous.publication_id
 AND old.item_id = o.item_id AND old.geography_id = o.geography_id
WHERE o.item_id = :item_id AND o.geography_id = :geography_id
ORDER BY p.period;

-- name: Q04_REGIONAL_SPREAD
SELECT p.period, COUNT(*) AS zones_observed,
       ROUND(100.0 * (MAX(o.price_kobo) - MIN(o.price_kobo)) / MIN(o.price_kobo), 2) AS spread_percent
FROM price_observation o
JOIN publication p ON p.publication_id = o.publication_id
JOIN geography g ON g.geography_id = o.geography_id
WHERE o.item_id = :item_id AND g.level = 'zone'
GROUP BY p.publication_id, p.period
HAVING COUNT(*) = 6
ORDER BY p.period;

-- name: Q05_REGIONAL_RANKING
-- Ties share a rank; the outer ORDER BY only stabilises display order.
WITH ranked AS (
  SELECT p.period, g.name AS zone,
         DENSE_RANK() OVER (PARTITION BY p.publication_id ORDER BY o.price_kobo DESC) AS price_rank,
         ROUND(100.0 * (o.price_kobo - national.price_kobo) / national.price_kobo, 2) AS premium_to_national_percent
  FROM price_observation o
  JOIN publication p ON p.publication_id = o.publication_id
  JOIN geography g ON g.geography_id = o.geography_id
  JOIN price_observation national
    ON national.publication_id = o.publication_id
   AND national.item_id = o.item_id AND national.geography_id = :national_id
  WHERE o.item_id = :item_id AND g.level = 'zone' AND p.period = :end_period
)
SELECT period, zone, price_rank, premium_to_national_percent
FROM ranked
ORDER BY price_rank, zone;

-- name: Q06_PERIOD_CHANGE_RANKING
SELECT i.label AS item, start.period AS start_period, finish.period AS end_period,
       ROUND(100.0 * (last.price_kobo - first.price_kobo) / first.price_kobo, 2) AS change_percent
FROM price_observation first
JOIN publication start ON start.publication_id = first.publication_id
JOIN price_observation last
  ON last.item_id = first.item_id AND last.geography_id = first.geography_id
JOIN publication finish ON finish.publication_id = last.publication_id
JOIN item i ON i.item_id = first.item_id
WHERE start.period = :start_period AND finish.period = :end_period
  AND first.geography_id = :national_id
ORDER BY change_percent DESC, i.label
LIMIT :top_n;

-- name: Q07_UNMATCHED_LABELS
-- A missing cross-level counterpart is a data limitation, not a zero price.
SELECT i.label AS item, g.level,
       COUNT(*) AS observations_without_other_level
FROM price_observation o
JOIN item i ON i.item_id = o.item_id
JOIN geography g ON g.geography_id = o.geography_id
WHERE NOT EXISTS (
  SELECT 1 FROM price_observation other
  JOIN geography other_geo ON other_geo.geography_id = other.geography_id
  WHERE other.publication_id = o.publication_id AND other.item_id = o.item_id
    AND other_geo.level <> g.level
)
GROUP BY i.item_id, i.label, g.level
ORDER BY i.label, g.level;

-- name: Q08_SPREAD_RANKING
SELECT i.label AS item, p.period, COUNT(*) AS zones_observed,
       ROUND(100.0 * (MAX(o.price_kobo) - MIN(o.price_kobo)) / MIN(o.price_kobo), 2) AS spread_percent
FROM price_observation o
JOIN publication p ON p.publication_id = o.publication_id
JOIN item i ON i.item_id = o.item_id
JOIN geography g ON g.geography_id = o.geography_id
WHERE p.period = :end_period AND g.level = 'zone'
GROUP BY i.item_id, i.label, p.period
HAVING COUNT(*) = 6
ORDER BY spread_percent DESC, i.label
LIMIT :top_n;
