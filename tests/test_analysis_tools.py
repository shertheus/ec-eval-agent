import hashlib
import json
import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
import numpy as np
from brain_eval.contracts import DatasetRequest, Protocol, Method, Submission
from brain_eval.datasets import prepare, dataset_dir
from brain_eval.experiments import Scheduler, submit, inspect
from brain_eval.storage import initialize, attempt_dir
from brain_eval.analysis_tools import inspect_dataset, compare_experiments
from brain_eval.bundles import export_experiment


class AnalysisToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = os.environ.get('BRAIN_EVAL_WORKSPACE')
        os.environ['BRAIN_EVAL_WORKSPACE'] = self.temp.name
        initialize()
        self.scheduler = Scheduler()
        self.scheduler.start()
        self.serial = 0

    def tearDown(self):
        self.scheduler.close()
        if self.old is None:
            os.environ.pop('BRAIN_EVAL_WORKSPACE', None)
        else:
            os.environ['BRAIN_EVAL_WORKSPACE'] = self.old
        self.temp.cleanup()

    def data(self, seed=7):
        return prepare(DatasetRequest(kind='var', nodes=3, samples=80, edges=2, seed=seed))['dataset_id']

    def completed(self, dataset):
        self.serial += 1
        p = Protocol(dataset_ids=[dataset], methods=[Method(name='granger', params={'lag':1})], timeout_seconds=15)
        exp = submit(Submission(protocol=p, idempotency_key=str(self.serial)))['experiment_id']
        deadline = time.monotonic()+25
        while time.monotonic() < deadline:
            state = inspect(exp)
            if state['status'] not in ('queued', 'running'):
                self.assertEqual(state['status'], 'succeeded', state)
                return exp
            time.sleep(.1)
        self.fail('fixture did not finish')

    def test_statistics_and_tampered_observations(self):
        ds = self.data()
        result = inspect_dataset(ds)
        self.assertEqual(len(result['columns']), 3)
        self.assertEqual(result['missing_values'], 0)
        self.assertIsNotNone(result['columns'][0]['lag1_correlation'])
        self.assertNotIn('observations', result)
        np.save(dataset_dir(ds)/'observations.npy', np.zeros((80,3)))
        with self.assertRaisesRegex(ValueError, 'integrity'):
            inspect_dataset(ds)

    def test_comparison_requires_matching_data(self):
        first = self.completed(self.data())
        second = self.completed(self.data())
        third = self.completed(self.data(seed=8))
        matched = compare_experiments([first, second])
        self.assertTrue(matched['matched_datasets'])
        self.assertEqual(len(matched['rows']), 2)
        with self.assertRaisesRegex(ValueError, 'semantics differ'):
            compare_experiments([first, third])
        self.assertFalse(compare_experiments([first, third], False)['matched_datasets'])

    def test_export_has_verifiable_manifest_and_no_raw_data(self):
        exp = self.completed(self.data())
        result = export_experiment(exp)
        self.assertFalse(result['includes_raw_data'])
        with zipfile.ZipFile(result['path']) as archive:
            names = archive.namelist()
            self.assertIn('reports/report.html', names)
            self.assertFalse(any('observations.npy' in n or 'truth.npy' in n or n.endswith('.env') for n in names))
            manifest = json.loads(archive.read('bundle-manifest.json'))
            for name, checksum in manifest['files'].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), checksum)
        self.assertEqual(hashlib.sha256(Path(result['path']).read_bytes()).hexdigest(), result['sha256'])

    def test_export_rejects_modified_result(self):
        exp = self.completed(self.data())
        run = inspect(exp)['runs'][0]
        (attempt_dir(exp, run['id'], run['attempt'])/'metrics.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            export_experiment(exp)
