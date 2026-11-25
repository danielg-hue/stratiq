import unittest
from datetime import datetime,timezone
from calibration import Sample,walk_forward
from quant import dupont,roic,economic_value_added,sloan_accruals

def d(y): return datetime(y,1,1,tzinfo=timezone.utc)
class CalibrationTests(unittest.TestCase):
    def test_mature_training_only(self):
        rows=[Sample(str(i),d(y),d(y+1),d(y+2),(i,-i),i/10,(d(y),d(y))) for y in (2010,2012,2014) for i in range(5)]
        result=walk_forward(rows,[(.5,.5),(1,0),(0,1)],[d(2014),d(2015)],d(2017))[0]
        self.assertEqual(result['weights'],(1,0)); self.assertEqual(result['train'][1],1); self.assertAlmostEqual(result['test'][0],1)
    def test_no_training(self):
        self.assertEqual(walk_forward([],[(1,)],[d(2014),d(2015)],d(2017))[0]['status'],'insufficient_training')
    def test_invalid_weights(self):
        with self.assertRaises(ValueError): walk_forward([],[(2,)],[d(2014),d(2015)],d(2017))
    def test_quant(self):
        self.assertAlmostEqual(dupont(10,100,50,25)['roe'],.4)
        self.assertEqual(roic(10,50),.2); self.assertEqual(economic_value_added(10,50,.1),5)
        self.assertEqual(sloan_accruals(10,15,50),-.1); self.assertIsNone(roic(10,0))
