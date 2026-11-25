import unittest
from rubrics import *
class RubricTests(unittest.TestCase):
 def test_registry(self):
  self.assertEqual(set(RUBRICS),ELEMENTS)
  self.assertEqual(len(RUBRICS),50)
  for r in RUBRICS.values(): self.assertTrue(all(x.strip() for x in vars(r).values()))
 def test_overlap(self):
  for g in OVERLAP_GROUPS: self.assertTrue(set(g)<=ELEMENTS)
 def test_origin(self):
  self.assertEqual(evidence_independence([{'origin':'SEC'},{'origin':' sec '},{'origin':'peer'}]),2)
  with self.assertRaises(ValueError): evidence_independence([{'origin':' '}])
 def test_risk(self):
  self.assertFalse(publication_gate({'index':100},['insolvency'])['publishable'])
  self.assertFalse(publication_gate({'index':None},[])['publishable'])
  self.assertFalse(publication_gate({'index':80},[])['publishable'])
  with self.assertRaises(ValueError): publication_gate({'index':80},['fake'])
