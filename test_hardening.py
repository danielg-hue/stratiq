import unittest
from datetime import datetime, timezone
from decimal import Decimal
from core import Assessment,Evidence,ELEMENTS,index,FRAMEWORKS
from quant import ratio,economic_value_added,altman_z_manufacturing
from backtest import spearman
from calibration import Sample,walk_forward
T=datetime(2020,1,1,tzinfo=timezone.utc)
E=Evidence('1',T,'filing')
def row(x): return Assessment(x,'assessed',Decimal(2),(E,),'test')
class Hardening(unittest.TestCase):
 def test_na_attack(self):
  with self.assertRaises(ValueError): index([Assessment(x,'na',None,(E,),'test') for x in ELEMENTS],T)
 def test_threshold_attack(self):
  with self.assertRaises(TypeError): index([row('rivalry')],T,minimum=0)
 def test_concentrated_missing(self):
  self.assertIsNone(index([row(x) for x in ELEMENTS-set(FRAMEWORKS['porter'])],T)['index'])
 def test_overflow(self):
  self.assertIsNone(ratio(1e308,1e-308)); self.assertIsNone(economic_value_added(1,1e308,1e308)); self.assertIsNone(altman_z_manufacturing(1e308,1e308,1,1,1,1,1))
 def test_nonfinite_rank(self):
  for v in (float('nan'),float('inf'),-float('inf')): self.assertIsNone(spearman([1,v,3],[1,2,3]))
 def test_future_feature(self):
  b=T.replace(year=2021); c=T.replace(year=2022)
  for ts in ((),(b,)):
   with self.assertRaises(ValueError): walk_forward([Sample('a',T,b,b,(1,),.1,ts)],[(1,)],[b,c],c)
 def test_bounds(self):
  for i in range(-8,9):
   rows=[Assessment(x,'assessed',Decimal(i)/4,(E,),'test') for x in ELEMENTS]
   self.assertEqual(index(rows,T)['index'],50+Decimal(i)*Decimal('6.25'))
