import unittest
from datetime import datetime,timezone
from quant import altman_z_manufacturing,piotroski_from_accounts
from backtest import Observation,compare,spearman
class ResearchTests(unittest.TestCase):
    def test_altman(self): self.assertAlmostEqual(altman_z_manufacturing(10,10,10,100,50,50,100),2.19)
    def test_missing(self): self.assertIsNone(altman_z_manufacturing(10,10,10,0,50,50,100)); self.assertIsNone(piotroski_from_accounts({},{}))
    def test_rank(self): self.assertAlmostEqual(spearman([1,2,3],[3,2,1]),-1); self.assertIsNone(spearman([1,1,1],[1,2,3]))
    def test_matched(self):
        a,b,c=[datetime(y,1,1,tzinfo=timezone.utc) for y in (2020,2021,2022)]
        rows=[Observation(str(i),a,b,b,{'a':i,'b':-i},i/10,{'a':a,'b':a}) for i in range(3)]
        rows.append(Observation('missing',a,b,b,{'a':4},.4,{'a':a,'b':a}))
        result=compare(rows,['a','b'],c)
        self.assertEqual(result['excluded'],1); self.assertEqual(result['cohorts'][0]['rank_ic'],{'a':1.,'b':-1.})
        self.assertEqual(compare(rows,['a','b'],a)['cohorts'],[])
        with self.assertRaises(ValueError): compare(rows+rows,['a','b'],c)
