import unittest
from engine.relevance import classify, process
class RelevanceTests(unittest.TestCase):
    def test_indirect(self):
        r=classify({'title':'Port closure interrupts cargo traffic'}); self.assertIn('EURUSD',r['potential_instruments']); self.assertEqual(r['direct_mentions'],[])
    def test_multilingual(self):
        for title in ['Inflação acelera','Banque: taux directeur inchangé','Leitzins bleibt unverändert','金融政策の変更']:
            with self.subTest(title=title): self.assertEqual(classify({'title':title})['triage'],'candidate')
    def test_unmatched_retained(self):
        r=process({'generated_at':'test','candidates':[{'title':'Local school opens'}]}); self.assertEqual(r['counts']['review_unmatched'],1); self.assertEqual(len(r['candidates']),1)
    def test_no_claims(self):
        r=classify({'title':'Bitcoin rises'}); self.assertIsNone(r['importance']); self.assertIsNone(r['confidence']); self.assertEqual(r['verification'],'unverified')
    def test_word_boundary(self): self.assertEqual(classify({'title':'Inflationary rhetoric'})['triage'],'review_unmatched')
    def test_direct(self): self.assertIn('EURGBP',classify({'title':'EURGBP update'})['direct_mentions'])
