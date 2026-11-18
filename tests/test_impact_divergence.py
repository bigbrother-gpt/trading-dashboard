import unittest
from engine.impact_divergence import analyze

BASE = {
    "event_id": "EXAMPLE-ONLY", "country": "UK", "indicator": "CPI YoY",
    "release_timestamp": "2026-01-01T07:00:00+00:00",
    "actual": 3.2, "forecast": 3.0, "unit": "percentage_points",
    "expectations": {"GBPUSD": "up", "EURGBP": "down", "USDJPY": "neutral"},
    "prices": {
        "GBPUSD": {"before": 1.25, "after": 1.24,
                   "before_timestamp": "2026-01-01T06:59:00+00:00",
                   "after_timestamp": "2026-01-01T07:05:00+00:00"},
        "EURGBP": {"before": 0.85, "after": 0.84,
                   "before_timestamp": "2026-01-01T06:59:00+00:00",
                   "after_timestamp": "2026-01-01T07:05:00+00:00"}
    }
}
class ImpactTests(unittest.TestCase):
    def test_divergence_and_alignment(self):
        r = analyze(BASE)
        self.assertAlmostEqual(r["surprise"], 0.2)
        self.assertEqual(r["instruments"]["GBPUSD"]["status"], "divergent")
        self.assertEqual(r["instruments"]["EURGBP"]["status"], "aligned")
        self.assertEqual(r["instruments"]["USDJPY"]["status"], "missing_market_prices")
    def test_unverified_timestamp_rejected(self):
        e = dict(BASE, release_timestamp="2026-01-01T07:00:00")
        with self.assertRaises(ValueError):
            analyze(e)
    def test_invalid_window_rejected(self):
        e = dict(BASE)
        e["prices"] = {"GBPUSD": dict(BASE["prices"]["GBPUSD"], after_timestamp="2026-01-01T06:58:00+00:00")}
        with self.assertRaises(ValueError):
            analyze(e)
    def test_missing_forecast_rejected(self):
        e = dict(BASE, forecast=None)
        with self.assertRaises(ValueError):
            analyze(e)
    def test_threshold_neutral(self):
        e = dict(BASE, expectations={"GBPUSD": "neutral"},
                 prices={"GBPUSD": dict(BASE["prices"]["GBPUSD"], after=1.2501)})
        self.assertEqual(analyze(e)["instruments"]["GBPUSD"]["status"], "aligned")
if __name__ == "__main__":
    unittest.main()
