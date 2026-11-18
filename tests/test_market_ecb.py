import sys,unittest,datetime as dt
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from market_ecb import parse_csv,crosses,snapshot
class ECBTests(unittest.TestCase):
 def setUp(self):
  self.rows={dt.date(2026,11,10):{'USD':1.10,'GBP':.85,'JPY':160},dt.date(2026,11,11):{'USD':1.12,'GBP':.86,'JPY':161},dt.date(2026,11,12):{'USD':1.14,'GBP':.87,'JPY':162},dt.date(2026,11,13):{'USD':1.15,'GBP':.88,'JPY':163},dt.date(2026,11,16):{'USD':1.16,'GBP':.89,'JPY':164},dt.date(2026,11,17):{'USD':1.17,'GBP':.90,'JPY':165}}
 def test_parse(self):
  raw='CURRENCY,TIME_PERIOD,OBS_VALUE\nUSD,2026-11-17,1.17\nUSD,2026-11-16,not-a-number\n'
  self.assertEqual(parse_csv(raw)[dt.date(2026,11,17)]['USD'],1.17)
 def test_cross(self):self.assertAlmostEqual(crosses(self.rows[dt.date(2026,11,17)])['GBPUSD'],1.3)
 def test_changes(self):
  s=snapshot(self.rows,dt.datetime(2026,11,17,20,tzinfo=dt.timezone.utc));q={x['symbol']:x for x in s['quotes']}
  self.assertEqual(len(q),4);self.assertAlmostEqual(q['EURUSD']['changes']['1D']['points'],.01);self.assertAlmostEqual(q['EURUSD']['changes']['5D']['points'],.07)
  self.assertNotIn('1M',q['EURUSD']['changes']);self.assertEqual(len(s['unavailable']),3)
 def test_stale(self):self.assertEqual(snapshot(self.rows,dt.datetime(2026,12,1,tzinfo=dt.timezone.utc))['quotes'],[])
 def test_incomplete(self):
  rows={dt.date(2026,11,17):{'USD':1.2}}
  self.assertEqual(snapshot(rows,dt.datetime(2026,11,17,tzinfo=dt.timezone.utc))['quotes'],[])
if __name__=='__main__':unittest.main()
