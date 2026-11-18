import sys,unittest,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from economic_engine import analyse,build,official,sessions,InvalidRelease,compact
from market_interpretation import compare,brief
BASE={'id':'cpi-test','indicator':'cpi','currency':'USD','period':'2026-10','unit':'percent',
 'released_at':'2026-11-12T13:30:00Z','official_url':'https://www.bls.gov/news.release/cpi.htm',
 'actual':'3.3','previous':'3.1','forecast':'3.0',
 'forecast_source_url':'https://example.org/consensus','forecast_asof':'2026-11-12T12:00:00Z'}
class EconomicTests(unittest.TestCase):
 def test_surprise(self):
  x=analyse(BASE);self.assertEqual(x['surprise'],'0.3');self.assertEqual(x['surprise_relative_percent'],'10');self.assertEqual(x['theoretical_movements']['EURUSD']['direction'],'down');self.assertEqual(x['theoretical_movements']['USDJPY']['direction'],'up')
 def test_no_forecast_no_theory(self):
  x=analyse({k:v for k,v in BASE.items() if k not in ('forecast','forecast_source_url','forecast_asof')});self.assertIsNone(x['surprise']);self.assertEqual(x['theoretical_movements'],{})
 def test_below(self):
  x=analyse(BASE|{'actual':'2.8'});self.assertEqual(x['theoretical_movements']['EURUSD']['direction'],'up')
 def test_unemployment_inverse(self):
  x=analyse(BASE|{'indicator':'unemployment_rate'});self.assertEqual(x['theoretical_movements']['USDJPY']['direction'],'down')
 def test_zero_forecast(self):
  x=analyse(BASE|{'forecast':'0'});self.assertIsNone(x['surprise_relative_percent'])
 def test_reject_postrelease_forecast(self):
  with self.assertRaises(InvalidRelease):analyse(BASE|{'forecast_asof':'2026-11-13T00:00:00Z'})
 def test_reject_unattributed_forecast(self):
  with self.assertRaises(InvalidRelease):analyse(BASE|{'forecast_source_url':None})
 def test_reject_fake_official(self):
  with self.assertRaises(InvalidRelease):analyse(BASE|{'official_url':'https://bls.gov.evil.org/fake'})
 def test_reject_nonfinite(self):
  with self.assertRaises(InvalidRelease):analyse(BASE|{'actual':'NaN'})
 def test_official_domain(self):
  self.assertEqual(official('https://www.ecb.europa.eu/press'),'ECB')
  self.assertIsNone(official('http://www.ecb.europa.eu/press'))
 def test_dst(self):
  a=sessions(dt.datetime(2026,7,1,12,tzinfo=dt.timezone.utc))
  b=sessions(dt.datetime(2026,1,1,12,tzinfo=dt.timezone.utc))
  self.assertNotEqual(a['London']['local_time'][-6:],b['London']['local_time'][-6:])
 def test_market_divergence_not_manipulation(self):
  x=analyse(BASE)
  result=compare(x,{'EURUSD':{'start':'1.1','end':'1.2','window':'30m','source_url':'https://example.org/data'}})
  self.assertEqual(result['EURUSD']['comparison'],'divergent')
  self.assertIn('does not establish manipulation',result['EURUSD']['interpretation'])
 def test_compact(self):
  x=compact(analyse(BASE));self.assertNotIn('sessions',x);self.assertEqual(x['theory']['EURUSD'],'down')
 def test_partial_batch(self):
  x=build({'releases':[BASE,BASE|{'official_url':'https://fake.org'}]});self.assertEqual(len(x['releases']),1);self.assertEqual(len(x['rejected']),1)
 def test_brief(self):self.assertIn('conditional',brief(analyse(BASE)))
if __name__=='__main__':unittest.main()
