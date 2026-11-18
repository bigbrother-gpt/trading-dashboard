import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from cross_reference import build,similarity

def item(id,title,topic='trade_logistics',url=None):
    return {'id':id,'title':title,'signals':[{'topic':topic}], 'references':[{'url':url or 'https://example.org/'+id,'source':id,'published':'2026-11-17T10:00:00+00:00'}]}
class CrossReferenceTests(unittest.TestCase):
    def test_exact_and_near_headlines_cluster(self):
        a=item('1','Port closure interrupts cargo traffic in Lisbon')
        b=item('2','Port closure interrupts cargo traffic in Lisbon')
        self.assertEqual(len(build({'candidates':[a,b]})['events']),1)
    def test_different_events_not_merged(self):
        a=item('1','Port closure interrupts cargo traffic in Lisbon')
        b=item('2','Port closure interrupts cargo traffic in Porto')
        self.assertEqual(len(build({'candidates':[a,b]})['events']),2)
    def test_different_topic_not_merged(self):
        a=item('1','Port closure interrupts cargo traffic in Lisbon')
        b=item('2','Port closure interrupts cargo traffic in Lisbon','monetary_policy')
        self.assertEqual(len(build({'candidates':[a,b]})['events']),2)
    def test_never_claim_confirmation_or_saturation(self):
        e=build({'candidates':[item('1','Port closure interrupts cargo traffic in Lisbon')]})['events'][0]
        self.assertIsNone(e['independent_confirmations'])
        self.assertFalse(e['stop_recommended'])
        self.assertEqual(e['verification'],'unverified')
    def test_empty(self):
        self.assertEqual(build({'candidates':[]})['events'],[])
if __name__=='__main__':unittest.main()
