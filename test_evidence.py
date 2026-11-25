import unittest
from dataclasses import replace
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from evidence import Document,Citation,audit
class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.t=datetime(2020,1,1,tzinfo=timezone.utc)
        b=b'example evidence'
        self.d=Document('a','publisher',self.t,self.t,b,sha256(b).hexdigest(),'research_only')
        self.c=Citation('brand','a',0,len(b),b,'supports')
    def runaudit(self,d=None,c=None): return audit([self.d] if d is None else d,[self.c] if c is None else c,self.t)
    def test_valid(self):
        r=self.runaudit(); self.assertTrue(r['integrity_checked']); self.assertFalse(r['publishable']); self.assertFalse(r['claims_verified'])
    def test_tamper(self):
        with self.assertRaises(ValueError): self.runaudit([replace(self.d,content=b'changed')])
    def test_excerpt(self):
        with self.assertRaises(ValueError): self.runaudit(c=[replace(self.c,excerpt=b'fake')])
    def test_future(self):
        with self.assertRaises(ValueError): self.runaudit([replace(self.d,available_at=self.t+timedelta(days=1))])
    def test_license(self):
        with self.assertRaises(ValueError): self.runaudit([replace(self.d,license='unknown')])
    def test_duplicate(self):
        with self.assertRaises(ValueError): self.runaudit(c=[self.c,self.c])
    def test_mirror_conflict(self):
        r=self.runaudit([self.d,replace(self.d,id='b',origin='mirror')],[self.c,replace(self.c,document_id='b',stance='contradicts')]); self.assertEqual(r['independent_group_candidates']['brand'],1); self.assertEqual(r['conflicts'],['brand'])
    def test_boolean_span(self):
        with self.assertRaises(ValueError): self.runaudit(c=[replace(self.c,start=False)])
    def test_missing_document(self):
        with self.assertRaises(ValueError): self.runaudit(d=[])
    def test_duplicate_document(self):
        with self.assertRaises(ValueError): self.runaudit(d=[self.d,self.d])
