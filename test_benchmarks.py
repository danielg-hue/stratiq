import unittest
from benchmarks import *
class BenchmarkTests(unittest.TestCase):
 def test_yields(self): self.assertEqual(yields(10,-5,100),{'earnings_yield':.1,'fcf_yield':-.05})
 def test_magic(self): self.assertEqual(magic_formula(20,100,30,20),{'earnings_yield':.2,'return_on_capital':.4})
 def test_invalid(self):
  for x in (None,float('nan'),float('inf'),True,'5',10**1000): self.assertIsNone(interest_coverage(x,1))
  for x in (0,-1): self.assertIsNone(interest_coverage(1,x))
 def test_beneish(self):
  x=dict.fromkeys(('dsri','gmi','aqi','sgi','depi','sgai','lvgi'),1); x['tata']=0
  self.assertAlmostEqual(beneish_m(x),-2.48); x['tata']=float('nan'); self.assertIsNone(beneish_m(x)); del x['sgi']; self.assertIsNone(beneish_m(x))
