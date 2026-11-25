import unittest
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from core import index,Assessment,Evidence
from rubrics import publication_gate
from quant import ratio,sloan_accruals,dupont
from calibration import Sample,walk_forward
from backtest import Observation,compare,spearman
T=datetime(2020,1,1,tzinfo=timezone.utc)
B=T.replace(year=2021); C=B.replace(year=2022); D=C.replace(year=2023)
class RedTeam(unittest.TestCase):
 def test_blank_source(self):
  with self.assertRaises(ValueError): index([Assessment('rivalry','assessed',Decimal(2),(Evidence('x',T,' '),),'claim')],T)
 def test_publication(self):
  for x in (999,float('nan'),Decimal('NaN'),80,True):
   self.assertFalse(publication_gate({'index':x,'evidence_verified':True},[])['publishable'])
 def test_mixed(self):
  rows=[Sample('a',T,b,b,(1,),.1,(T,)) for b in (B,T+timedelta(days=30))]
  with self.assertRaises(ValueError): walk_forward(rows,[(1,)],[C,D],D)
 def test_empty_test(self):
  rows=[Sample(str(i),T,B,B,(i,),i,(T,)) for i in range(5)]
  self.assertEqual(walk_forward(rows,[(1,)],[C,D],D)[0]['status'],'insufficient_testing')
 def test_numeric(self):
  for x in (True,10**1000,'1',float('nan')):
   self.assertIsNone(ratio(x,1)); self.assertIsNone(sloan_accruals(x,1,1)); self.assertIsNone(spearman([1,2,x],[1,2,3]))
  self.assertIsNone(dupont(1e100,1,1e-100,1e-100))
 def test_provenance(self):
  for ts in (None,{}, {'a':B}):
   with self.assertRaises(ValueError): compare([Observation('a',T,B,B,{'a':1},.1,ts)],['a'],C)
 def test_schema_coverage(self):
  from pathlib import Path
  s=Path(__file__).with_name('schema.sql').read_text()
  self.assertIn('insufficient framework coverage',s); self.assertIn('insufficient coverage',s)
