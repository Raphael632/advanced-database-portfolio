-- Apply only to the disposable optimised copy for this experiment.
-- Existing PRIMARY KEY and UNIQUE indexes are retained in both copies.
CREATE INDEX idx_p2_series_cover
ON price_observation(item_id, geography_id, publication_id, price_kobo);

CREATE INDEX idx_p2_price_cover
ON price_observation(item_id, price_kobo DESC, geography_id, publication_id);

-- A full ANALYZE is appropriate for this small, fixed experiment.
-- The baseline copy is also analysed before timing.
ANALYZE;
