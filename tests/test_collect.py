import unittest, datetime as dt
from engine.collect import parse,merge
class CollectTests(unittest.TestCase):
    def test_rss_and_duplicate(self):
        now=dt.datetime(2026,11,17,tzinfo=dt.timezone.utc)
        raw=b'<rss><channel><item><title>Rate decision</title><link>https://example.org/a</link><pubDate>Mon, 16 Nov 2026 10:00:00 GMT</pubDate></item><item><title>Old</title><link>https://example.org/b</link><pubDate>Mon, 16 Nov 2020 10:00:00 GMT</pubDate></item></channel></rss>'
        rows=parse(raw,{'id':'a'},now); self.assertEqual(len(rows),1); self.assertEqual(len(merge(rows+rows)[0]['references']),1)
        other=dict(rows[0],url='https://example.org/c',source='b'); self.assertEqual(len(merge(rows+[other])[0]['references']),2)
    def test_atom(self):
        now=dt.datetime(2026,11,17,tzinfo=dt.timezone.utc)
        raw=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Trade</title><link href="https://example.org/a"/><updated>2026-11-16T10:00:00Z</updated></entry></feed>'
        self.assertEqual(len(parse(raw,{'id':'a'},now)),1)
