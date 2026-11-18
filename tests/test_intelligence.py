import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from intelligence import audit,temporal_review,origin_hint
class IntelligenceTests(unittest.TestCase):
 def test_wire_origin_not_independence(self):
  a=audit({'title':'Reuters: central bank raises rate','references':[{'url':'https://a.example/story'},{'url':'https://b.example/story'}]})
  self.assertEqual(a['publisher_hosts'],2)
  self.assertEqual(a['shared_wire_origin_hint'],'reuters')
  self.assertFalse(a['independent_reporting_confirmed'])
 def test_bad_links(self):
  self.assertEqual(audit({'references':[{'url':'javascript:alert(1)'}]})['rejected_links'],1)
 def test_time_evolution(self):
  o=[{'url':'https://a','claims':[{'subject':'Port','predicate':'status','value':'closed','asof':'2026-01-01T10:00:00Z'}]}, {'url':'https://b','claims':[{'subject':'Port','predicate':'status','value':'open','asof':'2026-01-02T10:00:00Z'}]}]
  r=temporal_review(o)
  self.assertEqual(len(r['time_evolution']),1)
  self.assertEqual(r['same_time_conflicts'],[])
 def test_same_time_conflict(self):
  o=[{'url':'a','claims':[{'subject':'CPI','predicate':'rate','value':'2.0','asof':'2026-01-01T10:00:00Z'}]},{'url':'b','claims':[{'subject':'CPI','predicate':'rate','value':'3.0','asof':'2026-01-01T10:00:00+00:00'}]}]
  self.assertEqual(len(temporal_review(o)['same_time_conflicts']),1)
 def test_unknown_time_is_not_confirmed_conflict(self):
  o=[{'claims':[{'subject':'CPI','predicate':'rate','value':'2.0'}]},{'claims':[{'subject':'CPI','predicate':'rate','value':'3.0'}]}]
  self.assertEqual(len(temporal_review(o)['time_ambiguous_differences']),1)
  self.assertEqual(temporal_review(o)['same_time_conflicts'],[])
if __name__=='__main__':unittest.main()
