"""Local replication, recovery and shard exercise, not a deployed cluster.

One primary/one replica are independent SQLite files in one process. A paused
worker and availability flags simulate outages; there is no real network fault.
Only aggregate and fictional workflow evidence is exported.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import platform
import sqlite3

PREFIX = 'Ezenduka_Chukwubuikem_301913360'
ROOT = Path(__file__).resolve().parent.parent
EXTENSION = '''
CREATE TABLE demo_replication_log(
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 task_id INTEGER NOT NULL, previous_version INTEGER NOT NULL,
 new_version INTEGER NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL,
 CHECK(new_version=previous_version+1)
) STRICT;
CREATE TABLE demo_replica_progress(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 applied_sequence INTEGER NOT NULL CHECK(applied_sequence>=0)) STRICT;
INSERT INTO demo_replica_progress VALUES(1,0);
'''
PROJECTION = '''SELECT o.observation_id,p.period,i.label,g.name,g.level,o.price_kobo,
o.source_sheet,o.source_cell,p.resource_id,p.workbook_name,p.workbook_sha256,
r.download_url,r.sha256 FROM price_observation o
JOIN publication p USING(publication_id) JOIN item i USING(item_id)
JOIN geography g USING(geography_id) JOIN source_resource r USING(resource_id)
ORDER BY o.observation_id'''
SHARD_SCHEMA = '''CREATE TABLE observations(
 observation_id INTEGER PRIMARY KEY, period TEXT NOT NULL, item_label TEXT NOT NULL,
 geography TEXT NOT NULL, level TEXT NOT NULL, price_kobo INTEGER NOT NULL,
 source_sheet TEXT NOT NULL, source_cell TEXT NOT NULL, resource_id INTEGER NOT NULL,
 workbook_name TEXT NOT NULL, workbook_sha256 TEXT NOT NULL,
 download_url TEXT NOT NULL, resource_sha256 TEXT NOT NULL
) STRICT;'''


class Unavailable(RuntimeError):
    pass


class Conflict(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connect(path, readonly=False):
    db = sqlite3.connect(path.resolve().as_uri() + ('?mode=ro' if readonly else '?mode=rw'),
                         uri=True, isolation_level=None)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA synchronous=FULL')
    return db


def backup(source, destination):
    require(not destination.exists(), 'Refusing to replace an existing backup/database')
    target = sqlite3.connect(destination, isolation_level=None)
    try:
        source.backup(target)
        require(target.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Invalid backup')
        require(not target.execute('PRAGMA foreign_key_check').fetchall(), 'Backup FK failure')
    finally:
        target.close()


def state(db):
    row = db.execute('SELECT version,status,note FROM review_task WHERE task_id=1').fetchone()
    return dict(zip(('version', 'status', 'note'), row))


def checkpoint(db):
    return db.execute('SELECT applied_sequence FROM demo_replica_progress WHERE singleton=1').fetchone()[0]


def latest(db):
    return db.execute('SELECT coalesce(max(sequence),0) FROM demo_replication_log').fetchone()[0]


def write_primary(db, expected_version, note, status='in_review', available=True):
    if not available:
        raise Unavailable('Primary unavailable: writes are not redirected to the replica')
    require(not db.in_transaction, 'Write helper owns its transaction')
    require(note.startswith('DEMO:'), 'Workflow note must be explicitly fictional')
    try:
        db.execute('BEGIN IMMEDIATE')
        count = db.execute('UPDATE review_task SET note=?,status=?,version=version+1 '
                           'WHERE task_id=1 AND version=?', (note, status, expected_version)).rowcount
        if count != 1:
            raise Conflict('Stale primary edit')
        seq = db.execute('INSERT INTO demo_replication_log(task_id,previous_version,new_version,status,note) '
                         'VALUES(1,?,?,?,?)', (expected_version, expected_version + 1, status, note)).lastrowid
        db.execute('COMMIT')
        return seq
    except Exception:
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise


def replicate(primary, replica, fail_after=None):
    """Apply pending events and watermark atomically. Single worker only."""
    require(not primary.in_transaction and not replica.in_transaction, 'Unexpected open transaction')
    progress = checkpoint(replica)
    events = primary.execute('SELECT sequence,task_id,previous_version,new_version,status,note '
                             'FROM demo_replication_log WHERE sequence>? ORDER BY sequence', (progress,)).fetchall()
    try:
        replica.execute('BEGIN IMMEDIATE')
        for index, (seq, task_id, previous, new, status, note) in enumerate(events, 1):
            require(seq == progress + 1, 'Replication log gap; refusing silent data loss')
            require(new == previous + 1, 'Invalid version transition')
            count = replica.execute('UPDATE review_task SET version=?,status=?,note=? '
                                    'WHERE task_id=? AND version=?', (new, status, note, task_id, previous)).rowcount
            require(count == 1, 'Replica diverged; refusing overwrite')
            if fail_after == index:
                raise RuntimeError('Injected worker failure before checkpoint')
            replica.execute('UPDATE demo_replica_progress SET applied_sequence=? WHERE singleton=1', (seq,))
            progress = seq
        replica.execute('COMMIT')
        return len(events)
    except Exception:
        if replica.in_transaction:
            replica.execute('ROLLBACK')
        raise


def read_review(primary, replica, minimum_sequence, strict=True, primary_available=True):
    applied = checkpoint(replica)
    if applied >= minimum_sequence:
        return {'route': 'replica', 'satisfies_minimum': True, 'applied_sequence': applied, 'task': state(replica)}
    if strict:
        if not primary_available:
            raise Unavailable('Replica is behind required sequence and primary is unavailable')
        require(latest(primary) >= minimum_sequence, 'Requested future sequence is unavailable')
        return {'route': 'primary', 'satisfies_minimum': True, 'applied_sequence': latest(primary), 'task': state(primary)}
    return {'route': 'replica', 'satisfies_minimum': False, 'applied_sequence': applied, 'task': state(replica)}


def shard_for(period):
    # This exercise deliberately routes only the imported 2025 snapshot.
    require(isinstance(period, str) and len(period) == 7 and period[:5] == '2025-' and
            period[5:].isdigit() and 1 <= int(period[5:]) <= 12, 'Period outside configured shard map')
    return 0 if int(period[5:]) <= 6 else 1


def read_shards(paths):
    if not all(path.is_file() for path in paths):
        raise Unavailable('A required shard is missing: refusing a partial global result')
    rows = []
    for path in paths:
        db = connect(path, readonly=True)
        try:
            rows.extend(db.execute('SELECT * FROM observations ORDER BY observation_id').fetchall())
        finally:
            db.close()
    return sorted(rows)


def run(database, workspace, evidence_dir=None):
    database = database.resolve()
    require(database.is_file(), 'Build Portfolio 1 or provide --database')
    require(not Path(str(database) + '-wal').exists(), 'Close source writers/checkpoint source WAL first')
    original_hash = file_hash(database)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    local = workspace.resolve() / ('portfolio5_' + stamp)
    local.mkdir(parents=True, exist_ok=False)
    source = connect(database, readonly=True)
    try:
        rows = source.execute(PROJECTION).fetchall()
        require(len(rows) == 3528, 'Expected original Portfolio 1 dataset')
        backup(source, local / 'primary.sqlite3')
    finally:
        source.close()
    primary = connect(local / 'primary.sqlite3')
    replica = None
    events = []
    def record(name, **values):
        events.append({'case': name, 'passed': True, **values})
    try:
        require(primary.execute('SELECT count(*) FROM review_task').fetchone()[0] == 0,
                'Expected source without workflow edits')
        primary.executescript(EXTENSION)
        oid = primary.execute('SELECT min(observation_id) FROM price_observation').fetchone()[0]
        uid = primary.execute('SELECT min(user_id) FROM app_user').fetchone()[0]
        primary.execute('INSERT INTO review_task(task_id,observation_id,assigned_user_id,note) '
                        'VALUES(1,?,?,?)', (oid, uid, 'DEMO: initial review'))
        backup(primary, local / 'replica.sqlite3')
        replica = connect(local / 'replica.sqlite3')
        require(state(primary) == state(replica) and checkpoint(replica) == 0, 'Initial mismatch')
        record('S01_initial_snapshot', primary=state(primary), replica=state(replica), checkpoint=0)

        write_primary(primary, 0, 'DEMO: source header checked')
        acknowledged = write_primary(primary, 1, 'DEMO: label checked')
        stale = read_review(primary, replica, acknowledged, strict=False)
        fresh = read_review(primary, replica, acknowledged, strict=True)
        require(not stale['satisfies_minimum'] and stale['task']['version'] == 0, 'Expected stale replica')
        require(fresh['route'] == 'primary' and fresh['task']['version'] == 2, 'Fresh route incorrect')
        record('S02_paused_worker_stale_read', acknowledged_sequence=acknowledged,
               pending_events=latest(primary)-checkpoint(replica), eventual_read=stale, strict_read=fresh)

        refusals = []
        for operation in ('strict_read', 'write'):
            try:
                if operation == 'strict_read':
                    read_review(primary, replica, acknowledged, strict=True, primary_available=False)
                else:
                    write_primary(primary, 2, 'DEMO: unavailable write', available=False)
            except Unavailable as error:
                refusals.append({'operation': operation, 'message': str(error)})
            else:
                raise AssertionError('Operation should refuse unavailable primary')
        eventual = read_review(primary, replica, acknowledged, strict=False, primary_available=False)
        require(latest(primary) == 2 and eventual['task']['version'] == 0, 'Unexpected write/stale state')
        record('S03_simulated_primary_outage', refused=refusals, labelled_stale_read=eventual,
               replica_promoted=False)

        applied = replicate(primary, replica)
        require(applied == 2 and checkpoint(replica) == 2 and state(primary) == state(replica), 'Catch-up mismatch')
        repeated = replicate(primary, replica)
        require(repeated == 0 and state(replica)['version'] == 2, 'Duplicate replay changed state')
        record('S04_catch_up_and_repeat', applied_events=applied, repeat_applied_events=repeated,
               checkpoint=checkpoint(replica), task=state(replica))

        write_primary(primary, 2, 'DEMO: reconciled note')
        before, before_checkpoint = state(replica), checkpoint(replica)
        try:
            replicate(primary, replica, fail_after=1)
        except RuntimeError as error:
            require('Injected worker failure' in str(error), 'Unexpected worker error')
            failure = str(error)
        else:
            raise AssertionError('Injected failure did not occur')
        require(state(replica) == before and checkpoint(replica) == before_checkpoint,
                'Worker failure left partial data or checkpoint')
        require(replicate(primary, replica) == 1 and checkpoint(replica) == 3, 'Recovery replay failed')
        record('S05_worker_failure_and_retry', error=failure, rolled_back_task=before,
               rolled_back_checkpoint=before_checkpoint, recovered_task=state(replica), recovered_checkpoint=3)

        backup(primary, local / 'backup_at_sequence3.sqlite3')
        write_primary(primary, 3, 'DEMO: later acknowledged edit', status='resolved')
        backup_db = connect(local / 'backup_at_sequence3.sqlite3', readonly=True)
        try:
            backup(backup_db, local / 'restored.sqlite3')
        finally:
            backup_db.close()
        restored = connect(local / 'restored.sqlite3', readonly=True)
        try:
            lost = latest(primary)-latest(restored)
            require(lost == 1 and state(restored)['version'] == 3, 'Recovery point mismatch')
            require(restored.execute(PROJECTION).fetchall() == rows, 'Restored source rows differ')
            record('S06_restore_recovery_point', primary_sequence=latest(primary),
                   backup_sequence=latest(restored), acknowledged_edits_absent_from_restore=lost,
                   restored_task=state(restored), restored_source_observations=len(rows))
        finally:
            restored.close()
        require(replicate(primary, replica) == 1 and state(primary) == state(replica), 'Final catch-up failed')
        for db in (primary, replica):
            require(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Integrity failure')
            require(not db.execute('PRAGMA foreign_key_check').fetchall(), 'FK failure')
            require(db.execute(PROJECTION).fetchall() == rows, 'Source data changed in node')
    finally:
        primary.close()
        if replica is not None:
            replica.close()

    paths = [local/'shard_jan_jun.sqlite3', local/'shard_jul_dec.sqlite3']
    counts = []
    for index, path in enumerate(paths):
        db = sqlite3.connect(path)
        try:
            db.executescript(SHARD_SCHEMA)
            selected = [row for row in rows if shard_for(row[1]) == index]
            db.executemany('INSERT INTO observations VALUES(' + ','.join('?' for _ in range(13)) + ')', selected)
            db.commit()
            counts.append(db.execute('SELECT count(*) FROM observations').fetchone()[0])
            require(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Shard integrity failure')
        finally:
            db.close()
    combined = read_shards(paths)
    require(combined == rows, 'Shard union differs from original projection')
    require(len({row[0] for row in combined}) == len(rows), 'Shard overlap or duplicate IDs')
    record('S07_month_range_shards', shard_observations=counts, total_observations=len(combined),
           source_projection_sha256=digest(rows), shard_union_sha256=digest(combined),
           january_route=shard_for('2025-01'), december_route=shard_for('2025-12'),
           exact_union=True, no_overlap=True)
    try:
        read_shards([paths[0], local/'unavailable_shard.sqlite3'])
    except Unavailable as error:
        record('S08_missing_shard_refusal', message=str(error), partial_result_reported_as_complete=False)
    else:
        raise AssertionError('Missing shard should prevent global result')
    require(file_hash(database) == original_hash, 'Original database changed')
    evidence = {'run_id': stamp, 'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
        'scope': 'Local single-process simulation with independent SQLite files; no cloud/network deployment',
        'source_sha256_before': original_hash, 'source_sha256_after': file_hash(database),
        'runner_sha256': file_hash(Path(__file__)), 'source_observations': len(rows),
        'passed_cases': len(events), 'cases': events}
    out = evidence_dir.resolve() if evidence_dir else local/'evidence'
    out.mkdir(parents=True, exist_ok=True)
    (out/f'{PREFIX}_Distributed_Evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    lines = ['# Portfolio 5: executed local exercise', '', 'Run: `' + stamp + '`', '', evidence['scope'], '']
    for case in events:
        lines += ['## ' + case['case'], '', '**PASS**', '', '```json', json.dumps(case, indent=2), '```', '']
    (out/f'{PREFIX}_Distributed_Evidence.md').write_text('\n'.join(lines), encoding='utf-8')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Portfolio 5 evidence</title>
<style>body{max-width:1000px;margin:40px auto;padding:0 22px;font:17px/1.6 system-ui;color:#183048;background:#f5f8fc}section{padding:24px;background:white;border:1px solid #c8d7e5;border-radius:12px;margin:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}</style>
<h1>Portfolio 5: replication, recovery and sharding</h1><p>Local controlled exercise, not a cloud deployment.</p>
<section><h2>Implemented data flow</h2><pre>Original source (unchanged)\n  → Primary copy + atomic review event log\n      → Explicit replication worker → Replica + applied sequence\n      → Backup at sequence 3 → restored copy\n  → Month-range projection → Jan–Jun shard + Jul–Dec shard</pre></section>'''
    for case in events:
        page += '<section><h2>' + html.escape(case['case']) + '</h2><pre>' + html.escape(json.dumps(case, indent=2)) + '</pre></section>'
    page += '</html>'
    (out/f'{PREFIX}_Evidence_Preview.html').write_text(page, encoding='utf-8')
    print(json.dumps({'run_id': stamp, 'passed_cases': len(events), 'shard_counts': counts,
                     'source_unchanged': True, 'scope': evidence['scope']}, indent=2))
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT/'.local'/f'{PREFIX}_Food_Prices.sqlite3')
    parser.add_argument('--workspace', type=Path, default=ROOT/'.local')
    parser.add_argument('--evidence-dir', type=Path)
    args = parser.parse_args()
    run(args.database, args.workspace, args.evidence_dir)
