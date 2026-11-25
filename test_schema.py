"""Static contract checks only; not PostgreSQL integration tests."""
import unittest
from pathlib import Path
from core import FRAMEWORKS
SQL=Path(__file__).with_name('schema.sql').read_text()
class SchemaContract(unittest.TestCase):
 def test_registry(self):
  for f, es in FRAMEWORKS.items():
   for e in es: self.assertIn(f"('{e}','{f}')",SQL)
  self.assertIn('element text references element_registry',SQL)
 def test_mutations(self):
  for clause in ('before update or delete','before truncate','append-only record'): self.assertIn(clause,SQL)
 def test_evidence(self):
  for clause in ('deferrable initially deferred','scored element requires evidence','future evidence','source license not cleared'): self.assertIn(clause,SQL)
 def test_access(self):
  for clause in ('enable row level security','from public, anon, authenticated','from service_role'): self.assertIn(clause,SQL)
 def test_no_na(self): self.assertIn("status in ('assessed','unknown')",SQL)
 def test_seal(self):
  for clause in ('for update','snapshot sealed','incomplete snapshot','read committed required','guard_assessment','guard_evidence','guard_seal'): self.assertIn(clause,SQL)
