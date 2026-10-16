-- Raw price result rows from these statements remain local, outside the repository.

-- name: SERIES
SELECT publication_id, price_kobo
FROM price_observation
WHERE item_id = :item_id AND geography_id = :geography_id
ORDER BY publication_id;

-- name: TOP_PRICES
-- Only one item is compared, preserving the same reported unit/pack description.
SELECT publication_id, geography_id, price_kobo
FROM price_observation
WHERE item_id = :item_id AND price_kobo >= :floor_kobo
ORDER BY price_kobo DESC, geography_id, publication_id
LIMIT :top_n;

-- name: WRAPPED_SERIES
-- Deliberately unnecessary conversion, used to demonstrate a predicate rewrite.
SELECT publication_id, price_kobo
FROM price_observation
WHERE CAST(item_id AS TEXT) = :item_text AND geography_id = :geography_id
ORDER BY publication_id;
