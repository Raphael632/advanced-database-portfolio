"""Portfolio 3: reproducible two-connection transaction experiments.

Only a new private copy is changed. Review tasks are fictional demonstrations.
No raw price rows are exported. Standard library only; Python >= 3.12.
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
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UPDATE = ('UPDATE review_task SET note=?, status=?, version=version+1 '
          'WHERE task_id=?')
GUARDED = UPDATE + ' AND version=?'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task(db, key):
    row = db.execute('SELECT status,version,note FROM review_task WHERE task_id=?',
                     (key,)).fetchone()
    return None if row is None else dict(zip(('status', 'version', 'note'), row))


def guarded_edit(db, key, expected_version, note, status):
    """Own a short transaction. Return False on a stale edit; never overwrite it."""
    require(not db.in_transaction, 'guarded_edit needs a connection without an active transaction')
    try:
        db.execute('BEGIN IMMEDIATE')
        changed = db.execute(GUARDED, (note, status, key, expected_version)).rowcount
        require(changed in (0, 1), 'Unexpected affected-row count')
        db.execute('COMMIT' if changed == 1 else 'ROLLBACK')
        return changed == 1
    except Exception:
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise


def run(database, workspace, evidence_dir=None):
    database = database.resolve()
    require(database.is_file(), 'Build Portfolio 1 first or pass --database')
    require(not Path(str(database) + '-wal').exists(), 'Close source writers and checkpoint source WAL first')
    source_hash = digest(database)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    local = workspace.resolve() / ('portfolio3_' + stamp)
    local.mkdir(parents=True, exist_ok=False)
    copy = local / 'review_experiments.sqlite3'
    source = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    seed = sqlite3.connect(copy, isolation_level=None)
    try:
        require(source.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Invalid source')
        require(not source.execute('PRAGMA foreign_key_check').fetchall(), 'Source FK failure')
        source.backup(seed)
        require(seed.execute('SELECT count(*) FROM review_task').fetchone()[0] == 0,
                'Expected pristine Portfolio 1 source with no review tasks')
        require(seed.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal', 'WAL unavailable')
    finally:
        seed.close()
        source.close()

    cases = []
    current = None
    def connect(label):
        db = sqlite3.connect(copy, isolation_level=None, timeout=0)
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA read_uncommitted=OFF')
        db.execute('PRAGMA busy_timeout=0')
        db.execute('PRAGMA synchronous=FULL')
        def trace(sql):
            if current is not None:
                current['sql_trace'].append({'connection': label, 'sql': sql})
        db.set_trace_callback(trace)
        return db

    a, b = connect('A'), connect('B')
    def begin_case(name):
        nonlocal current
        require(not a.in_transaction and not b.in_transaction, 'Leaked transaction between cases')
        current = {'case': name, 'steps': [], 'sql_trace': []}
        cases.append(current)

    def record(event, **values):
        current['steps'].append({'event': event, **values})

    def expect_error(db, sql, parameters, code):
        try:
            db.execute(sql, parameters)
        except sqlite3.Error as error:
            record('Expected database error', code=error.sqlite_errorcode,
                   name=error.sqlite_errorname, message=str(error))
            require(error.sqlite_errorcode == code, f'Expected error code {code}')
        else:
            raise AssertionError('Expected database error did not occur')

    try:
        observations = [r[0] for r in a.execute(
            'SELECT observation_id FROM price_observation ORDER BY observation_id LIMIT 9')]
        require(len(observations) == 9, 'Need at least nine source observations')
        user = a.execute('SELECT user_id FROM app_user ORDER BY user_id LIMIT 1').fetchone()[0]
        require(a.execute('SELECT count(*) FROM price_observation').fetchone()[0] == 3528,
                'This captured exercise expects the Portfolio 1 dataset')
        # Each case gets its own fictional workflow task; no source prices are changed.
        for key, observation in enumerate(observations, 1):
            a.execute('INSERT INTO review_task(task_id,observation_id,assigned_user_id,note) '
                      'VALUES(?,?,?,?)', (key, observation, user, 'DEMO: initial review'))

        begin_case('T01_commit_and_reopen')
        a.execute('BEGIN IMMEDIATE')
        a.execute(UPDATE, ('DEMO: checked provenance', 'in_review', 1))
        record('Before commit', writer=task(a, 1), other_reader=task(b, 1))
        require(task(a, 1)['version'] == 1 and task(b, 1)['version'] == 0,
                'Uncommitted edit leaked across connections')
        a.execute('COMMIT')
        reopened = connect('C_reopened')
        try:
            record('Committed row visible on new connection', row=task(reopened, 1))
            require(task(reopened, 1)['version'] == 1, 'Committed update missing after reopen')
        finally:
            reopened.close()
        current['passed'] = True

        begin_case('T02_atomic_rollback_on_constraint_failure')
        before = [task(b, key) for key in (2, 3)]
        a.execute('BEGIN IMMEDIATE')
        a.execute(UPDATE, ('DEMO: first operation succeeds', 'in_review', 2))
        expect_error(a, UPDATE, ('DEMO: invalid second operation', 'invalid_status', 3),
                     sqlite3.SQLITE_CONSTRAINT_CHECK)
        record('Statement failure alone leaves transaction active',
               in_transaction=a.in_transaction, first_operation=task(a, 2))
        require(a.in_transaction and task(a, 2)['version'] == 1,
                'Expected first statement to remain pending after ABORT')
        a.execute('ROLLBACK')
        after = [task(b, key) for key in (2, 3)]
        record('Explicit rollback restores both tasks', before=before, after=after)
        require(before == after, 'Rollback did not restore whole unit of work')
        current['passed'] = True

        begin_case('T03_savepoint_partial_rollback')
        a.execute('BEGIN IMMEDIATE')
        a.execute(UPDATE, ('DEMO: keep this check', 'in_review', 3))
        a.execute('SAVEPOINT optional_note')
        a.execute(UPDATE, ('DEMO: discard this optional note', 'resolved', 3))
        require(task(a, 3)['version'] == 2, 'Inner update missing')
        a.execute('ROLLBACK TO optional_note')
        a.execute('RELEASE optional_note')
        a.execute('COMMIT')
        record('Outer edit retained; optional edit undone', row=task(b, 3))
        require(task(b, 3) == {'status': 'in_review', 'version': 1,
                             'note': 'DEMO: keep this check'}, 'Savepoint result incorrect')
        current['passed'] = True

        begin_case('T04_stale_form_overwrite_without_guard')
        old_a, old_b = task(a, 4), task(b, 4)
        record('Both forms loaded outside a long transaction', A=old_a, B=old_b)
        a.execute('BEGIN IMMEDIATE')
        a.execute(UPDATE, ('DEMO: A checked source header', 'in_review', 4))
        a.execute('COMMIT')
        b.execute('BEGIN IMMEDIATE')
        # Deliberately unsafe application: increments current version but ignores loaded version.
        b.execute(UPDATE, ('DEMO: B stale form replaces A note', 'resolved', 4))
        b.execute('COMMIT')
        record('Unsafe stale form overwrote A despite version-increment trigger', row=task(a, 4))
        require(task(a, 4)['version'] == 2 and task(a, 4)['note'].startswith('DEMO: B'),
                'Expected application-level overwrite not reproduced')
        current['passed'] = True

        begin_case('T05_optimistic_version_guard')
        loaded_a, loaded_b = task(a, 5), task(b, 5)
        require(guarded_edit(a, 5, loaded_a['version'], 'DEMO: A approved provenance', 'in_review'),
                'First guarded edit should succeed')
        accepted = guarded_edit(b, 5, loaded_b['version'], 'DEMO: stale B note', 'resolved')
        record('Stale B edit rejected with zero affected rows', accepted=accepted, row=task(b, 5))
        require(not accepted and task(b, 5)['note'] == 'DEMO: A approved provenance',
                'Stale guarded edit overwrote accepted work')
        refreshed = task(b, 5)
        # Simulates an explicitly reconsidered edit, not an automatic stale-payload retry.
        require(guarded_edit(b, 5, refreshed['version'],
                            'DEMO: A approved provenance; B checked label', 'resolved'),
                'Reconciled edit should succeed')
        record('B refreshes, reconciles and submits a new edit', row=task(a, 5))
        require(task(a, 5)['version'] == 2, 'Expected two accepted edits')
        current['passed'] = True

        begin_case('T06_WAL_reader_snapshot')
        a.execute('BEGIN')
        snapshot = task(a, 6)  # First SELECT establishes this reader's snapshot.
        require(guarded_edit(b, 6, 0, 'DEMO: B committed while A reads', 'in_review'), 'B failed')
        during = task(a, 6)
        record('B committed but existing A snapshot is stable', before=snapshot, during=during)
        require(snapshot == during, 'Read snapshot changed within transaction')
        a.execute('COMMIT')
        refreshed = task(a, 6)
        record('After ending read transaction A sees new commit', row=refreshed)
        require(refreshed['version'] == 1, 'New reader did not see committed change')
        current['passed'] = True

        begin_case('T07_stale_snapshot_write_upgrade')
        a.execute('BEGIN')
        require(task(a, 7)['version'] == 0, 'Initial snapshot incorrect')
        require(guarded_edit(b, 7, 0, 'DEMO: B accepted edit', 'in_review'), 'B failed')
        expect_error(a, GUARDED, ('DEMO: stale snapshot edit', 'resolved', 7, 0),
                     sqlite3.SQLITE_BUSY_SNAPSHOT)
        a.execute('ROLLBACK')
        latest = task(a, 7)
        require(guarded_edit(a, 7, latest['version'],
                            'DEMO: B accepted edit; A reconciled after refresh', 'resolved'),
                'Fresh reconciled transaction failed')
        record('Rollback, refresh and reconsider before new transaction', row=task(b, 7))
        current['passed'] = True

        begin_case('T08_single_writer_contention')
        a.execute('BEGIN IMMEDIATE')
        a.execute(UPDATE, ('DEMO: A holds writer transaction', 'in_review', 8))
        expect_error(b, 'BEGIN IMMEDIATE', (), sqlite3.SQLITE_BUSY)
        require(not b.in_transaction, 'Failed BEGIN should not start a transaction')
        require(task(b, 8)['version'] == 0, 'WAL reader saw pending writer change')
        a.execute('COMMIT')
        latest = task(b, 8)
        require(guarded_edit(b, 8, latest['version'],
                            'DEMO: B edit after writer released', 'resolved'), 'Retry failed')
        record('B succeeds after A commits and B rereads', row=task(a, 8))
        current['passed'] = True

        begin_case('T09_error_cleanup_and_constraints')
        expect_error(a, 'UPDATE review_task SET note=? WHERE task_id=?',
                     ('DEMO: forbidden no-version edit', 9), sqlite3.SQLITE_CONSTRAINT_TRIGGER)
        expect_error(a, 'INSERT INTO review_task(observation_id,assigned_user_id) VALUES(?,?)',
                     (-1, user), sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY)
        try:
            guarded_edit(a, 9, 0, 'DEMO: invalid helper edit', 'invalid_status')
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError('Helper must propagate invalid status')
        require(not a.in_transaction and task(b, 9)['version'] == 0,
                'Helper did not clean up failed transaction')
        require(not guarded_edit(a, -1, 0, 'DEMO: missing task', 'resolved'),
                'Missing task should not be reported as saved')
        record('Invalid edits left no transaction or partial change', row=task(b, 9))
        current['passed'] = True
        current = None
        require(a.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Final integrity failure')
        require(not a.execute('PRAGMA foreign_key_check').fetchall(), 'Final FK failure')
        require(not a.in_transaction and not b.in_transaction, 'Final transaction leaked')
        settings = {name: a.execute('PRAGMA ' + name).fetchone()[0] for name in
                    ('journal_mode', 'synchronous', 'foreign_keys', 'read_uncommitted', 'busy_timeout')}
    finally:
        a.close()
        b.close()
    require(digest(database) == source_hash, 'Original source changed during experiment')
    evidence = {
        'run_id': stamp, 'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version,
        'source_sha256_before': source_hash, 'source_sha256_after': digest(database),
        'runner_sha256': digest(Path(__file__)), 'settings': settings,
        'scheduling': 'Deterministically interleaved independent connections in one process; no threads or sleeps',
        'workflow_data': 'Nine fictional DEMO tasks attached to existing observations in a local-only copy',
        'checks': {'integrity': 'ok', 'foreign_keys': 'ok', 'source_unchanged': True,
                   'passed_cases': len(cases)}, 'cases': cases}
    out = evidence_dir.resolve() if evidence_dir else local / 'evidence'
    out.mkdir(parents=True, exist_ok=True)
    (out / f'{PREFIX}_Transaction_Evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    lines = ['# Portfolio 3: executed transaction evidence', '', f'Run: `{stamp}`', '',
             'All task notes below are fictional demonstration data. No raw prices are exported.', '']
    for case in cases:
        lines.extend(['## ' + case['case'], '', '**PASS**', '', '```json',
                      json.dumps(case['steps'], indent=2), '```', ''])
    (out / f'{PREFIX}_Transaction_Evidence.md').write_text('\n'.join(lines), encoding='utf-8')
    preview = ['<!doctype html><html lang="en"><meta charset="utf-8">',
               '<title>Portfolio 3 — Transaction Evidence</title>',
               '<style>body{max-width:1000px;margin:40px auto;padding:0 22px;font:17px/1.6 system-ui;color:#183048;background:#f5f8fc}section{background:white;padding:22px;margin:22px 0;border:1px solid #d5dfeb;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}.pass{color:#146b40}h1,h2{line-height:1.25}</style>',
               '<h1>Portfolio 3: transactions and concurrency</h1>',
               '<p>Ezenduka Chukwubuikem · 301913360 · Nigeria Food Price Observatory</p>',
               '<p>Generated from actual assertions and database outputs; this is an evidence viewer, not a screenshot.</p>',
               '<section><h2>How the version guard protects a review</h2><pre>A and B load task version 0\n       ↓\nA saves WHERE version = 0 → one row saved → version 1\n       ↓\nB saves WHERE version = 0 → zero rows saved → conflict\n       ↓\nB refreshes → reconciles notes → saves WHERE version = 1 → version 2</pre></section>',
               '<p>Run ' + html.escape(stamp) + ' · ' + str(len(cases)) + ' verified scenarios · Original database unchanged</p>']
    for case in cases:
        preview.extend(['<section><h2>' + html.escape(case['case']) + '</h2><strong class="pass">PASS</strong>',
                        '<pre>' + html.escape(json.dumps(case['steps'], indent=2)) + '</pre>',
                        '<details><summary>Actual SQL trace by connection</summary><pre>' +
                        html.escape(json.dumps(case['sql_trace'], indent=2)) + '</pre></details></section>'])
    preview.append('</html>')
    (out / f'{PREFIX}_Evidence_Preview.html').write_text('\n'.join(preview), encoding='utf-8')
    print(json.dumps({'run_id': stamp, 'passed_cases': len(cases), 'integrity': 'ok',
                      'source_unchanged': True, 'evidence_directory': str(out)}, indent=2))
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path,
                        default=ROOT / '.local' / f'{PREFIX}_Food_Prices.sqlite3')
    parser.add_argument('--workspace', type=Path, default=ROOT / '.local')
    parser.add_argument('--evidence-dir', type=Path)
    args = parser.parse_args()
    run(args.database, args.workspace, args.evidence_dir)
