"""Focused failure and routing tests using fictional task data only."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

P = 'Ezenduka_Chukwubuikem_301913360'
spec = importlib.util.spec_from_file_location('portfolio5', Path(__file__).with_name(P+'_Run.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ReplicationRules(unittest.TestCase):
    def setUp(self):
        self.primary = sqlite3.connect(':memory:', isolation_level=None)
        self.replica = sqlite3.connect(':memory:', isolation_level=None)
        for db in (self.primary, self.replica):
            db.executescript('''CREATE TABLE review_task(task_id INTEGER PRIMARY KEY,
                version INTEGER NOT NULL, status TEXT CHECK(status IN ('open','in_review','resolved')),
                note TEXT NOT NULL) STRICT;
                INSERT INTO review_task VALUES(1,0,'open','DEMO: initial');''')
            db.executescript(p.EXTENSION)

    def tearDown(self):
        self.primary.close()
        self.replica.close()

    def test_stale_primary_edit_creates_no_event(self):
        p.write_primary(self.primary,0,'DEMO: accepted')
        with self.assertRaises(p.Conflict):
            p.write_primary(self.primary,0,'DEMO: stale')
        self.assertEqual(p.latest(self.primary),1)
        self.assertEqual(p.state(self.primary)['note'],'DEMO: accepted')
        self.assertFalse(self.primary.in_transaction)

    def test_event_insert_failure_rolls_back_task(self):
        self.primary.executescript("CREATE TRIGGER reject_log BEFORE INSERT ON demo_replication_log BEGIN SELECT RAISE(ABORT,'injected log failure'); END;")
        with self.assertRaises(sqlite3.IntegrityError):
            p.write_primary(self.primary,0,'DEMO: must roll back')
        self.assertEqual(p.state(self.primary)['version'],0)
        self.assertEqual(p.latest(self.primary),0)
        self.assertFalse(self.primary.in_transaction)

    def test_mid_batch_failure_rolls_back_every_event_and_checkpoint(self):
        p.write_primary(self.primary,0,'DEMO: one')
        p.write_primary(self.primary,1,'DEMO: two')
        with self.assertRaisesRegex(RuntimeError,'Injected worker failure'):
            p.replicate(self.primary,self.replica,fail_after=2)
        self.assertEqual(p.state(self.replica)['version'],0)
        self.assertEqual(p.checkpoint(self.replica),0)
        self.assertFalse(self.replica.in_transaction)
        self.assertEqual(p.replicate(self.primary,self.replica),2)

    def test_repeat_delivery_does_not_duplicate_edits(self):
        p.write_primary(self.primary,0,'DEMO: one')
        self.assertEqual(p.replicate(self.primary,self.replica),1)
        self.assertEqual(p.replicate(self.primary,self.replica),0)
        self.assertEqual(p.state(self.replica)['version'],1)

    def test_missing_event_is_detected(self):
        p.write_primary(self.primary,0,'DEMO: one')
        p.write_primary(self.primary,1,'DEMO: two')
        self.primary.execute('DELETE FROM demo_replication_log WHERE sequence=1')
        with self.assertRaisesRegex(RuntimeError,'log gap'):
            p.replicate(self.primary,self.replica)
        self.assertEqual(p.checkpoint(self.replica),0)

    def test_diverged_replica_is_not_overwritten(self):
        p.write_primary(self.primary,0,'DEMO: legitimate')
        self.replica.execute("UPDATE review_task SET version=5,note='DEMO: out of band'")
        with self.assertRaisesRegex(RuntimeError,'diverged'):
            p.replicate(self.primary,self.replica)
        self.assertEqual(p.state(self.replica)['version'],5)
        self.assertEqual(p.checkpoint(self.replica),0)

    def test_strict_read_routes_to_primary_then_caught_up_replica(self):
        token=p.write_primary(self.primary,0,'DEMO: write')
        self.assertEqual(p.read_review(self.primary,self.replica,token)['route'],'primary')
        p.replicate(self.primary,self.replica)
        self.assertEqual(p.read_review(self.primary,self.replica,token,primary_available=False)['route'],'replica')

    def test_outage_refuses_write_and_strict_read_but_labels_stale_read(self):
        token=p.write_primary(self.primary,0,'DEMO: write')
        with self.assertRaises(p.Unavailable):
            p.write_primary(self.primary,1,'DEMO: must not save',available=False)
        with self.assertRaises(p.Unavailable):
            p.read_review(self.primary,self.replica,token,primary_available=False)
        result=p.read_review(self.primary,self.replica,token,strict=False,primary_available=False)
        self.assertFalse(result['satisfies_minimum'])
        self.assertEqual(result['task']['version'],0)
        self.assertEqual(p.latest(self.primary),1)

    def test_shard_boundaries_and_invalid_periods(self):
        self.assertEqual(p.shard_for('2025-06'),0)
        self.assertEqual(p.shard_for('2025-07'),1)
        for period in ('2024-12','2025-00','2025-13','2025-1','not-a-date'):
            with self.assertRaises(RuntimeError):
                p.shard_for(period)

    def test_missing_shard_does_not_create_empty_database(self):
        with tempfile.TemporaryDirectory() as directory:
            missing=Path(directory)/'missing.sqlite3'
            with self.assertRaises(p.Unavailable):
                p.read_shards([missing])
            self.assertFalse(missing.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
