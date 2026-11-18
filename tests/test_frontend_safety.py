import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class FrontendSafetyTests(unittest.TestCase):
 def test_no_demo_fallback(self):
  s=(ROOT/'live-data.js').read_text()
  self.assertIn("data.splice(0,data.length); render();",s)
  self.assertIn("NO VALIDATED LIVE SNAPSHOT",s)
  self.assertNotIn('DEMONSTRATION ONLY / FICTIONAL EVENTS',s)
 def test_schedule_opt_in(self):
  s=(ROOT/'.github/workflows/pages.yml').read_text()
  self.assertIn('HERMES_ENABLE_SCHEDULE',s)
 def test_market_rights(self):
  s=(ROOT/'markets.js').read_text()
  self.assertIn('European Central Bank (ECB)',s)
  self.assertIn('não em tempo real',s)
if __name__=='__main__':unittest.main()
