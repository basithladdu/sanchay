import subprocess
import tempfile
import time
import unittest
import os
import copy
import contextlib
import io
import shutil
from pathlib import Path

from sanchay import cli, dedup, demo, forecast, plan, regret, report, scan, snapshot


class TestSanchay(unittest.TestCase):
    def setUp(self):
        self.now = time.time()
        self.files = [
            scan.FileInfo('/app/node_modules/.cache/pkg/index.js', 5000000, self.now - 86400 * 30, self.now - 86400 * 30, 101),
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

    def test_direct_duplicate_evidence_precedes_a_path_heuristic(self):
        cached_duplicate = scan.FileInfo(
            '/tmp/.cache/build-output.bin', 4096, self.now, self.now, 105)
        self.assertEqual(regret.classify(cached_duplicate, duplicated=True),
                         'duplicate')

    def test_staleness_calculation(self):
        f = scan.FileInfo('/tmp/test', 100, self.now, self.now - 86400 * 365, 1)
        stale = regret.staleness(f, self.now)
        self.assertAlmostEqual(stale, 1.0, places=2)

    def test_unique_files_excluded_from_cleanup_ranking(self):
        ranked = regret.rank(self.files, duplicate_paths=frozenset(), now=self.now)
        paths = [r['path'] for r in ranked]
        self.assertIn('/app/node_modules/.cache/pkg/index.js', paths)
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

    def test_only_clean_committed_files_are_git_recoverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clean = root / 'clean.txt'
            modified = root / 'modified.txt'
            staged = root / 'staged.txt'
            for path in (clean, modified, staged):
                path.write_bytes(b'committed content')

            def git(*args):
                subprocess.run(
                    ['git', *args], cwd=root, check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            git('init', '-q')
            git('add', '.')
            git('-c', 'user.name=SANCHAY Tests',
                '-c', 'user.email=tests@sanchay.invalid',
                'commit', '-qm', 'fixture')
            modified.write_bytes(b'uncommitted working content')
            staged.write_bytes(b'uncommitted staged content')
            git('add', staged.name)

            regret._repo_cache.clear()
            self.addCleanup(regret._repo_cache.clear)

            def info(path):
                stat = path.stat()
                return scan.FileInfo(
                    str(path), stat.st_size, stat.st_atime,
                    stat.st_mtime, stat.st_ino)

            self.assertEqual(regret.classify(info(clean), False), 'tracked')
            self.assertEqual(regret.classify(info(modified), False), 'unique')
            self.assertEqual(regret.classify(info(staged), False), 'unique')

    def test_cleanup_plan_never_contains_unique_files(self):
        cleanup_plan = plan.build(self.files, [], '/app', now=self.now)
        kinds = [item['kind'] for item in cleanup_plan['recommendations']]
        paths = [item['path'] for item in cleanup_plan['recommendations']]

        self.assertNotIn('unique', kinds)
        self.assertNotIn('/home/user/thesis_final.pdf', paths)
        self.assertEqual(cleanup_plan['execution']['automatic_deletion'], False)
        self.assertTrue(cleanup_plan['fingerprint_sha256'])

    def test_cleanup_plan_names_a_deterministic_duplicate_survivor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duplicate_a = root / 'a.iso'
            duplicate_z = root / 'z.iso'
            duplicate_a.write_bytes(b'x' * 4096)
            duplicate_z.write_bytes(b'x' * 4096)
            files = scan.scan(root)
            cleanup_plan = plan.build(files, dedup.duplicates(files), root, now=self.now)

            self.assertEqual(len(cleanup_plan['recommendations']), 1)
            item = cleanup_plan['recommendations'][0]
            self.assertEqual(item['kind'], 'duplicate')
            self.assertEqual(item['path'], str(duplicate_z))
            self.assertEqual(item['survivor_path'], str(duplicate_a))
            self.assertEqual(item['recovery_evidence']['type'], 'byte_for_byte_match')
            self.assertEqual(item['recovery_evidence']['strength'], 'direct')
            self.assertIn(str(duplicate_a), item['recovery_evidence']['detail'])
            self.assertEqual(item['observed_identity']['size'], 4096)

    def test_byte_comparison_confirms_duplicate_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / 'left.bin'
            right = root / 'right.bin'
            left.write_bytes(b'x' * 4096)
            right.write_bytes(b'x' * 4096)
            self.assertTrue(dedup.same_content(left, right))

            right.write_bytes(b'y' * 4096)
            self.assertFalse(dedup.same_content(left, right))

    def test_hardlinks_are_not_treated_as_reclaimable_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.bin'
            alias = root / 'alias.bin'
            source.write_bytes(b'x' * 4096)
            os.link(source, alias)

            def info(path):
                st = path.stat()
                return scan.FileInfo(str(path), st.st_size, st.st_atime, st.st_mtime,
                                     st.st_ino, st.st_dev)

            self.assertEqual(dedup.duplicates([info(source), info(alias)]), [])

    def test_snapshots_measure_observed_net_growth(self):
        previous = snapshot.capture(self.files, '/app', 1000, now=100)
        later_files = self.files + [
            scan.FileInfo('/app/.cache/new-build', 86400, self.now, self.now, 99)]
        current = snapshot.capture(later_files, '/app', 500, now=100 + 86400)

        observed = snapshot.observed_growth(previous, current)
        self.assertEqual(observed['net_bytes'], 86400)
        self.assertEqual(observed['bytes_per_day'], 86400)

    def test_snapshots_fit_a_local_linear_growth_trend(self):
        first = snapshot.capture(self.files, '/app', 1000, now=100)
        second = snapshot.capture(
            self.files + [scan.FileInfo('/app/.cache/day-one', 86400,
                                        self.now, self.now, 98)],
            '/app', 900, now=100 + 86400)
        third = snapshot.capture(
            self.files + [scan.FileInfo('/app/.cache/day-two', 172800,
                                        self.now, self.now, 97)],
            '/app', 800, now=100 + 172800)

        trend = snapshot.linear_trend([first, second, third])
        self.assertEqual(trend['sample_count'], 3)
        self.assertAlmostEqual(trend['bytes_per_day'], 86400)
        self.assertAlmostEqual(trend['r_squared'], 1.0)

        two_point_trend = snapshot.linear_trend([first, second])
        self.assertIsNone(two_point_trend['r_squared'])

    def test_cleanup_plan_verification_rechecks_manifest_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keeper = root / 'a.iso'
            duplicate = root / 'z.iso'
            keeper.write_bytes(b'x' * 4096)
            duplicate.write_bytes(b'x' * 4096)
            files = scan.scan(root)
            cleanup_plan = plan.build(files, dedup.duplicates(files), root,
                                      now=self.now)

            verified = plan.verify(cleanup_plan)
            self.assertTrue(verified['fingerprint_valid'])
            self.assertTrue(verified['valid'])

            tampered = copy.deepcopy(cleanup_plan)
            tampered['safety']['rule'] = 'changed after review'
            self.assertFalse(plan.verify(tampered)['fingerprint_valid'])

            duplicate.write_bytes(b'y' * 4096)
            stale = plan.verify(cleanup_plan)
            self.assertFalse(stale['valid'])
            self.assertIn('candidate', stale['recommendations'][0]['reasons'][0])

    def test_plan_verification_rejects_paths_outside_its_scan_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'scan-root'
            root.mkdir()
            keeper = root / 'a.iso'
            duplicate = root / 'z.iso'
            keeper.write_bytes(b'x' * 4096)
            duplicate.write_bytes(b'x' * 4096)
            cleanup_plan = plan.build(
                scan.scan(root), dedup.duplicates(scan.scan(root)), root, now=self.now)

            tampered = copy.deepcopy(cleanup_plan)
            tampered['recommendations'][0]['path'] = str(Path(tmp) / 'outside.iso')
            unsigned = {key: value for key, value in tampered.items()
                        if key != 'fingerprint_sha256'}
            tampered['fingerprint_sha256'] = plan._fingerprint(unsigned)

            result = plan.verify(tampered)
            self.assertFalse(result['valid'])
            self.assertTrue(any(
                'outside the selected scan root' in reason
                for reason in result['recommendations'][0]['reasons']))

    def test_cli_handles_an_invalid_plan_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / 'broken-plan.json'
            broken.write_text('{not json', encoding='utf-8')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = cli.main(['--verify-plan', str(broken)])

            self.assertEqual(status, 2)
            self.assertIn('unavailable for review', output.getvalue())

    def test_demo_fixture_exercises_safe_and_protected_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = demo.create(Path(tmp) / 'fixture')
            files = scan.scan(root)
            groups = dedup.duplicates(files)
            cleanup_plan = plan.build(files, groups, root, now=self.now)
            paths = {item['path'] for item in cleanup_plan['recommendations']}

            self.assertIn(str(root / 'downloads' / 'boss-image-copy.iso'), paths)
            self.assertIn(str(root / 'workspace' / 'node_modules' / '.cache' / 'bundle.bin'),
                          paths)
            self.assertNotIn(str(root / 'documents' / 'capstone-thesis.txt'), paths)
            self.assertNotIn(str(root / 'hardlinks' / 'alias.bin'), paths)
            self.assertTrue(plan.verify(cleanup_plan)['valid'])

    def test_demo_fixture_refuses_a_non_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'keep.txt').write_text('do not touch', encoding='utf-8')
            with self.assertRaises(ValueError):
                demo.create(root)

    def test_scan_prunes_repository_and_credential_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            visible = root / 'visible.txt'
            visible.write_text('candidate', encoding='utf-8')
            (root / '.git').mkdir()
            (root / '.git' / 'config').write_text('sensitive repo metadata', encoding='utf-8')
            (root / '.ssh').mkdir()
            (root / '.ssh' / 'id_ed25519').write_text('sensitive key material', encoding='utf-8')

            paths = {item.path for item in scan.scan(root)}
            self.assertEqual(paths, {str(visible)})
            with self.assertRaises(ValueError):
                scan.scan(root / '.ssh')

    def test_whole_dependency_and_environment_trees_are_not_assumed_regenerable(self):
        package = scan.FileInfo('/usr/lib/python3.12/site-packages/tool.py', 4096,
                                self.now, self.now, 200)
        environment = scan.FileInfo('/home/user/project/.venv/bin/python', 4096,
                                    self.now, self.now, 201)
        dependency = scan.FileInfo('/home/user/project/node_modules/lib/index.js',
                                   4096, self.now, self.now, 202)

        self.assertEqual(regret.classify(package, False), 'unique')
        self.assertEqual(regret.classify(environment, False), 'unique')
        self.assertEqual(regret.classify(dependency, False), 'unique')

    def test_report_paths_are_relative_to_the_selected_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / 'workspace' / 'node_modules' / 'bundle.bin'
            nested.parent.mkdir(parents=True)
            nested.write_bytes(b'x')
            self.assertEqual(report._display_path(nested, root),
                             'workspace/node_modules/bundle.bin')

    def test_report_evidence_labels_do_not_expose_the_selected_root(self):
        root = Path('/private/selected-root')
        row = {
            'kind': 'duplicate',
            'survivor_path': str(root / 'archive' / 'source.iso'),
            'recovery_evidence': {
                'strength': 'direct',
                'detail': f'full-content digest matches {root}',
            },
        }
        label = report._evidence_label(row, root)
        self.assertIn('archive/source.iso', label)
        self.assertNotIn(str(root), label)

    def test_cli_history_uses_the_local_linear_trend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = demo.create(Path(tmp) / 'fixture')
            files = scan.scan(root)
            previous = snapshot.capture(
                files, root, shutil.disk_usage(root).free, now=time.time() - 86400)
            previous['used_bytes'] -= 1024
            previous_path = Path(tmp) / 'previous.json'
            snapshot.write(previous, previous_path)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                cli.main([str(root), '--history', str(previous_path), '--limit', '1'])

            self.assertIn('local linear trend from 2 snapshots', output.getvalue())


if __name__ == '__main__':
    unittest.main()
