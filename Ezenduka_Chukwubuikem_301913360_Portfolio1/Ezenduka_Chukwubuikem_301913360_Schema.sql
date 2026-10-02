-- SQLite >= 3.37. Enable foreign keys on EVERY connection.
PRAGMA foreign_keys = ON;

CREATE TABLE publisher (
    publisher_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    homepage TEXT NOT NULL
) STRICT;

CREATE TABLE source_resource (
    resource_id INTEGER PRIMARY KEY,
    publisher_id INTEGER NOT NULL REFERENCES publisher(publisher_id),
    download_url TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
    retrieved_at TEXT NOT NULL,
    byte_count INTEGER NOT NULL CHECK (byte_count > 0)
) STRICT;

CREATE TABLE publication (
    publication_id INTEGER PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES source_resource(resource_id),
    period TEXT NOT NULL UNIQUE CHECK (
        length(period) = 7 AND period GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'
        AND CAST(substr(period,6,2) AS INTEGER) BETWEEN 1 AND 12
    ),
    workbook_name TEXT NOT NULL,
    workbook_sha256 TEXT NOT NULL CHECK (
        length(workbook_sha256) = 64 AND workbook_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    UNIQUE(resource_id, workbook_name)
) STRICT;

CREATE TABLE item (
    item_id INTEGER PRIMARY KEY,
    label TEXT NOT NULL UNIQUE CHECK (length(trim(label)) > 0)
) STRICT;

CREATE TABLE geography (
    geography_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    level TEXT NOT NULL CHECK (level IN ('national','zone')),
    CHECK ((level = 'national' AND name = 'Nigeria') OR
           (level = 'zone' AND name IN ('NORTH CENTRAL','NORTH EAST','NORTH WEST',
                                        'SOUTH EAST','SOUTH SOUTH','SOUTH WEST')))
) STRICT;

-- Observation grain: one published current-month price per item/geography/publication.
-- Prices are NGN stored as integer kobo. Source workbooks retain full precision.
CREATE TABLE price_observation (
    observation_id INTEGER PRIMARY KEY,
    publication_id INTEGER NOT NULL REFERENCES publication(publication_id),
    item_id INTEGER NOT NULL REFERENCES item(item_id),
    geography_id INTEGER NOT NULL REFERENCES geography(geography_id),
    price_kobo INTEGER NOT NULL CHECK (price_kobo > 0),
    source_sheet TEXT NOT NULL CHECK (length(trim(source_sheet)) > 0),
    source_cell TEXT NOT NULL CHECK (length(trim(source_cell)) > 0),
    UNIQUE(publication_id, item_id, geography_id),
    UNIQUE(publication_id, source_sheet, source_cell)
) STRICT;

-- Source snapshots are immutable; workflow changes belong in review_task.
CREATE TRIGGER protect_price_update BEFORE UPDATE ON price_observation
BEGIN SELECT RAISE(ABORT, 'Published source observations are immutable'); END;
CREATE TRIGGER protect_price_delete BEFORE DELETE ON price_observation
BEGIN SELECT RAISE(ABORT, 'Published source observations are immutable'); END;

CREATE TABLE app_user (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE CHECK (length(trim(username)) > 0),
    role TEXT NOT NULL CHECK (role IN ('analyst','steward','administrator')),
    is_demo INTEGER NOT NULL DEFAULT 1 CHECK (is_demo = 1)
) STRICT;

CREATE TABLE review_task (
    task_id INTEGER PRIMARY KEY,
    observation_id INTEGER NOT NULL UNIQUE REFERENCES price_observation(observation_id),
    assigned_user_id INTEGER NOT NULL REFERENCES app_user(user_id),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_review','resolved')),
    version INTEGER NOT NULL DEFAULT 0 CHECK (version >= 0),
    note TEXT NOT NULL DEFAULT ''
) STRICT;

CREATE TRIGGER review_version_increment BEFORE UPDATE ON review_task
WHEN NEW.version != OLD.version + 1
BEGIN SELECT RAISE(ABORT, 'A task update must increment version by exactly one'); END;

CREATE VIEW published_prices AS
SELECT o.observation_id, p.period, i.label AS item, g.name AS geography,
       g.level, o.price_kobo, o.price_kobo / 100.0 AS price_ngn,
       p.resource_id, p.workbook_name, o.source_sheet, o.source_cell
FROM price_observation AS o
JOIN publication AS p ON p.publication_id = o.publication_id
JOIN item AS i ON i.item_id = o.item_id
JOIN geography AS g ON g.geography_id = o.geography_id;
