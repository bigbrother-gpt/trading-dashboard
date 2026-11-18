import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from publish import build
from scoring import score

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,11,17,12,tzinfo=dt.timezone.utc)
        self.discovery={'generated_at':self.now.isoformat(),'sources':[{'id':'fed','status':'ok'}]}
        self.relevance={'generated_at':self.now.isoformat(),'candidates':[{'id':'a','title':'Central bank announces rate cut','triage':'candidate','signals':[{'topic':'monetary_policy'}],'potential_instruments':['EURUSD'],'references':[{'source':'fed','url':'https://www.federalreserve.gov/new','published':self.now.isoformat()}]}]}
    def test_unverified_metadata(self):
        result=build(self.discovery,self.relevance,self.now)
        item=result['items'][0]
        self.assertEqual(item['verification'],'unverified')
        self.assertIsNone(item['importance']);self.assertIsNone(item['country']);self.assertIsNone(item['impact'])
    def test_no_healthy_feeds_fails_closed(self):
        self.discovery['sources'][0]['status']='error'
        with self.assertRaises(ValueError):build(self.discovery,self.relevance,self.now)
    def test_stale_fails_closed(self):
        self.discovery['generated_at']=(self.now-dt.timedelta(hours=2)).isoformat()
        with self.assertRaises(ValueError):build(self.discovery,self.relevance,self.now)
    def test_old_dropped(self):
        self.relevance['candidates'][0]['references'][0]['published']=(self.now-dt.timedelta(days=31)).isoformat()
        self.assertEqual(build(self.discovery,self.relevance,self.now)['items'],[])
    def test_bad_urls_dropped(self):
        self.relevance['candidates'][0]['references'][0]['url']='javascript:alert(1)'
        self.assertEqual(build(self.discovery,self.relevance,self.now)['items'],[])
    def test_score_thresholds(self):
        self.assertEqual(score(100,100,100)['classification'],'Critical')
        self.assertEqual(score(60,60,60)['classification'],'Emerging')
        self.assertEqual(score(30,30,30)['classification'],'Early Signal')
        self.assertEqual(score(0,0,0)['classification'],'Informational')
    def test_score_rejects_unknown(self):
        with self.assertRaises(ValueError):score(None,50,50)
        with self.assertRaises(ValueError):score(101,50,50)
if __name__=='__main__':unittest.main()
