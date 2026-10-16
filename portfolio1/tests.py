"""Offline constraint and importer tests. All fixture values are fictional test data."""
import importlib.util
from pathlib import Path
import sqlite3
import unittest

PREFIX = 'Ezenduka_Chukwubuikem_301913360'
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('portfolio_build', HERE / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript((HERE / 'schema.sql').read_text(encoding='utf-8'))
        self.db.execute("INSERT INTO publisher VALUES(1,'Fixture publisher','https://example.invalid')")
        self.db.execute("INSERT INTO source_resource VALUES(1,1,'https://example.invalid/source',?,'2026-10-02T00:00:00+00:00',100)", ('a'*64,))
        self.db.execute("INSERT INTO publication VALUES(1,1,'2025-01','fixture.xlsx',?)", ('b'*64,))
        self.db.execute("INSERT INTO item VALUES(1,'Fictional fixture item')")
        self.db.execute("INSERT INTO geography VALUES(1,'Nigeria','national')")
        self.db.execute("INSERT INTO price_observation VALUES(1,1,1,1,10000,'Fixture','D2')")
        self.db.execute("INSERT INTO app_user VALUES(1,'demo_test','analyst',1)")
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def rejected(self, sql, params=(), pattern=None):
        with self.assertRaisesRegex(sqlite3.IntegrityError, pattern or '.'):
            self.db.execute(sql, params)

    def test_foreign_keys_enabled(self):
        self.assertEqual(self.db.execute('PRAGMA foreign_keys').fetchone()[0], 1)

    def test_missing_item_rejected(self):
        self.rejected("INSERT INTO price_observation VALUES(2,1,999,1,100,'Fixture','D3')", pattern='FOREIGN KEY')

    def test_duplicate_observation_rejected(self):
        self.rejected("INSERT INTO price_observation VALUES(2,1,1,1,200,'Fixture','D3')", pattern='UNIQUE')

    def test_duplicate_source_cell_rejected(self):
        self.db.execute("INSERT INTO item VALUES(2,'Second fictional item')")
        self.rejected("INSERT INTO price_observation VALUES(2,1,2,1,200,'Fixture','D2')", pattern='UNIQUE')

    def test_zero_and_negative_prices_rejected(self):
        for price in (0,-1):
            with self.subTest(price=price):
                self.rejected("INSERT INTO price_observation VALUES(2,1,1,1,?,'Fixture','D3')", (price,), 'CHECK')

    def test_non_integer_price_rejected(self):
        self.rejected("INSERT INTO price_observation VALUES(2,1,1,1,1.25,'Fixture','D3')", pattern='INTEGER')

    def test_null_price_rejected(self):
        self.rejected("INSERT INTO price_observation VALUES(2,1,1,1,NULL,'Fixture','D3')", pattern='NOT NULL')

    def test_invalid_period_rejected(self):
        for period in ('2025-00','2025-13','2025-1','2025-AA'):
            with self.subTest(period=period):
                self.rejected("INSERT INTO publication VALUES(2,1,?,'other.xlsx',?)", (period,'c'*64), 'CHECK')

    def test_invalid_geography_rejected(self):
        self.rejected("INSERT INTO geography VALUES(2,'Lagos','zone')", pattern='CHECK')

    def test_referenced_item_delete_rejected(self):
        self.rejected('DELETE FROM item WHERE item_id=1', pattern='FOREIGN KEY')

    def test_source_prices_immutable(self):
        self.rejected('UPDATE price_observation SET price_kobo=500 WHERE observation_id=1', pattern='immutable')
        self.rejected('DELETE FROM price_observation WHERE observation_id=1', pattern='immutable')

    def test_task_requires_valid_user(self):
        self.rejected("INSERT INTO review_task VALUES(1,1,999,'open',0,'fixture')", pattern='FOREIGN KEY')

    def test_task_status_restricted(self):
        self.rejected("INSERT INTO review_task VALUES(1,1,1,'invalid',0,'fixture')", pattern='CHECK')

    def test_versioned_task_update(self):
        self.db.execute("INSERT INTO review_task VALUES(1,1,1,'open',0,'fixture')")
        self.rejected("UPDATE review_task SET status='in_review' WHERE task_id=1", pattern='increment version')
        changed = self.db.execute("UPDATE review_task SET status='in_review',version=version+1 WHERE task_id=1 AND version=0").rowcount
        stale = self.db.execute("UPDATE review_task SET status='resolved',version=version+1 WHERE task_id=1 AND version=0").rowcount
        self.assertEqual((changed,stale),(1,0))
        self.assertEqual(self.db.execute('SELECT status,version FROM review_task').fetchone(),('in_review',1))

    def test_failed_batch_rolls_back(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db:
                self.db.execute("INSERT INTO review_task VALUES(1,1,1,'open',0,'fixture')")
                self.db.execute("INSERT INTO review_task VALUES(2,1,1,'open',0,'duplicate')")
        self.assertEqual(self.db.execute('SELECT count(*) FROM review_task').fetchone()[0],0)


class ImportTests(unittest.TestCase):
    def test_period_is_taken_from_header(self):
        for header, expected in [('Average of Mar-25','2025-03'),('Average of Apr-25','2025-04'),('Average of September-25','2025-09')]:
            with self.subTest(header=header):
                self.assertEqual(build.reporting_period(header),expected)

    def test_unrecognised_header_rejected(self):
        with self.assertRaises(ValueError):
            build.reporting_period('Selected Food Dec 2024')

    def test_round_half_up(self):
        self.assertEqual(build.kobo(1.005),101)
        self.assertEqual(build.kobo(1.004),100)

    def test_invalid_price_is_not_filled_with_zero(self):
        for price in (None,'N/A',True,0,-1,float('nan'),float('inf')):
            with self.subTest(price=price):
                with self.assertRaises(ValueError):
                    build.kobo(price)

    def test_cosmetic_label_cleanup_preserves_meaning(self):
        self.assertEqual(build.clean_label('Agric  hen eggs, '),'Agric hen eggs')
        self.assertNotEqual(build.clean_label('Smoked fish'),build.clean_label('Smoked fish (Mackerel)'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
