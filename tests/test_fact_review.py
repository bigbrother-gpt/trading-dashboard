import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
from fact_review import review

def obs(origin,claims,verified=False):
    return {'url':f'https://example.org/{origin}', 'origin_id':origin,
            'independently_verified':verified,'claims':[{'subject':'Port','predicate':'status','value':v} for v in claims]}

class TestFactReview(unittest.TestCase):
    def test_empty(self):
        self.assertFalse(review([])['stop_recommended'])
    def test_novelty(self):
        r=review([obs('a',['closed']),obs('b',['closed'])]);self.assertEqual(r['novelty_by_source'][1]['new_claims'],0)
    def test_no_independence_assumption(self):
        r=review([obs('a',['closed']),obs('b',['closed']),obs('c',['closed']),obs('d',['closed'])]);self.assertFalse(r['stop_recommended'])
    def test_advisory_stop(self):
        r=review([obs('a',['closed'],True),obs('b',['closed'],True),obs('c',['closed']),obs('d',['closed'])]);self.assertTrue(r['stop_recommended'])
    def test_conflict_blocks_stop(self):
        r=review([obs('a',['closed'],True),obs('b',['open'],True),obs('c',['open']),obs('d',['open']),obs('e',['open'])]);self.assertFalse(r['stop_recommended']);self.assertTrue(r['contradictions'])
    def test_reactivation(self):
        r=review([obs('a',['closed'],True),obs('b',['closed'],True),obs('c',['closed']),obs('d',['closed']),obs('e',['reopened'])]);self.assertFalse(r['stop_recommended']);self.assertEqual(r['novelty_by_source'][-1]['redundant_streak'],0)
    def test_malformed_claims(self):
        r=review([{'url':'x','claims':[{'subject':'','predicate':'status','value':'closed'}]}]);self.assertEqual(len(r['observed_claims']),0)
if __name__=='__main__':unittest.main()
