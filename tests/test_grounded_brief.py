import unittest
from engine.economic_engine import analyse
from engine.grounded_brief import brief

BASE={'indicator':'cpi','currency':'USD','period':'2026-10','unit':'percent',
      'official_url':'https://www.bls.gov/news.release/cpi.htm',
      'released_at':'2026-11-12T13:30:00+00:00','actual':'3.3','previous':'3.1'}
class TestBrief(unittest.TestCase):
    def test_no_forecast_abstains(self):
        b=brief(analyse(BASE))
        self.assertIn('withheld',b['interpretation'])
        self.assertEqual(b['theoretical_movements'],{})
        self.assertIn('Not measured',b['market_reaction'])
    def test_sourced_forecast(self):
        r=BASE|{'forecast':'3.0','forecast_source_url':'https://example.com/consensus',
                'forecast_asof':'2026-11-11T12:00:00+00:00'}
        b=brief(analyse(r))
        self.assertIn('surprise 0.3',b['interpretation'])
        self.assertEqual(b['theoretical_movements']['EURUSD']['direction'],'down')
        self.assertEqual(b['method'],'deterministic_template_not_ai_inference')
    def test_unexpected_verification_fails_closed(self):
        r=analyse(BASE);r['verification']='verified'
        with self.assertRaises(ValueError):brief(r)
if __name__=='__main__':unittest.main()
