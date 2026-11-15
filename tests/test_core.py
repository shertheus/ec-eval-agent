import os
import tempfile
import unittest
from pathlib import Path
import numpy as np
from brain_eval.contracts import DatasetRequest,Protocol,Submission,Method
from brain_eval.datasets import prepare,dataset_dir,observations
from brain_eval.metrics import graph_metrics
from brain_eval.protocols import validate
from brain_eval.storage import initialize
from brain_eval.experiments import submit,inspect,Scheduler


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.previous={key:os.environ.get(key) for key in ['BRAIN_EVAL_WORKSPACE','BRAIN_EVAL_INPUT']}
        os.environ['BRAIN_EVAL_WORKSPACE']=self.temp.name
        os.environ['BRAIN_EVAL_INPUT']=str(Path(self.temp.name)/'input')
        Path(os.environ['BRAIN_EVAL_INPUT']).mkdir()
        initialize()

    def tearDown(self):
        for key,value in self.previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
        self.temp.cleanup()

    def dataset(self):return prepare(DatasetRequest(kind='var',nodes=3,edges=2,samples=80))

    def test_reversal_and_bidirectional_metrics(self):
        true=np.array([[0,1],[0,0]])
        reverse=true.T
        m=graph_metrics(reverse,true)
        self.assertEqual((m['f1'],m['shd']),(0.,1))
        m=graph_metrics(np.array([[1,1],[1,1]]),true)
        self.assertAlmostEqual(m['f1'],2/3)
        self.assertEqual(m['shd'],1)
        self.assertEqual(graph_metrics(np.zeros((2,2)),np.zeros((2,2)))['f1'],0.)

    def test_rng_and_data_integrity(self):
        a=self.dataset();b=self.dataset()
        self.assertEqual(a['checksum'],b['checksum'])
        path=dataset_dir(a['dataset_id'])/'observations.npy'
        np.save(path,np.ones((80,3)))
        with self.assertRaisesRegex(ValueError,'integrity'):observations(a['dataset_id'])

    def test_import_rejects_path_escape_and_nan(self):
        with self.assertRaisesRegex(ValueError,'inside'):
            prepare(DatasetRequest(kind='import',path='/etc/passwd'))
        p=Path(os.environ['BRAIN_EVAL_INPUT'])/'bad.npy'
        np.save(p,np.full((50,3),np.nan))
        with self.assertRaisesRegex(ValueError,'NaN'):
            prepare(DatasetRequest(kind='import',path='bad.npy'))

    def test_real_input_no_fabricated_truth(self):
        p=Path(os.environ['BRAIN_EVAL_INPUT'])/'valid.npy'
        np.save(p,np.random.default_rng(1).normal(size=(50,3)))
        meta=prepare(DatasetRequest(kind='import',path='valid.npy'))
        self.assertFalse(meta['has_truth'])
        self.assertFalse((dataset_dir(meta['dataset_id'])/'truth.npy').exists())

    def test_static_brain_methods_allowed_but_iid_time_rejected(self):
        ds=self.dataset()
        p=Protocol(dataset_ids=[ds['dataset_id']],methods=[Method(name='notears')])
        result=validate(p)
        self.assertTrue(result['valid']);self.assertTrue(result['warnings'])
        # Import IID metadata to ensure time ordering is never silently invented.
        inp=Path(os.environ['BRAIN_EVAL_INPUT'])/'iid.npy'
        np.save(inp,np.random.default_rng(1).normal(size=(50,3)))
        iid=prepare(DatasetRequest(kind='import',path='iid.npy',input_kind='iid'))
        p=Protocol(dataset_ids=[iid['dataset_id']],methods=[Method(name='granger')])
        self.assertFalse(validate(p)['valid'])

    def test_idempotency_and_explicit_retry(self):
        ds=self.dataset();p=Protocol(dataset_ids=[ds['dataset_id']],methods=[Method(name='notears')])
        first=submit(Submission(protocol=p,idempotency_key='same'))
        second=submit(Submission(protocol=p,idempotency_key='same'))
        self.assertEqual(first['experiment_id'],second['experiment_id'])
        self.assertEqual(len(inspect(first['experiment_id'])['runs']),1)
        p.title='different'
        with self.assertRaisesRegex(ValueError,'different protocol'):
            submit(Submission(protocol=p,idempotency_key='same'))
        scheduler=Scheduler()
        scheduler.control(first['experiment_id'],'cancel')
        self.assertEqual(inspect(first['experiment_id'])['counts'],{'cancelled':1})
        scheduler.control(first['experiment_id'],'retry')
        self.assertEqual(inspect(first['experiment_id'])['counts'],{'queued':1})

    def test_parameter_validation(self):
        ds=self.dataset()
        for method in [Method(name='notears',device='cuda'),Method(name='golem',params={'num_iter':1.5}),Method(name='golem',params={'typo':2})]:
            self.assertFalse(validate(Protocol(dataset_ids=[ds['dataset_id']],methods=[method]))['valid'])

    def test_granger_direction(self):
        from brain_eval.adapters import fit
        rng=np.random.default_rng(8);x=rng.normal(size=(1200,2))
        x[1:,1]+=.9*x[:-1,0]
        graph,weights,extra=fit(x,Method(name='granger',params={'lag':1}),1)
        self.assertEqual(graph[0,1],1)
        self.assertEqual(graph[1,0],0)

    def test_neural_gc_orientation(self):
        from brain_eval.vendor.neural_gc.cmlp import cMLP
        import torch
        model=cMLP(2,2,[3])
        with torch.no_grad():
            for network in model.networks:network.layers[0].weight.zero_()
            model.networks[1].layers[0].weight[:,0,1]=1
        graph=model.GC().numpy().T
        self.assertEqual(graph.tolist(),[[0,1],[0,0]])


if __name__=='__main__':unittest.main()
