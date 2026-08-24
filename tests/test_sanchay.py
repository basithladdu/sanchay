import time
import unittest
from sanchay import dedup, forecast, regret, scan


class TestSanchay(unittest.TestCase):
    def setUp(self):
        self.now = time.time()
        self.files = [
            scan.FileInfo('/app/node_modules/pkg/index.js', 5000000, self.now - 86400 * 30, self.now - 86400 * 30, 101),
            scan.FileInfo('/app/__pycache__/mod.cpython-312.pyc', 1000000, self.now - 86400 * 10, self.now - 86400 * 10, 102),
            scan.FileInfo('/home/user/notes.txt', 2000000, self.now - 86400 * 200, self.now - 86400 * 200, 103),
            scan.FileInfo('/home/user/thesis_final.pdf', 50000000, self.now - 86400 * 500, self.now - 86400 * 500, 104),
        ]

    def test_classification_disposable(self):
        self.assertEqual(regret.classify(self.files[0], duplicated=False), 'disposable')
        self.assertEqual(regret.classify(self.files[1], duplicated=False), 'disposable')

    def test_classification_unique_and_irreplaceable(self):
        # A unique, untracked, uncached file must be classified as 'unique'
        self.assertEqual(regret.classify(self.files[3], duplicated=False), 'unique')

    def test_staleness_calculation(self):
        f = scan.FileInfo('/tmp/test', 100, self.now - 86400 * 365, self.now - 86400 * 365, 1)
        stale = regret.staleness(f, self.now)
        self.assertAlmostEqual(stale, 1.0, places=2)

    def test_unique_files_excluded_from_cleanup_ranking(self):
        ranked = regret.rank(self.files, duplicate_paths=frozenset(), now=self.now)
        paths = [r['path'] for r in ranked]
        self.assertIn('/app/node_modules/pkg/index.js', paths)
        self.assertIn('/app/__pycache__/mod.cpython-312.pyc', paths)
        # Unique thesis file must NEVER appear in recommendations
        self.assertNotIn('/home/user/thesis_final.pdf', paths)
        self.assertNotIn('/home/user/notes.txt', paths)

    def test_forecast_rate_and_exhaustion(self):
        rate = forecast.rate(self.files)
        self.assertGreater(rate, 0)
        days = forecast.days_until_full(self.files, free_bytes=1000000000)
        self.assertIsNotNone(days)
        self.assertGreater(days, 0)


if __name__ == '__main__':
    unittest.main()
