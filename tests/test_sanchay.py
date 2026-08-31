import subprocess
import tempfile
import time
import unittest
import importlib.util
from unittest import mock
import argparse
import os
import copy
import contextlib
import io
import shutil
from types import SimpleNamespace
from pathlib import Path

from sanchay import (cli, dedup, demo, forecast, managed, plan, regret, report,
                     scan, snapshot, storage)


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

    def test_reclaim_target_parser_accepts_human_units(self):
        self.assertEqual(cli.parse_reclaim_bytes('600M'), 600 * 1024 ** 2)
        self.assertEqual(cli.parse_reclaim_bytes('1.5 GiB'), int(1.5 * 1024 ** 3))
        with self.assertRaises(argparse.ArgumentTypeError):
            cli.parse_reclaim_bytes('0')
        with self.assertRaises(argparse.ArgumentTypeError):
            cli.parse_reclaim_bytes('enough')

    def test_reclaim_target_selects_only_evidence_backed_candidates_until_met(self):
        candidates = [
            scan.FileInfo('/app/.cache/large.bin', 5000, self.now, self.now - 86400 * 90, 301),
            scan.FileInfo('/app/.cache/small.bin', 4000, self.now, self.now - 86400 * 45, 302),
            scan.FileInfo('/home/user/only-copy.bin', 50000, self.now, self.now - 86400 * 365, 303),
        ]
        cleanup_plan = plan.build(candidates, [], '/app', now=self.now, limit=1,
                                  target_reclaim_bytes=6000)
        selection = cleanup_plan['selection']

        self.assertEqual([item['path'] for item in cleanup_plan['recommendations']],
                         ['/app/.cache/large.bin', '/app/.cache/small.bin'])
        self.assertEqual(selection['target_reclaim_bytes'], 6000)
        self.assertEqual(selection['selected_reclaim_bytes'], 9000)
        self.assertTrue(selection['target_met'])
        self.assertEqual(selection['shortfall_bytes'], 0)
        self.assertNotIn('/home/user/only-copy.bin',
                         [item['path'] for item in cleanup_plan['recommendations']])

    def test_reclaim_target_reports_an_evidence_limited_shortfall(self):
        candidates = [
            scan.FileInfo('/app/.cache/only.bin', 4000, self.now, self.now - 86400 * 90, 304),
            scan.FileInfo('/home/user/only-copy.bin', 50000, self.now, self.now - 86400 * 365, 305),
        ]
        cleanup_plan = plan.build(candidates, [], '/app', now=self.now,
                                  target_reclaim_bytes=6000)
        selection = cleanup_plan['selection']

        self.assertFalse(selection['target_met'])
        self.assertEqual(selection['selected_reclaim_bytes'], 4000)
        self.assertEqual(selection['shortfall_bytes'], 2000)

    def test_boss_managed_storage_is_deferred_to_its_owning_tool(self):
        files = [
            scan.FileInfo('/home/user/.cache/build.bin', 4000, self.now,
                          self.now - 86400 * 90, 701),
            scan.FileInfo('/var/cache/apt/archives/boss-tools.deb', 12000,
                          self.now, self.now - 86400 * 90, 702),
            scan.FileInfo('/var/log/journal/machine/system.journal', 16000,
                          self.now, self.now - 86400 * 90, 703),
            scan.FileInfo('/var/lib/docker/overlay2/layer/diff.bin', 22000,
                          self.now, self.now - 86400 * 90, 704),
            scan.FileInfo('/var/lib/containerd/content/blobs/sha256/blob', 24000,
                          self.now, self.now - 86400 * 90, 705),
            scan.FileInfo('/var/lib/flatpak/repo/objects/object', 28000,
                          self.now, self.now - 86400 * 90, 706),
            scan.FileInfo('/home/user/project/var/cache/apt/archives/not-system.deb',
                          20000, self.now, self.now - 86400 * 90, 707),
        ]

        cleanup_plan = plan.build(files, [], '/', now=self.now,
                                  target_reclaim_bytes=6000)
        selected_paths = [item['path'] for item in cleanup_plan['recommendations']]
        advisory = {item['key']: item
                    for item in cleanup_plan['safety']['managed_operational_storage']}

        self.assertEqual(selected_paths, ['/home/user/.cache/build.bin'])
        self.assertFalse(cleanup_plan['selection']['target_met'])
        self.assertEqual(cleanup_plan['selection']['shortfall_bytes'], 2000)
        self.assertEqual(cleanup_plan['safety']['deferred_managed_entries'], 5)
        self.assertEqual(cleanup_plan['safety']['deferred_managed_bytes'], 102000)
        self.assertIn('apt_archive_cache', advisory)
        self.assertIn('persistent_system_journal', advisory)
        self.assertIn('docker_engine_storage', advisory)
        self.assertIn('container_runtime_storage', advisory)
        self.assertIn('flatpak_system_installation', advisory)
        self.assertIn('apt-get autoclean', advisory['apt_archive_cache']['review_action'])
        self.assertIn('journalctl --disk-usage',
                      advisory['persistent_system_journal']['review_action'])
        self.assertIn('docker system df -v',
                      advisory['docker_engine_storage']['review_action'])
        self.assertIn('flatpak uninstall --unused',
                      advisory['flatpak_system_installation']['review_action'])
        self.assertEqual(managed.classify(files[-1].path), None)
        self.assertEqual(managed.classify('/var/lib/docker-old/layer.bin'), None)
        self.assertEqual(managed.classify('/home/user/project/var/lib/docker/layer.bin'),
                         None)
        self.assertEqual(regret.classify(files[-1], False), 'unique')
        self.assertEqual(managed.content_candidates(files), [files[0], files[-1]])

    @unittest.skipUnless(importlib.util.find_spec('pandas'),
                         'requires the optional report dependencies')
    def test_report_separates_system_managed_storage_from_file_cleanup(self):
        files = [
            scan.FileInfo('/home/user/.cache/build.bin', 4000, self.now,
                          self.now - 86400 * 90, 711),
            scan.FileInfo('/var/cache/apt/archives/boss-tools.deb', 12000,
                          self.now, self.now - 86400 * 90, 712),
            scan.FileInfo('/var/log/journal/machine/system.journal', 16000,
                          self.now, self.now - 86400 * 90, 713),
            scan.FileInfo('/var/lib/docker/overlay2/layer/diff.bin', 22000,
                          self.now, self.now - 86400 * 90, 714),
            scan.FileInfo('/var/lib/containerd/content/blobs/sha256/blob', 24000,
                          self.now, self.now - 86400 * 90, 715),
            scan.FileInfo('/var/lib/flatpak/repo/objects/object', 28000,
                          self.now, self.now - 86400 * 90, 716),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'report.html'
            report.build(files, '/', 1000000, output, cross_filesystems=True)
            page = output.read_text(encoding='utf-8')

        self.assertIn('System-managed storage', page)
        self.assertIn('APT archive cache', page)
        self.assertIn('Persistent systemd journal', page)
        self.assertIn('Docker Engine storage', page)
        self.assertIn('Container runtime storage', page)
        self.assertIn('Flatpak system installation', page)
        self.assertIn('excluded from file-level reclamation', page)
        self.assertIn('not calculated across multiple filesystems', page)
        self.assertIn('Cross-filesystem inventory; no aggregate free-space or reclaim target', page)
        self.assertIn('Allocated inventory', page)
        self.assertIn('no shared free-space claim', page)

    def test_cli_labels_managed_storage_as_deferred_not_reclaimable(self):
        files = [
            scan.FileInfo('/home/user/.cache/build.bin', 4000, self.now,
                          self.now - 86400 * 90, 721),
            scan.FileInfo('/var/cache/apt/archives/boss-tools.deb', 12000,
                          self.now, self.now - 86400 * 90, 722),
            scan.FileInfo('/var/lib/docker/overlay2/layer/diff.bin', 22000,
                          self.now, self.now - 86400 * 90, 723),
        ]
        output = io.StringIO()
        with mock.patch.object(scan, 'scan', return_value=files), \
                mock.patch.object(shutil, 'disk_usage',
                                  return_value=SimpleNamespace(free=1000000)), \
                contextlib.redirect_stdout(output):
            status = cli.main(['/'])

        rendered = output.getvalue()
        self.assertIsNone(status)
        self.assertIn('managed:', rendered)
        self.assertIn('APT archive cache', rendered)
        self.assertIn('Docker Engine storage', rendered)
        self.assertIn('never selected as file cleanup candidates', rendered)

    def test_cross_filesystem_scan_avoids_a_single_mount_capacity_claim(self):
        files = [
            scan.FileInfo('/home/user/.cache/build.bin', 4000, self.now,
                          self.now - 86400 * 90, 731, device=101),
            scan.FileInfo('/mnt/data/only-copy.bin', 12000, self.now,
                          self.now - 86400 * 90, 732, device=202),
        ]
        output = io.StringIO()
        with mock.patch.object(scan, 'scan', return_value=files), \
                mock.patch.object(shutil, 'disk_usage',
                                  side_effect=AssertionError('must not use root free space')), \
                contextlib.redirect_stdout(output):
            status = cli.main(['/', '--cross-filesystems'])

        self.assertIsNone(status)
        self.assertIn('across 2 filesystems', output.getvalue())
        self.assertIn('not calculated across multiple filesystems', output.getvalue())

    def test_cross_filesystem_rejects_a_shared_reclaim_target(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.main(['/', '--cross-filesystems', '--target-reclaim', '1G'])

    def test_cross_filesystem_plan_carries_its_capacity_boundary(self):
        document = plan.build(self.files, [], '/', cross_filesystems=True)
        self.assertEqual(document['safety']['scan_scope'],
                         'cross_filesystem_inventory')
        self.assertIn('no shared free-space',
                      document['safety']['capacity_boundary'])
        with self.assertRaisesRegex(ValueError, 'shared reclaim target'):
            plan.build(self.files, [], '/', target_reclaim_bytes=1,
                       cross_filesystems=True)

    def test_cross_filesystem_rejects_capacity_history_inputs(self):
        inputs = (
            ['--snapshot', 'baseline.json'],
            ['--compare', 'baseline.json'],
            ['--history', 'day-1.json', 'day-7.json'],
        )
        for extra in inputs:
            with self.subTest(extra=extra), self.assertRaises(SystemExit), \
                    contextlib.redirect_stderr(io.StringIO()):
                cli.main(['/', '--cross-filesystems', *extra])

    def test_cross_filesystem_tui_is_not_silently_downgraded(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.main(['/', '--cross-filesystems', '--tui'])

    def test_reclaim_target_prefers_lowest_risk_with_minimal_safe_excess(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / '.cache' / 'small-safe.bin'
            duplicate_a = root / 'archive' / 'large-source.bin'
            duplicate_z = root / 'downloads' / 'large-copy.bin'
            cache.parent.mkdir(parents=True)
            duplicate_a.parent.mkdir(parents=True)
            duplicate_z.parent.mkdir(parents=True)
            cache.write_bytes(b'c' * 8192)
            duplicate_a.write_bytes(b'd' * 20480)
            duplicate_z.write_bytes(b'd' * 20480)
            old = self.now - 86400 * 300
            os.utime(duplicate_a, (old, old))
            os.utime(duplicate_z, (old, old))

            files = scan.scan(root)
            cleanup_plan = plan.build(files, dedup.duplicates(files), root,
                                      now=self.now, target_reclaim_bytes=6000)
            selection = cleanup_plan['selection']

            self.assertEqual([item['path'] for item in cleanup_plan['recommendations']],
                             [str(cache)])
            self.assertEqual(cleanup_plan['recommendations'][0]['kind'], 'disposable')
            self.assertEqual(selection['selected_reclaim_bytes'], 8192)
            self.assertTrue(selection['target_met'])
            self.assertIn('lowest-recovery-risk', selection['method'])

    def test_equal_priority_targets_are_selected_by_normalized_path(self):
        candidates = [
            scan.FileInfo('/app/.cache/z-last.bin', 4096, self.now,
                          self.now - 86400 * 90, 306),
            scan.FileInfo('/app/.cache/a-first.bin', 4096, self.now,
                          self.now - 86400 * 90, 307),
        ]
        cleanup_plan = plan.build(candidates, [], '/app', now=self.now,
                                  target_reclaim_bytes=4096)

        self.assertEqual([item['path'] for item in cleanup_plan['recommendations']],
                         ['/app/.cache/a-first.bin'])

    def test_runway_label_avoids_false_long_range_precision(self):
        self.assertEqual(forecast.runway_label(None), '—')
        self.assertEqual(forecast.runway_label(12.4), '~12 days')
        self.assertEqual(forecast.runway_label(730), '~2.0 years')
        self.assertEqual(forecast.runway_label(3650), '>10 years')

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
            self.assertEqual(item['observed_identity']['allocated_size'], 4096)
            self.assertEqual(cleanup_plan['schema_version'], 5)
            self.assertIn('mtime_ns', item['observed_identity'])
            self.assertEqual(item['decision_trace']['name'], 'regret_aware_priority')
            self.assertEqual(item['decision_trace']['inputs']['reclaimable_allocated_bytes'], 4096)
            self.assertEqual(item['decision_trace']['inputs']['logical_size_bytes'], 4096)
            self.assertEqual(item['decision_trace']['computed_priority'], item['priority'])
            self.assertEqual(
                plan.duplicate_evidence_paths(cleanup_plan),
                frozenset({str(duplicate_a), str(duplicate_z)}))

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

    def test_hashing_rejects_an_inode_replaced_after_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / 'candidate.bin'
            replacement = root / 'replacement.bin'
            candidate.write_bytes(b'a' * 4096)
            info = scan.scan(root)[0]

            replacement.write_bytes(b'b' * 4096)
            os.replace(replacement, candidate)

            self.assertIsNone(dedup._digest(info.path, expected=info, root=root))

    @unittest.skipUnless(dedup.root_anchoring_available(),
                         'requires POSIX descriptor-relative no-follow support')
    def test_root_anchored_reader_rejects_a_parent_symlink_swap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'root'
            nested = root / 'cache'
            outside = Path(tmp) / 'outside'
            nested.mkdir(parents=True)
            outside.mkdir()
            candidate = nested / 'candidate.bin'
            candidate.write_bytes(b'a' * 4096)
            (outside / 'candidate.bin').write_bytes(b'secret' * 683)
            info = scan.scan(root)[0]

            nested.rename(root / 'cache-original')
            os.symlink(outside, nested, target_is_directory=True)

            self.assertIsNone(dedup._digest(info.path, expected=info, root=root))

    def test_hardlinks_are_not_treated_as_reclaimable_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.bin'
            alias = root / 'alias.bin'
            source.write_bytes(b'x' * 4096)
            os.link(source, alias)

            self.assertEqual(dedup.duplicates(scan.scan(root)), [])

    def test_mixed_hardlink_and_duplicate_reclaims_only_a_standalone_inode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'a-source.bin'
            alias = root / 'a-alias.bin'
            standalone = root / 'z-standalone.bin'
            source.write_bytes(b'x' * 4096)
            os.link(source, alias)
            standalone.write_bytes(b'x' * 4096)

            files = scan.scan(root)
            with mock.patch.object(dedup, '_digest', wraps=dedup._digest) as digest:
                groups = dedup.duplicates(files)
            copy_map = dedup.confirmed_duplicate_map(groups)
            cleanup_plan = plan.build(files, groups, root, now=self.now)

            self.assertEqual(len(groups), 1)
            self.assertEqual(dedup.reclaimable(groups), 4096)
            self.assertEqual(digest.call_count, 4)
            self.assertEqual(len({str(call.args[0]) for call in digest.call_args_list}), 2)
            self.assertEqual(set(copy_map), {str(standalone)})
            self.assertIn(copy_map[str(standalone)], {str(source), str(alias)})
            self.assertEqual([row['path'] for row in cleanup_plan['recommendations']],
                             [str(standalone)])
            self.assertEqual(cleanup_plan['safety']['excluded_hardlink_entries'], 2)
            self.assertEqual(cleanup_plan['safety']['excluded_hardlink_physical_bytes'],
                             4096)

    def test_physical_storage_metrics_do_not_double_count_hardlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.bin'
            alias = root / 'alias.bin'
            source.write_bytes(b'x' * 4096)
            os.link(source, alias)
            files = scan.scan(root)

            measured_at = source.stat().st_mtime
            captured = snapshot.capture(files, root, 1000, now=100)
            self.assertEqual(storage.physical_bytes(files), 4096)
            self.assertEqual(storage.hardlink_alias_count(files), 1)
            self.assertEqual(captured['schema_version'], 3)
            self.assertEqual(captured['used_bytes'], 4096)
            self.assertEqual(captured['logical_bytes'], 4096)
            self.assertEqual(captured['physical_file_count'], 1)
            self.assertEqual(captured['hardlink_alias_count'], 1)
            self.assertEqual(forecast.daily_growth(files, now=measured_at)[0], 4096)

    def test_allocated_bytes_prevent_sparse_files_from_overstating_reclaim(self):
        sparse = scan.FileInfo('/app/.cache/sparse-image.bin', 1024 ** 3,
                               self.now, self.now - 86400 * 30, 901,
                               allocated_size=4096)
        normal = scan.FileInfo('/app/.cache/normal-cache.bin', 8192,
                               self.now, self.now - 86400 * 30, 902,
                               allocated_size=8192)
        files = [sparse, normal]

        self.assertEqual(storage.logical_bytes(files), 1024 ** 3 + 8192)
        self.assertEqual(storage.physical_bytes(files), 12288)
        self.assertEqual(storage.allocated_bytes(sparse), 4096)
        self.assertEqual(storage.allocated_bytes(
            scan.FileInfo('/app/.cache/fallback.bin', 4096, self.now,
                          self.now, 903)), 4096)
        self.assertEqual(storage.allocated_bytes_from_stat(
            SimpleNamespace(st_size=1024 ** 3, st_blocks=8)), 4096)
        self.assertEqual(storage.allocated_bytes_from_stat(
            SimpleNamespace(st_size=4096)), 4096)

        cleanup_plan = plan.build(files, [], '/app', now=self.now)
        rows = {item['path']: item for item in cleanup_plan['recommendations']}
        self.assertEqual(rows[sparse.path]['size'], 4096)
        self.assertEqual(rows[sparse.path]['logical_size'], 1024 ** 3)
        self.assertEqual(rows[sparse.path]['decision_trace']['inputs']
                         ['reclaimable_allocated_bytes'], 4096)
        self.assertEqual(rows[sparse.path]['decision_trace']['inputs']
                         ['logical_size_bytes'], 1024 ** 3)

        captured = snapshot.capture(files, '/app', 1000, now=100)
        self.assertEqual(captured['schema_version'], 3)
        self.assertEqual(captured['used_bytes'], 12288)
        self.assertEqual(captured['logical_bytes'], 1024 ** 3 + 8192)
        self.assertEqual(forecast.daily_growth(files, now=self.now)[30], 12288)

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

            plan_path = root / 'cleanup-plan.json'
            plan.write(cleanup_plan, plan_path)
            verified = plan.verify(plan.read(plan_path))
            self.assertTrue(verified['fingerprint_valid'])
            self.assertTrue(verified['valid'])

            old_schema = copy.deepcopy(cleanup_plan)
            old_schema['schema_version'] = 4
            unsigned = {key: value for key, value in old_schema.items()
                        if key != 'fingerprint_sha256'}
            old_schema['fingerprint_sha256'] = plan._fingerprint(unsigned)
            legacy_path = root / 'legacy-plan.json'
            plan.write(old_schema, legacy_path)
            with self.assertRaises(ValueError):
                plan.read(legacy_path)

            tampered = copy.deepcopy(cleanup_plan)
            tampered['safety']['rule'] = 'changed after review'
            tampered_result = plan.verify(tampered)
            self.assertFalse(tampered_result['fingerprint_valid'])
            self.assertIn('integrity checksum', tampered_result['reason'])

            duplicate.write_bytes(b'y' * 4096)
            stale = plan.verify(cleanup_plan)
            self.assertFalse(stale['valid'])
            self.assertIn('candidate', stale['recommendations'][0]['reasons'][0])

    def test_cleanup_plan_verification_rejects_changed_hardlink_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / 'workspace' / 'node_modules' / '.cache' / 'bundle.bin'
            cache.parent.mkdir(parents=True)
            cache.write_bytes(b'x' * 4096)
            files = scan.scan(root)
            cleanup_plan = plan.build(files, [], root, now=self.now)

            alias = root / 'workspace' / 'bundle-alias.bin'
            os.link(cache, alias)
            result = plan.verify(cleanup_plan)

            self.assertFalse(result['valid'])
            self.assertTrue(any('candidate nlink changed' in reason
                                for reason in result['recommendations'][0]['reasons']))

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
            self.assertEqual(cleanup_plan['safety']['excluded_hardlink_entries'], 2)
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
            for name in ('.git', '.ssh', '.docker', '.azure', '.oci',
                         '.terraform.d'):
                protected = root / name
                protected.mkdir()
                (protected / 'credential-material').write_text(
                    'sensitive credential material', encoding='utf-8')

            paths = {item.path for item in scan.scan(root)}
            self.assertEqual(paths, {str(visible)})
            for name in ('.ssh', '.docker', '.azure', '.oci', '.terraform.d'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    scan.scan(root / name)

    def test_scan_excludes_common_secret_files_before_metadata_or_hashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            visible = root / 'visible.txt'
            visible.write_text('candidate', encoding='utf-8')
            for name in ('.env', '.env.local', '.npmrc', '.git-credentials',
                         '.terraformrc', 'credentials.tfrc.json', 'id_ed25519',
                         'service.pem', 'token.key', 'vault.kdbx',
                         'credentials.json'):
                (root / name).write_text('secret material', encoding='utf-8')
            (root / '.env.example').write_text('example only', encoding='utf-8')
            (root / 'config.json').write_text('ordinary app configuration',
                                              encoding='utf-8')

            paths = {item.path for item in scan.scan(root)}
            self.assertEqual(paths, {
                str(visible), str(root / '.env.example'), str(root / 'config.json')})

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
