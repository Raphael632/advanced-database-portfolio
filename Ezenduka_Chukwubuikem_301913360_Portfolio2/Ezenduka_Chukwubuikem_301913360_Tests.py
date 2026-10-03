"""Semantic edge cases for Portfolio 2. Every fixture price is fictional."""
import importlib.util
from pathlib import Path
import sqlite3
import unittest

PREFIX='Ezenduka_Chukwubuikem_301913360'
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('portfolio2',HERE/f'{PREFIX}_Run.py')
portfolio=importlib.util.module_from_spec(spec)
spec.loader.exec_module(portfolio)
QUERIES=portfolio.sql_catalog('Queries')
BENCH=portfolio.sql_catalog('Benchmark_Queries')


class QuerySemantics(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        schema=HERE.parent/f'{PREFIX}_Portfolio1'/f'{PREFIX}_Schema.sql'
        self.db.executescript(schema.read_text(encoding='utf-8'))
        self.db.execute("INSERT INTO publisher VALUES(1,'Test fixture','https://example.invalid')")
        self.db.execute("INSERT INTO source_resource VALUES(1,1,'https://example.invalid/source',?,'2026-10-03',1)",('a'*64,))
        for month in (1,2,3):
            self.db.execute('INSERT INTO publication VALUES(?,?,?,?,?)',(month,1,f'2025-{month:02d}',f'fixture{month}.xlsx','b'*64))
        for key,label in [(1,portfolio.FOCUS_ITEM),(2,'Smoked fish (Mackerel)'),(3,'Smoked fish'),(4,'Second fixture product')]:
            self.db.execute('INSERT INTO item VALUES(?,?)',(key,label))
        for key,name in enumerate(['Nigeria','NORTH CENTRAL','NORTH EAST','NORTH WEST','SOUTH EAST','SOUTH SOUTH','SOUTH WEST'],1):
            self.db.execute('INSERT INTO geography VALUES(?,?,?)',(key,name,'national' if key==1 else 'zone'))
        self.params={'item_id':1,'item_text':'1','geography_id':1,'national_id':1,
                     'start_period':'2025-01','end_period':'2025-03','floor_kobo':1,'top_n':10}

    def tearDown(self):
        self.db.close()

    def add(self,month,item,geography,price):
        self.db.execute('INSERT INTO price_observation(publication_id,item_id,geography_id,price_kobo,source_sheet,source_cell) VALUES(?,?,?,?,?,?)',
                        (month,item,geography,price,'Fixture',f'I{item}G{geography}'))

    def rows(self,name):
        return portfolio.result(self.db,QUERIES[name],self.params)['rows']

    def test_missing_month_is_not_bridged(self):
        self.add(1,1,1,10000)
        self.add(3,1,1,12000)
        self.assertEqual(self.rows('Q03_MONTHLY_CHANGE'),[])

    def test_changes_use_previous_calendar_month_and_real_division(self):
        self.add(1,1,1,10000)
        self.add(2,1,1,11000)
        self.add(3,1,1,8800)
        rows=self.rows('Q03_MONTHLY_CHANGE')
        self.assertEqual([(r['period'],r['preceding_month'],r['change_percent']) for r in rows],
                         [('2025-02','2025-01',10.0),('2025-03','2025-02',-20.0)])

    def test_rank_ties_and_exclusion_of_national_row(self):
        self.add(3,1,1,100000)
        for geo,price in enumerate([20000,20000,15000,14000,13000,12000],2):
            self.add(3,1,geo,price)
        rows=self.rows('Q05_REGIONAL_RANKING')
        self.assertEqual([r['price_rank'] for r in rows],[1,1,2,3,4,5])
        self.assertNotIn('Nigeria',[r['zone'] for r in rows])
        self.assertEqual(rows[0]['premium_to_national_percent'],-80.0)

    def test_missing_sixth_zone_is_not_reported_as_complete_spread(self):
        for geo in range(2,7): self.add(3,1,geo,geo*100)
        self.assertEqual(self.rows('Q04_REGIONAL_SPREAD'),[])
        self.assertEqual(self.rows('Q08_SPREAD_RANKING'),[])

    def test_spread_denominator_is_minimum_of_same_item(self):
        for geo,price in enumerate([10000,11000,12000,13000,14000,20000],2):
            self.add(3,1,geo,price)
        self.add(3,1,1,90000)
        self.assertEqual(self.rows('Q04_REGIONAL_SPREAD')[0]['spread_percent'],100.0)

    def test_smoked_fish_labels_remain_unmatched(self):
        self.add(3,2,1,10000)
        for geo in range(2,8): self.add(3,3,geo,10000)
        rows=self.rows('Q07_UNMATCHED_LABELS')
        self.assertEqual([(r['item'],r['observations_without_other_level']) for r in rows],
                         [('Smoked fish',6),('Smoked fish (Mackerel)',1)])

    def test_period_change_ranks_relative_not_absolute_increase(self):
        for item,start,end in [(1,100,200),(4,10000,11000)]:
            self.add(1,item,1,start)
            self.add(3,item,1,end)
        rows=self.rows('Q06_PERIOD_CHANGE_RANKING')
        self.assertEqual([r['change_percent'] for r in rows],[100.0,10.0])

    def test_bound_parameter_does_not_become_sql(self):
        self.add(1,1,1,10000)
        params=dict(self.params,item_id='1 OR 1=1')
        self.assertEqual(self.db.execute(BENCH['SERIES'],params).fetchall(),[])

    def test_top_price_ties_have_deterministic_order(self):
        for month,geo in [(2,2),(1,3),(1,2)]: self.add(month,1,geo,20000)
        self.params['top_n']=2
        self.assertEqual(self.db.execute(BENCH['TOP_PRICES'],self.params).fetchall(),[(1,2,20000),(2,2,20000)])

    def test_rewrite_equivalence_requires_canonical_integer_text(self):
        self.add(1,1,1,10000)
        before=self.db.execute(BENCH['WRAPPED_SERIES'],self.params).fetchall()
        after=self.db.execute(BENCH['SERIES'],self.params).fetchall()
        self.assertEqual(before,after)
        # This documents why arbitrary text cannot be silently rewritten as an integer.
        self.assertEqual(self.db.execute(BENCH['WRAPPED_SERIES'],dict(self.params,item_text='01')).fetchall(),[])
        self.assertNotEqual(before,[])

    def test_indexes_preserve_all_query_results(self):
        for month in range(1,4):
            for geo in range(1,8): self.add(month,1,geo,10000+month*100+geo*10)
        before={name:self.rows(name) for name in QUERIES}
        self.db.executescript((HERE/f'{PREFIX}_Indexes.sql').read_text(encoding='utf-8'))
        after={name:self.rows(name) for name in QUERIES}
        self.assertEqual(before,after)

    def test_query_only_connections_reject_writes(self):
        self.db.commit()
        self.db.execute('PRAGMA query_only=ON')
        with self.assertRaises(sqlite3.OperationalError):
            self.db.execute("INSERT INTO item VALUES(99,'Must not be written')")


if __name__=='__main__': unittest.main(verbosity=2)
