import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from geography import locate
from evidence import extract,provenance
class TestEnrichment(unittest.TestCase):
 def test_single_country(self):
  self.assertEqual(locate('Port closures in Portugal')['country'],'Portugal')
 def test_ambiguous(self):
  self.assertIsNone(locate('Portugal and Japan discuss trade'))
 def test_no_guess(self):
  self.assertIsNone(locate('Central bank raises rates'))
 def test_claim_evidence(self):
  x=extract({'title':'Central bank announces new rate','references':[{'url':'https://example.org/a','source':'a'}]})
  self.assertEqual(x[0]['verification'],'unverified')
 def test_no_independent_claim(self):
  self.assertIsNone(provenance({'references':[{'url':'https://a.com/x'},{'url':'https://b.com/y'}]})['independent_confirmations'])
 def test_no_unfounded_extraction(self):
  self.assertEqual(extract({'title':'The annual meeting','references':[{'url':'https://example.org'}]}),[])
