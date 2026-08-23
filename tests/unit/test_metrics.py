import unittest

from validation.metrics import geh, holdout_split, mape, rmse, screenline, vkt


class MetricTests(unittest.TestCase):
    def test_traffic_metrics(self):
        self.assertEqual(round(geh(110, 100), 6), 0.9759)
        self.assertEqual(round(mape([110, 60], [100, 50]), 6), 15.0)
        self.assertEqual(round(rmse([110, 60], [100, 50]), 6), 10.0)
        self.assertEqual(screenline({"a": 110, "b": 60}, {"a": 100, "b": 50}, ["a", "b"])["model"], 170)
        self.assertEqual(vkt({"a": 110, "b": 60}, {"a": 1, "b": 2}), 230)

    def test_validation_series_length_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            rmse([1, 2], [1])
        with self.assertRaises(ValueError):
            mape([1], [1, 2])

    def test_holdout_is_deterministic_and_disjoint(self):
        first = holdout_split(["b", "a", "c", "d"])
        second = holdout_split(["d", "c", "a", "b"])
        self.assertEqual(first, second)
        self.assertFalse(set(first[0]) & set(first[1]))
        self.assertEqual(set(first[0]) | set(first[1]), {"a", "b", "c", "d"})
