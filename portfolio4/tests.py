"""Semantic and persistence checks using fictional data only."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage

PREFIX = 'Ezenduka_Chukwubuikem_301913360'
spec = importlib.util.spec_from_file_location('portfolio4', Path(__file__).with_name('run.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class DocumentSemantics(unittest.TestCase):
    def setUp(self):
        self.db = TinyDB(storage=MemoryStorage)
        self.snapshots = self.db.table('monthly_items', cache_size=0)
        self.reviews = self.db.table('demo_reviews', cache_size=0)
        self.doc = p.fictional_example()

    def tearDown(self):
        self.db.close()

    def test_valid_fictional_document_and_key(self):
        p.validate_document(self.doc)
        self.assertEqual(self.doc['document_key'], p.document_key('2099-01', 'Fictional training item'))

    def test_integer_kobo_rejects_bool_float_zero_negative(self):
        for bad in (True, 12.5, 0, -10):
            with self.subTest(price=bad):
                doc = deepcopy(self.doc)
                doc['observations'][0]['price_kobo'] = bad
                with self.assertRaises(ValueError):
                    p.validate_document(doc)

    def test_bad_month_key_and_schema_rejected(self):
        for field, value in [('period', '2025-13'), ('document_key', 'wrong'),
                             ('schema_version', True), ('schema_version', 2)]:
            doc = deepcopy(self.doc)
            doc[field] = value
            with self.assertRaises(ValueError):
                p.validate_document(doc)

    def test_duplicate_geography_and_wrong_level_rejected(self):
        doc = deepcopy(self.doc)
        doc['observations'][1]['geography'] = 'Nigeria'
        doc['observations'][1]['level'] = 'national'
        with self.assertRaises(ValueError):
            p.validate_document(doc)
        doc = deepcopy(self.doc)
        doc['observations'][0]['level'] = 'zone'
        with self.assertRaises(ValueError):
            p.validate_document(doc)

    def test_missing_provenance_rejected(self):
        del self.doc['provenance']['workbook_sha256']
        with self.assertRaises(ValueError):
            p.validate_document(self.doc)

    def test_duplicate_batch_rejected_before_any_write(self):
        with self.assertRaises(ValueError):
            p.import_snapshots(self.snapshots, [self.doc, deepcopy(self.doc)])
        self.assertEqual(len(self.snapshots), 0)

    def test_observation_reuse_across_documents_rejected(self):
        second = deepcopy(self.doc)
        second['item']['label'] = 'Another fictional item'
        second['document_key'] = p.document_key(second['period'], second['item']['label'])
        with self.assertRaises(ValueError):
            p.import_snapshots(self.snapshots, [self.doc, second])
        self.assertEqual(len(self.snapshots), 0)

    def test_reimport_requires_empty_collection(self):
        p.import_snapshots(self.snapshots, [self.doc])
        with self.assertRaises(ValueError):
            p.import_snapshots(self.snapshots, [self.doc])
        self.assertEqual(len(self.snapshots), 1)

    def test_nested_predicates_match_same_element(self):
        p.import_snapshots(self.snapshots, [self.doc])
        d, o = Query(), Query()
        # Nigeria is 10000; a different zone is 20000. Neither element satisfies both.
        correct = d.observations.any((o.geography == 'Nigeria') & (o.price_kobo >= 15000))
        wrong = d.observations.any(o.geography == 'Nigeria') & d.observations.any(o.price_kobo >= 15000)
        self.assertEqual(len(self.snapshots.search(correct)), 0)
        self.assertEqual(len(self.snapshots.search(wrong)), 1)

    def test_distinct_fish_labels_not_merged(self):
        docs = []
        for index, label in enumerate(['Smoked fish', 'Smoked fish (Mackerel)']):
            doc = deepcopy(self.doc)
            doc['item']['label'] = label
            doc['document_key'] = p.document_key(doc['period'], label)
            for obs in doc['observations']:
                obs['observation_id'] += index * 10
            docs.append(doc)
        p.import_snapshots(self.snapshots, docs)
        self.assertEqual(len(self.snapshots), 2)
        self.assertEqual(len(self.snapshots.search(Query().item.label == 'Smoked fish')), 1)

    def test_review_reference_and_status_validation(self):
        with self.assertRaises(ValueError):
            p.create_review(self.snapshots, self.reviews, 'absent', 'DEMO: missing')
        p.import_snapshots(self.snapshots, [self.doc])
        rid = p.create_review(self.snapshots, self.reviews, self.doc['document_key'], 'DEMO: original')
        with self.assertRaises(ValueError):
            p.update_review(self.reviews, rid, 'bad-status', 'DEMO: invalid', [])
        self.assertEqual(self.reviews.get(doc_id=rid)['status'], 'open')

    def test_crud_persists_without_mutating_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'fictional.json'
            with TinyDB(file) as db:
                snapshots, reviews = db.table('monthly_items'), db.table('demo_reviews')
                p.import_snapshots(snapshots, [self.doc])
                rid = p.create_review(snapshots, reviews, self.doc['document_key'], 'DEMO: create')
                p.update_review(reviews, rid, 'resolved', 'DEMO: update', ['label'])
                draft = p.create_review(snapshots, reviews, self.doc['document_key'], 'DEMO: draft')
                reviews.remove(doc_ids=[draft])
            with TinyDB(file) as db:
                self.assertEqual(len(db.table('demo_reviews')), 1)
                self.assertEqual(db.table('demo_reviews').get(doc_id=rid)['checks'], ['label'])
                self.assertEqual(dict(db.table('monthly_items').all()[0]), self.doc)


if __name__ == '__main__':
    unittest.main(verbosity=2)
