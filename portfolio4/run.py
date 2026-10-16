"""Portfolio 4: real TinyDB document storage, queries, CRUD and reconciliation.

Populated JSON storage is local-only. Exported evidence contains counts,
hashes and fictional workflow records, never source price arrays.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
from importlib.metadata import version
import json
from pathlib import Path
import re
import sqlite3
import platform
from tinydb import TinyDB, Query

PREFIX = 'Ezenduka_Chukwubuikem_301913360'
ROOT = Path(__file__).resolve().parent.parent
FOCUS = 'Rice Local, short-Grained'
ZONES = {'NORTH CENTRAL', 'NORTH EAST', 'NORTH WEST', 'SOUTH EAST', 'SOUTH SOUTH', 'SOUTH WEST'}
SOURCE_SQL = '''SELECT p.period, i.label, g.name, g.level, o.price_kobo,
o.observation_id, o.source_sheet, o.source_cell, p.resource_id,
p.workbook_name, p.workbook_sha256, r.download_url, r.sha256, pub.name
FROM price_observation o JOIN publication p USING(publication_id)
JOIN item i USING(item_id) JOIN geography g USING(geography_id)
JOIN source_resource r USING(resource_id) JOIN publisher pub USING(publisher_id)
ORDER BY p.period, i.label, g.name'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def document_key(period, label):
    return fingerprint([period, label])


def validate_document(doc):
    """Application validation; TinyDB itself does not enforce this schema."""
    require(type(doc) is dict, 'Document must be a dictionary')
    require(type(doc.get('schema_version')) is int and doc['schema_version'] == 1, 'Unsupported schema version')
    require(isinstance(doc.get('period'), str) and
            re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', doc['period']), 'Invalid period')
    require(isinstance(doc.get('item'), dict), 'Missing item object')
    label = doc['item'].get('label')
    require(isinstance(label, str) and label.strip() == label and bool(label), 'Invalid exact item label')
    require(doc.get('document_key') == document_key(doc['period'], label), 'Invalid document key')
    provenance = doc.get('provenance')
    require(isinstance(provenance, dict), 'Missing provenance')
    for field in ('publisher', 'download_url', 'workbook_name'):
        require(isinstance(provenance.get(field), str) and bool(provenance[field]), 'Missing ' + field)
    require(type(provenance.get('resource_id')) is int and provenance['resource_id'] > 0, 'Invalid resource ID')
    for field in ('resource_sha256', 'workbook_sha256'):
        require(isinstance(provenance.get(field), str) and
                re.fullmatch('[0-9a-f]{64}', provenance[field]), 'Invalid provenance hash')
    observations = doc.get('observations')
    require(isinstance(observations, list) and 1 <= len(observations) <= 7, 'Need one to seven observations')
    geographies, ids = set(), set()
    for obs in observations:
        require(isinstance(obs, dict), 'Invalid observation object')
        name, level = obs.get('geography'), obs.get('level')
        require((name == 'Nigeria' and level == 'national') or
                (name in ZONES and level == 'zone'), 'Invalid geography/level')
        require(name not in geographies, 'Duplicate geography in item/month')
        geographies.add(name)
        require(type(obs.get('price_kobo')) is int and obs['price_kobo'] > 0, 'Price must be positive integer kobo')
        require(type(obs.get('observation_id')) is int and obs['observation_id'] > 0, 'Invalid observation ID')
        require(obs['observation_id'] not in ids, 'Duplicate observation ID')
        ids.add(obs['observation_id'])
        for field in ('source_sheet', 'source_cell'):
            require(isinstance(obs.get(field), str) and bool(obs[field].strip()), 'Missing source cell/sheet')


def build_documents(rows):
    grouped = {}
    for row in rows:
        period, label, geography, level, price, oid, sheet, cell, rid, workbook, whash, url, rhash, publisher = row
        key = document_key(period, label)
        provenance = dict(publisher=publisher, resource_id=rid, download_url=url,
                          resource_sha256=rhash, workbook_name=workbook, workbook_sha256=whash)
        if key not in grouped:
            grouped[key] = dict(schema_version=1, document_key=key, period=period,
                                item={'label': label}, provenance=provenance, observations=[])
        require(grouped[key]['provenance'] == provenance, 'Conflicting source within item/month')
        grouped[key]['observations'].append(dict(observation_id=oid, geography=geography,
            level=level, price_kobo=price, source_sheet=sheet, source_cell=cell))
    docs = list(grouped.values())
    for doc in docs:
        validate_document(doc)
    return docs


def flatten(documents):
    rows = []
    for doc in documents:
        p = doc['provenance']
        for obs in doc['observations']:
            rows.append((doc['period'], doc['item']['label'], obs['geography'], obs['level'],
                         obs['price_kobo'], obs['observation_id'], obs['source_sheet'], obs['source_cell'],
                         p['resource_id'], p['workbook_name'], p['workbook_sha256'], p['download_url'],
                         p['resource_sha256'], p['publisher']))
    return sorted(rows, key=lambda r: r[:3])


def import_snapshots(table, documents):
    require(len(table) == 0, 'Import requires an empty snapshot table')
    keys, observation_ids = set(), set()
    for doc in documents:
        validate_document(doc)
        require(doc['document_key'] not in keys, 'Duplicate item/month document key')
        keys.add(doc['document_key'])
        for observation in doc['observations']:
            oid = observation['observation_id']
            require(oid not in observation_ids, 'Repeated observation ID across documents')
            observation_ids.add(oid)
    return table.insert_multiple(documents)


def query_cases(table):
    d, o = Query(), Query()
    return {
        'D01_December_focus': table.search((d.period == '2025-12') & (d.item.label == FOCUS)),
        'D02_December_with_national': table.search((d.period == '2025-12') &
                                                d.observations.any(o.level == 'national')),
        'D03_without_national': table.search(~d.observations.any(o.level == 'national')),
        'D04_without_zones': table.search(~d.observations.any(o.level == 'zone')),
        # Both predicates must hold on the SAME observation, not two different elements.
        'D05_national_at_least_100000_kobo': table.search(d.observations.any(
            (o.geography == 'Nigeria') & (o.price_kobo >= 100000))),
        'D06_focus_all_months': table.search(d.item.label == FOCUS),
    }


def create_review(snapshots, reviews, key, note):
    require(snapshots.contains(Query().document_key == key), 'Referenced snapshot is missing')
    require(isinstance(note, str) and note.startswith('DEMO:'), 'Fictional review must be labelled DEMO:')
    return reviews.insert({'document_key': key, 'status': 'open', 'note': note, 'is_demo': True})


def update_review(reviews, review_id, status, note, checks):
    require(status in ('open', 'in_review', 'resolved'), 'Invalid review status')
    require(isinstance(note, str) and note.startswith('DEMO:'), 'Fictional review must be labelled DEMO:')
    require(isinstance(checks, list) and all(isinstance(c, str) for c in checks), 'Invalid checklist')
    require(reviews.contains(doc_id=review_id), 'Review not found')
    return reviews.update({'status': status, 'note': note, 'checks': checks}, doc_ids=[review_id])


def fictional_example():
    """Complete valid example with invented prices; never presented as NBS data."""
    label, period = 'Fictional training item', '2099-01'
    return {'schema_version': 1, 'document_key': document_key(period, label), 'period': period,
            'item': {'label': label}, 'provenance': {
                'publisher': 'FICTIONAL TRAINING FIXTURE - NOT NBS', 'resource_id': 1,
                'download_url': 'https://example.invalid/fictional', 'resource_sha256': 'a' * 64,
                'workbook_name': 'fictional.xlsx', 'workbook_sha256': 'b' * 64},
            'observations': [dict(observation_id=1, geography='Nigeria', level='national',
                                 price_kobo=10000, source_sheet='Fictional', source_cell='B2'),
                             dict(observation_id=2, geography='NORTH CENTRAL', level='zone',
                                 price_kobo=20000, source_sheet='Fictional', source_cell='C2')]}


def run(database, workspace, evidence_dir=None):
    database = database.resolve()
    require(database.is_file(), 'Build Portfolio 1 or supply --database')
    require(not Path(str(database) + '-wal').exists(), 'Close source writers/checkpoint WAL first')
    initial_hash = file_hash(database)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    local = workspace.resolve() / ('portfolio4_' + stamp)
    local.mkdir(parents=True, exist_ok=False)
    storage = local / 'food_price_documents_LOCAL_ONLY.json'
    conn = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    try:
        require(conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Invalid source')
        require(not conn.execute('PRAGMA foreign_key_check').fetchall(), 'Source FK failure')
        rows = conn.execute(SOURCE_SQL).fetchall()
        documents = build_documents(rows)
        with TinyDB(storage, ensure_ascii=False, indent=2) as db:
            snapshots = db.table('monthly_items', cache_size=0)
            import_snapshots(snapshots, documents)
        # Real close/reopen of JSONStorage, not just an in-memory dictionary comparison.
        with TinyDB(storage) as db:
            snapshots = db.table('monthly_items', cache_size=0)
            actual_rows = flatten(snapshots.all())
            require(actual_rows == rows, 'Persisted documents differ from source observations/provenance')
            results = query_cases(snapshots)
            sql_reference = {
                'D01_December_focus': ("p.period='2025-12' AND i.label=?", (FOCUS,)),
                'D02_December_with_national': ("p.period='2025-12' AND g.level='national'", ()),
                'D03_without_national': ("NOT EXISTS (SELECT 1 FROM price_observation x JOIN geography gx "
                    "USING(geography_id) WHERE x.publication_id=o.publication_id AND x.item_id=o.item_id AND gx.level='national')", ()),
                'D04_without_zones': ("NOT EXISTS (SELECT 1 FROM price_observation x JOIN geography gx "
                    "USING(geography_id) WHERE x.publication_id=o.publication_id AND x.item_id=o.item_id AND gx.level='zone')", ()),
                'D05_national_at_least_100000_kobo': ("g.name='Nigeria' AND o.price_kobo>=100000", ()),
                'D06_focus_all_months': ('i.label=?', (FOCUS,)),
            }
            summaries = {}
            for name, matches in results.items():
                predicate, params = sql_reference[name]
                sql = ('SELECT DISTINCT p.period,i.label FROM price_observation o '
                       'JOIN publication p USING(publication_id) JOIN item i USING(item_id) '
                       'JOIN geography g USING(geography_id) WHERE ' + predicate + ' ORDER BY p.period,i.label')
                expected = conn.execute(sql, params).fetchall()
                actual = sorted((d['period'], d['item']['label']) for d in matches)
                require(actual == expected, 'SQL oracle mismatch for ' + name)
                summaries[name] = {'matched_documents': len(matches), 'identity_sha256': fingerprint(actual),
                                   'sqlite_reference_matched': True, 'reference_sql': sql,
                                   'parameters': list(params)}
            before_digest = fingerprint(snapshots.all())
            reviews = db.table('demo_reviews', cache_size=0)
            key = results['D01_December_focus'][0]['document_key']
            rid = create_review(snapshots, reviews, key, 'DEMO: inspect this monthly item')
            created = dict(reviews.get(doc_id=rid))
            changed = update_review(reviews, rid, 'resolved', 'DEMO: illustrative local review complete',
                                    ['provenance', 'regional coverage'])
            require(changed == [rid], 'Expected one updated review')
            updated = dict(reviews.get(doc_id=rid))
            draft = create_review(snapshots, reviews, key, 'DEMO: temporary draft to delete')
            removed = reviews.remove(doc_ids=[draft])
            require(removed == [draft] and not reviews.contains(doc_id=draft), 'Delete failed')
            require(fingerprint(snapshots.all()) == before_digest, 'Review CRUD changed price snapshots')
            monthly = Counter(d['period'] for d in snapshots)
            sizes = Counter(len(d['observations']) for d in snapshots)
        with TinyDB(storage) as db:
            require(dict(db.table('demo_reviews').get(doc_id=rid)) == updated, 'Updated review not persisted')
            require(len(db.table('demo_reviews')) == 1, 'Deleted draft returned after reopen')
            require(flatten(db.table('monthly_items').all()) == rows, 'Final snapshots changed')
    finally:
        conn.close()
    require(file_hash(database) == initial_hash, 'Original database changed')
    evidence = {'run_id': stamp, 'engine': 'TinyDB', 'tinydb_version': version('tinydb'),
        'python_version': platform.python_version(), 'sqlite_reference_version': sqlite3.sqlite_version,
        'source_sha256_before': initial_hash, 'source_sha256_after': file_hash(database),
        'runner_sha256': file_hash(Path(__file__)), 'storage': 'JSONStorage; one local writer; cache_size=0',
        'source_rows': len(rows), 'documents': len(documents), 'documents_per_month': dict(sorted(monthly.items())),
        'document_sizes': dict(sorted(sizes.items())), 'flattened_source_sha256': fingerprint(rows),
        'flattened_persisted_sha256': fingerprint(actual_rows), 'all_source_fields_reconciled': True,
        'queries': summaries, 'demo_crud': {'created': created, 'updated': updated,
            'temporary_draft_deleted': True, 'persisted_after_reopen': True, 'snapshot_unchanged': True},
        'limitations': ['No ACID or multi-client safety claim', 'No native indexes or foreign-key enforcement',
                        'Schema, uniqueness and references are checked by application code only']}
    out = evidence_dir.resolve() if evidence_dir else local / 'evidence'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'nosql_evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    example = fictional_example()
    validate_document(example)
    (out / 'fictional_document_example.json').write_text(json.dumps(example, indent=2), encoding='utf-8')
    lines = ['# Portfolio 4: actual NoSQL results', '', 'Run: `' + stamp + '`', '',
             f"TinyDB {version('tinydb')}; {len(documents)} persisted item/month documents; {len(rows)} reconciled observations.",
             '', '| Query | Matching documents | Independent SQL check |', '|---|---:|---|']
    lines += [f'| {name} | {result["matched_documents"]} | PASS |' for name, result in summaries.items()]
    lines += ['', 'All original source fields, including provenance, matched after closing and reopening storage.',
              'Fictional review insert/read/update/delete and persistence checks passed; snapshot documents were unchanged.',
              'The original SQLite file hash is unchanged. Full checksums and reference SQL are in the JSON evidence.']
    (out / 'nosql_evidence.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    preview = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Portfolio 4 — Document Database</title>
<style>body{max-width:1040px;margin:40px auto;padding:0 22px;font:17px/1.6 system-ui;color:#183048;background:#f5f8fc}section{background:white;padding:24px;border:1px solid #d5dfeb;border-radius:12px;margin:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #ddd}</style>
<h1>Portfolio 4: document database</h1><p>Ezenduka Chukwubuikem · 301913360 · Nigeria Food Price Observatory</p>
<section><h2>Model structure</h2><pre>Portfolio 1 relational data (read-only)\n       ↓ group by month + exact item label\nTinyDB monthly_items\n  ├─ identity: document_key, schema_version\n  ├─ period + item label\n  ├─ publication provenance\n  └─ observations[]: geography, level, integer kobo, source cell\n\nTinyDB demo_reviews → document_key reference\n  └─ fictional note, status, optional checklist</pre></section>'''
    preview += '<section><h2>Verified query results</h2><p>Run ' + stamp + '</p><table><tr><th>Query</th><th>Documents</th><th>SQL check</th></tr>'
    for name, result in summaries.items():
        preview += '<tr><td>' + html.escape(name) + '</td><td>' + str(result['matched_documents']) + '</td><td>PASS</td></tr>'
    preview += '</table><p>' + str(len(documents)) + ' documents preserve all ' + str(len(rows)) + ' source observations and provenance fields.</p></section>'
    preview += '<section><h2>Fictional document example — not NBS prices</h2><pre>' + html.escape(json.dumps(example, indent=2)) + '</pre></section>'
    preview += '<section><h2>Single-writer CRUD evidence</h2><pre>' + html.escape(json.dumps(evidence['demo_crud'], indent=2)) + '</pre></section>'
    preview += '<p>This is an actual embedded NoSQL implementation. It does not provide production concurrency, native indexes or ACID guarantees.</p></html>'
    (out / 'evidence_preview.html').write_text(preview, encoding='utf-8')
    print(json.dumps({'run_id': stamp, 'documents': len(documents), 'observations': len(rows),
                      'query_matches': {k: v['matched_documents'] for k, v in summaries.items()},
                      'reconciled': True, 'crud_verified': True, 'source_unchanged': True}, indent=2))
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT / '.local' / f'{PREFIX}_Food_Prices.sqlite3')
    parser.add_argument('--workspace', type=Path, default=ROOT / '.local')
    parser.add_argument('--evidence-dir', type=Path)
    args = parser.parse_args()
    run(args.database, args.workspace, args.evidence_dir)
