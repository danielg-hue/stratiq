import unittest
from core import *
from datetime import timezone
T=datetime(2020,1,1,tzinfo=timezone.utc)
E=Evidence('1',T,'filing')
class Tests(unittest.TestCase):
 def test_count(self): self.assertEqual(len(ELEMENTS),50)
 def test_full(self): self.assertEqual(index([Assessment(x,'assessed',Decimal(2),(E,),'test') for x in ELEMENTS],T)['index'],100)
 def test_missing(self): self.assertIsNone(index([],T)['index'])
 def test_future(self):
  with self.assertRaises(ValueError): index([Assessment('rivalry','assessed',Decimal(1),(Evidence('2',T.replace(year=2021),'filing'),),'test')],T)
 def test_precision(self):
  with self.assertRaises(ValueError): index([Assessment('rivalry','assessed',Decimal('.1'),(E,),'test')],T)
 def test_na(self):
  with self.assertRaises(ValueError): index([Assessment('rivalry','na',None)],T)
 def test_purge(self): self.assertEqual(eligible_training([dict(as_of=T.replace(year=2018),outcome_end=T,label_available_at=T)],T),[])
 def test_benchmark_missing(self): self.assertIsNone(piotroski({}))
if __name__=='__main__': unittest.main()
