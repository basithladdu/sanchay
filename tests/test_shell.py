import io
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.request import urlopen

from sanchay import actions, advisor, cli, dedup, plan, report, scan
from sanchay.session import ScanSession
from sanchay.shell import ReportServer, SanchayShell, split_arguments
from sanchay.palette import (COMMAND_CHOICES, CONTINUE_PROMPT, STORAGE_MARK,
                             TERMINAL_TITLE, SlashCommandCompleter,
                             can_use_palette, configure_terminal_title,
                             reset_terminal_title, welcome_content,
                             wordmark_width)
from prompt_toolkit.formatted_text import fragment_list_to_text
from sanchay.paths import report_destination
from sanchay.spinner import (LoadingIndicator, format_elapsed,
                             loading_text, shimmer_fragments)
from prompt_toolkit.document import Document


class TestInteractiveShell(unittest.TestCase):
    def _disposable_plan(self, root, names=("build.bin",)):
        cache = Path(root) / ".cache"
        cache.mkdir()
        for index, name in enumerate(names, start=1):
            (cache / name).write_bytes(bytes([index]) * (4096 + index))
        files = scan.scan(root)
        return plan.build(files, [], root, limit=50)

    def test_split_arguments_preserves_quoted_windows_paths(self):
        self.assertEqual(
            split_arguments(r'"C:\Program Files\SANCHAY" --cross-filesystems'),
            [r'C:\Program Files\SANCHAY', '--cross-filesystems'])

    def test_slash_palette_lists_every_command_when_slash_is_typed(self):
        completions = list(SlashCommandCompleter().get_completions(
            Document('/'), mock.Mock()))
        displayed = {completion.display_text for completion in completions}

        self.assertEqual(displayed, {choice.name for choice in COMMAND_CHOICES})
        self.assertTrue(all(completion.display_meta for completion in completions))

    def test_slash_palette_filters_commands_and_preserves_argument_space(self):
        completions = list(SlashCommandCompleter().get_completions(
            Document('/ana'), mock.Mock()))

        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].text, '/analyze')
        self.assertEqual(completions[0].start_position, -4)

    def test_slash_palette_is_disabled_for_redirected_shells(self):
        shell = SanchayShell(stdin=io.StringIO(), stdout=io.StringIO())
        self.assertFalse(can_use_palette(shell))

    def test_interactive_title_identifies_sanchay_and_is_released_on_exit(self):
        with mock.patch('sanchay.palette.set_title') as set_tab_title, \
                mock.patch('sanchay.palette.clear_title') as clear_tab_title:
            configured = configure_terminal_title()
            reset_terminal_title(configured)

        self.assertEqual(TERMINAL_TITLE, '💾 SANCHAY')
        set_tab_title.assert_called_once_with('💾 SANCHAY')
        clear_tab_title.assert_called_once_with()

    def test_terminal_title_falls_back_when_emoji_encoding_is_unavailable(self):
        with mock.patch(
                'sanchay.palette.set_title',
                side_effect=[UnicodeEncodeError('ascii', '💾', 0, 1, 'unsupported'), None],
        ) as set_tab_title:
            configured = configure_terminal_title()

        self.assertTrue(configured)
        self.assertEqual(
            set_tab_title.call_args_list,
            [mock.call('💾 SANCHAY'), mock.call('SANCHAY')],
        )

    def test_welcome_screen_describes_sanchay_and_downloads(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
                os.environ, {'SANCHAY_DOWNLOAD_DIR': tmp}):
            content = welcome_content(columns=120)
        rendered = fragment_list_to_text(content)

        self.assertIn('Welcome to SANCHAY', rendered)
        self.assertIn('What SANCHAY does', rendered)
        self.assertIn('Safety notes', rendered)
        self.assertIn('Unique files stay protected', rendered)
        self.assertIn(str(Path(tmp).resolve()), rendered)
        self.assertNotIn('#', rendered)
        # The wordmark is drawn as solid letters trailed by a contour echo.
        self.assertIn('█' * 7, rendered)
        self.assertIn('╰───██╮', rendered)
        for row in STORAGE_MARK:
            self.assertIn(''.join(text for _, text in row), rendered)
        styles = {style for style, _ in content}
        self.assertIn('class:welcome-logo', styles)
        self.assertIn('class:welcome-logo-shadow', styles)
        self.assertIn('class:storage-red', styles)
        self.assertIn('class:storage-blue', styles)
        self.assertIn('class:storage-green', styles)
        self.assertEqual(CONTINUE_PROMPT, 'Press Enter to continue... ')

    def test_welcome_screen_drops_the_mark_and_wordmark_when_too_narrow(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
                os.environ, {'SANCHAY_DOWNLOAD_DIR': tmp}):
            snug = fragment_list_to_text(
                welcome_content(columns=wordmark_width()))
            narrow = fragment_list_to_text(
                welcome_content(columns=wordmark_width() - 1))

        mark_top = ''.join(text for _, text in STORAGE_MARK[0])
        self.assertIn('█' * 7, snug)
        self.assertNotIn(mark_top, snug)
        self.assertNotIn('█', narrow)
        self.assertIn('S A N C H A Y', narrow)
        self.assertIn('What SANCHAY does', narrow)

    def test_loading_indicator_text_shows_phase_time_and_cancel_hint(self):
        rendered = loading_text('Building the HTML report', '/', 7.9)
        self.assertEqual(
            rendered,
            '[/] Working (7s) | Building the HTML report | Ctrl+C to cancel')

    def test_elapsed_reads_as_a_stopwatch_at_every_scale(self):
        self.assertEqual(format_elapsed(0), '0s')
        self.assertEqual(format_elapsed(7.9), '7s')
        self.assertEqual(format_elapsed(111), '1m 51s')
        self.assertEqual(format_elapsed(3845), '1h 04m')
        self.assertEqual(format_elapsed(-5), '0s')

    def test_shimmer_moves_one_highlight_across_the_word(self):
        def lit(tick):
            fragments = shimmer_fragments(
                'Working', tick, base='base', mid='mid', glow='glow')
            text = ''.join(text for _, text in fragments)
            self.assertEqual(text, 'Working')
            return ''.join(
                text for style, text in fragments if style == 'glow')

        highlights = [lit(tick) for tick in range(13)]
        self.assertEqual(''.join(highlights), 'Working')
        # The sweep repeats, so the animation never settles on one frame.
        self.assertEqual(lit(3), lit(16))

    def test_loading_animation_is_silent_for_redirected_output(self):
        output = io.StringIO()
        with LoadingIndicator(output, 'Scanning'):
            pass
        self.assertEqual(output.getvalue(), '')

    def test_report_chart_falls_back_when_optional_visualization_is_missing(self):
        missing = ModuleNotFoundError("No module named 'plotly'", name='plotly')
        with mock.patch('sanchay.report.import_module', side_effect=missing):
            rendered = report._recoverability_chart([], set(), '/')

        self.assertIn('Chart unavailable', rendered)
        self.assertIn('AI recommendations', rendered)
        self.assertIn('.[viz]', rendered)

    def test_report_still_writes_without_optional_visualization(self):
        missing = ModuleNotFoundError("No module named 'pandas'", name='pandas')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'document.txt').write_text('retain me', encoding='utf-8')
            files = scan.scan(root)
            output = root / 'report.html'

            with mock.patch('sanchay.report.import_module', side_effect=missing):
                written = report.build(files, root, 1_000_000, output)

            rendered = output.read_text(encoding='utf-8')

        self.assertEqual(written, output)
        self.assertIn('Chart unavailable', rendered)
        self.assertIn('AI Recommendation Model', rendered)
        self.assertIn('Reviewable Storage Candidates', rendered)

    def test_report_chart_does_not_hide_unrelated_import_errors(self):
        missing = ModuleNotFoundError(
            "No module named 'sanchay.internal'", name='sanchay.internal')
        with mock.patch('sanchay.report.import_module', side_effect=missing):
            with self.assertRaises(ModuleNotFoundError):
                report._recoverability_chart([], set(), '/')

    def test_slash_prefix_routes_to_regular_cmd_handlers(self):
        shell = SanchayShell(stdout=io.StringIO())
        command, argument, parsed = shell.parseline('/scan "C:\\Data Drive"')
        self.assertEqual(command, 'scan')
        self.assertEqual(argument, '"C:\\Data Drive"')
        self.assertEqual(parsed, 'scan "C:\\Data Drive"')

        command, argument, _ = shell.parseline('/verify-plan plan.json')
        self.assertEqual(command, 'verify_plan')
        self.assertEqual(argument, 'plan.json')

    def test_help_renders_a_command_purpose_table(self):
        output = io.StringIO()
        shell = SanchayShell(stdout=output)

        shell.onecmd('/help')

        rendered = output.getvalue()
        self.assertIn('SANCHAY command reference', rendered)
        self.assertIn('COMMAND', rendered)
        self.assertIn('PURPOSE', rendered)
        self.assertIn('/analyze <path> [options]', rendered)
        self.assertIn('/ps', rendered)
        self.assertIn('/stop <id|all>', rendered)
        self.assertIn('always stored in Downloads', rendered)

    def test_about_explains_product_and_safety_boundary(self):
        output = io.StringIO()
        shell = SanchayShell(stdout=output)

        shell.onecmd('/about')

        rendered = output.getvalue()
        self.assertIn('evidence-first storage review assistant', rendered)
        self.assertIn('auditable HTML report in Downloads', rendered)
        self.assertIn('disabled by default', rendered)

    def test_ai_command_selects_ollama_for_the_next_scan(self):
        output = io.StringIO()
        shell = SanchayShell(stdout=output)
        runtime = {
            "ollama_available": True,
            "ollama_models": ["qwen2.5-coder:7b"],
            "selected_ollama_model": "qwen2.5-coder:7b",
            "api_configured": False,
        }

        with mock.patch.object(advisor, "runtime_status", return_value=runtime):
            shell.onecmd('/ai ollama qwen2.5-coder:7b')

        self.assertEqual(shell.advisor_config.provider, "ollama")
        self.assertEqual(shell.advisor_config.ollama_model, "qwen2.5-coder:7b")
        self.assertIn("applies to the next /analyze", output.getvalue())
        self.assertNotIn("API key", str(shell.advisor_config.public()))

    def test_ai_off_rejects_a_model_name(self):
        output = io.StringIO()
        shell = SanchayShell(stdout=output)

        shell.onecmd('/ai off unexpected-model')

        self.assertIn("off mode does not accept", output.getvalue())

    def test_pasted_file_path_gets_a_command_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / 'screen shot.png'
            image.write_bytes(b'not really an image')
            output = io.StringIO()
            shell = SanchayShell(stdout=output)
            shell.onecmd(f'/"{image}"')

        message = output.getvalue()
        self.assertIn('file path, not a SANCHAY command', message)
        self.assertIn('/scan', message)
        self.assertNotIn('Unknown command', message)

    def test_candidate_output_names_the_active_scan_and_keeps_every_row(self):
        session = mock.Mock()
        session.ready = True
        session.stale = False
        session.root = str(Path('scan-root').resolve())
        session.candidates.return_value = [
            {'path': str(Path(session.root) / f'file-{index}.bin'),
             'size': index, 'kind': 'duplicate', 'staleness': 0}
            for index in range(1, 11)
        ]
        output = io.StringIO()
        shell = SanchayShell(session=session, stdout=output)

        shell.onecmd('/candidates 10')

        rendered = output.getvalue()
        self.assertIn(f'Candidates from active scan: {session.root}', rendered)
        for index in range(1, 11):
            self.assertIn(f'{index:>2}  ', rendered)

    def test_cli_without_arguments_starts_the_interactive_shell(self):
        with mock.patch('sanchay.shell.run', return_value=0) as run_shell:
            self.assertEqual(cli.main([]), 0)
        run_shell.assert_called_once_with()

    def test_analyze_scans_lists_candidates_and_writes_report_in_one_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'scan root'
            root.mkdir()
            requested_path = Path(tmp) / 'somewhere-else' / 'result.html'
            downloads = Path(tmp) / 'Downloads'
            output_path = downloads / 'result.html'
            session = mock.Mock()
            session.root = str(root.resolve())
            session.scan.return_value = {
                'root': session.root,
                'file_entries': 2,
                'allocated_bytes': 8192,
                'duplicate_groups': 1,
                'duplicate_reclaimable_bytes': 4096,
                'candidate_count': 1,
                'protected_unique_files': 1,
                'coverage': {'complete': True},
            }
            session.candidates.return_value = [{
                'path': str(root / 'copy.bin'),
                'size': 4096,
                'kind': 'duplicate',
                'staleness': 0.5,
            }]
            session.write_report.return_value = str(output_path.resolve())
            output = io.StringIO()
            shell = SanchayShell(session=session, stdout=output)

            with mock.patch.dict(
                    os.environ, {'SANCHAY_DOWNLOAD_DIR': str(downloads)}):
                shell.onecmd(
                    f'/analyze "{root}" --report "{requested_path}" --limit 1')

        session.scan.assert_called_once_with(
            str(root), cross_filesystems=False)
        session.candidates.assert_called_once_with(1)
        session.write_report.assert_called_once_with(str(output_path))
        rendered = output.getvalue()
        self.assertIn('Candidates from active scan:', rendered)
        self.assertIn('Analysis complete.', rendered)
        self.assertIn('run /serve separately', rendered)

    def test_interactive_report_destination_is_always_downloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            downloads = Path(tmp) / 'Downloads'
            with mock.patch.dict(
                    os.environ, {'SANCHAY_DOWNLOAD_DIR': str(downloads)}):
                destination = report_destination(
                    r'C:\unrelated\folder\my storage review')

            self.assertEqual(destination, downloads.resolve() / 'my storage review.html')
            self.assertTrue(downloads.is_dir())

    def test_report_prints_and_uses_the_downloads_html_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            downloads = Path(tmp) / 'Downloads'
            expected = downloads.resolve() / 'review.html'
            session = mock.Mock()
            session.ready = True
            session.stale = False
            session.root = str(Path(tmp).resolve())
            session.write_report.return_value = str(expected)
            output = io.StringIO()
            shell = SanchayShell(session=session, stdout=output)

            with mock.patch.dict(
                    os.environ, {'SANCHAY_DOWNLOAD_DIR': str(downloads)}):
                shell.onecmd('/report "C:\\other\\review.html"')

        session.write_report.assert_called_once_with(str(expected))
        self.assertIn('HTML report destination: ' + str(expected), output.getvalue())
        self.assertIn('Report created: ' + str(expected), output.getvalue())

    def test_run_is_an_alias_for_analyze(self):
        self.assertIs(SanchayShell.do_run, SanchayShell.do_analyze)

    def test_session_passes_precomputed_evidence_to_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'scan-root'
            root.mkdir()
            left = root / 'left.bin'
            right = root / 'right.bin'
            left.write_bytes(b'x' * 4096)
            right.write_bytes(b'x' * 4096)
            session = ScanSession()
            summary = session.scan(str(root))
            output = Path(tmp) / 'report.html'

            with mock.patch('sanchay.session.report.build',
                            return_value=str(output)) as build_report:
                written = session.write_report(str(output))

        self.assertEqual(summary['duplicate_groups'], 1)
        self.assertEqual(written, str(output.resolve()))
        kwargs = build_report.call_args.kwargs
        self.assertIs(kwargs['duplicate_groups'], session.groups)
        self.assertIs(kwargs['cleanup_plan'], session.active_plan)

    @unittest.skipUnless(importlib.util.find_spec('pandas')
                         and importlib.util.find_spec('plotly'),
                         'requires optional report dependencies')
    def test_report_reuses_precomputed_groups_and_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = self._disposable_plan(tmp)
            files = scan.scan(tmp)
            output = Path(tmp) / 'report.html'
            with mock.patch.object(report.dedup, 'duplicates',
                                   side_effect=AssertionError('duplicate rescan')), \
                    mock.patch.object(report.plan, 'build',
                                      side_effect=AssertionError('plan rebuild')):
                report.build(
                    files, tmp, 1000000, output,
                    duplicate_groups=[], cleanup_plan=document)

            self.assertTrue(output.is_file())
            self.assertIn('Scan target:', output.read_text(encoding='utf-8'))

    def test_report_server_binds_to_loopback_and_serves_latest_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / 'review report.html'
            report_path.write_text('<h1>SANCHAY report</h1>', encoding='utf-8')
            server = ReportServer()
            try:
                url = server.start(report_path, port=0)
                with urlopen(url, timeout=3) as response:
                    payload = response.read().decode('utf-8')
            finally:
                server.stop()

        self.assertTrue(url.startswith('http://127.0.0.1:'))
        self.assertIn('review%20report.html', url)
        self.assertIn('SANCHAY report', payload)

    def test_serve_chooses_a_free_port_and_prints_the_exact_report_url(self):
        session = mock.Mock()
        session.last_report = str(Path('real-report.html').resolve())
        report_server = mock.Mock()
        report_server.start.return_value = (
            'http://127.0.0.1:54321/real-report.html')
        output = io.StringIO()
        shell = SanchayShell(
            session=session, stdout=output, report_server=report_server)

        shell.onecmd('/serve')

        report_server.start.assert_called_once_with(
            session.last_report, port=0)
        self.assertIn(
            'Exact URL for the active scan report: '
            'http://127.0.0.1:54321/real-report.html',
            output.getvalue())
        self.assertIn('1 background task running',
                      shell.background_tasks.status_line())

        shell.onecmd('/ps')
        self.assertIn('report-server', output.getvalue())
        self.assertIn('http://127.0.0.1:54321/real-report.html', output.getvalue())

        shell.onecmd('/stop 1')
        report_server.stop.assert_called_once_with()
        self.assertEqual(shell.background_tasks.status_line(), '')
        self.assertIn('Stopped background task 1', output.getvalue())

    def test_delete_requires_permission_and_exact_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = self._disposable_plan(tmp)
            target = Path(document['recommendations'][0]['path'])
            permission = actions.ActionPermission()

            with self.assertRaises(actions.ActionDenied):
                actions.delete(document, 1, permission, 'DELETE:1')
            self.assertTrue(target.exists())

            self.assertTrue(permission.enable(actions.AUTHORIZATION_PHRASE))
            with self.assertRaises(actions.ActionDenied):
                actions.delete(document, 1, permission, 'DELETE')
            self.assertTrue(target.exists())
            self.assertFalse(permission.enabled)

            self.assertTrue(permission.enable(actions.AUTHORIZATION_PHRASE))
            actions.delete(document, 1, permission, 'DELETE:1')
            self.assertFalse(target.exists())

    def test_delete_fails_closed_when_candidate_identity_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = self._disposable_plan(tmp)
            target = Path(document['recommendations'][0]['path'])
            target.write_bytes(b'changed')
            permission = actions.ActionPermission()
            permission.enable(actions.AUTHORIZATION_PHRASE)

            with self.assertRaises(actions.ActionDenied):
                actions.delete(document, 1, permission, 'DELETE:1')
            self.assertTrue(target.exists())

    def test_delete_requires_complete_single_filesystem_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / '.cache'
            cache.mkdir()
            target = cache / 'build.bin'
            target.write_bytes(b'x' * 4096)
            files = scan.scan(tmp)
            document = plan.build(
                files, [], tmp, scan_coverage=scan.ScanCoverage(1, 0))
            permission = actions.ActionPermission()
            permission.enable(actions.AUTHORIZATION_PHRASE)

            with self.assertRaisesRegex(actions.ActionDenied, 'coverage is incomplete'):
                actions.delete(document, 1, permission, 'DELETE:1')
            self.assertTrue(target.exists())

    def test_duplicate_delete_requires_the_exact_named_retained_peer(self):
        with tempfile.TemporaryDirectory() as tmp:
            left = Path(tmp) / 'left.bin'
            right = Path(tmp) / 'right.bin'
            left.write_bytes(b'x' * 4096)
            right.write_bytes(b'x' * 4096)
            files = scan.scan(tmp)
            groups = dedup.duplicates(files, root=tmp)
            document = plan.build(files, groups, tmp)
            item = document['recommendations'][0]
            target = Path(item['path'])
            survivor = Path(item['survivor_path'])
            permission = actions.ActionPermission()

            permission.enable(actions.AUTHORIZATION_PHRASE)
            with self.assertRaisesRegex(actions.ActionDenied, 'requires --retain'):
                actions.delete(document, 1, permission, 'DELETE:1')

            permission.enable(actions.AUTHORIZATION_PHRASE)
            with self.assertRaisesRegex(actions.ActionDenied, 'does not match'):
                actions.delete(
                    document, 1, permission, 'DELETE:1', retained_path=target)

            permission.enable(actions.AUTHORIZATION_PHRASE)
            actions.delete(
                document, 1, permission, 'DELETE:1', retained_path=survivor)
            self.assertFalse(target.exists())
            self.assertTrue(survivor.exists())

    @unittest.skipUnless(actions._descriptor_actions_available(),
                         'requires POSIX descriptor-relative no-follow support')
    def test_delete_rejects_a_parent_symlink_swap_on_linux(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = self._disposable_plan(tmp)
            cache = Path(tmp) / '.cache'
            moved_cache = Path(tmp) / 'cache-real'
            cache.rename(moved_cache)
            cache.symlink_to(moved_cache, target_is_directory=True)
            permission = actions.ActionPermission()
            permission.enable(actions.AUTHORIZATION_PHRASE)

            with self.assertRaises(actions.ActionDenied):
                actions.delete(document, 1, permission, 'DELETE:1')
            self.assertTrue((moved_cache / 'build.bin').exists())

    def test_move_is_same_filesystem_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = self._disposable_plan(tmp)
            target = Path(document['recommendations'][0]['path'])
            archive = Path(tmp) / 'archive'
            archive.mkdir()
            destination = archive / target.name
            destination.write_bytes(b'existing')
            permission = actions.ActionPermission()
            permission.enable(actions.AUTHORIZATION_PHRASE)

            with self.assertRaises(actions.ActionDenied):
                actions.move(document, 1, str(destination), permission, 'MOVE:1')
            self.assertTrue(target.exists())
            self.assertEqual(destination.read_bytes(), b'existing')

            destination.unlink()
            permission.enable(actions.AUTHORIZATION_PHRASE)
            item, written = actions.move(
                document, 1, str(destination), permission, 'MOVE:1')
            self.assertEqual(item['path'], str(target))
            self.assertEqual(written, str(destination.resolve()))
            self.assertFalse(target.exists())
            self.assertTrue(destination.exists())

    def test_clean_only_removes_disposable_active_plan_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = self._disposable_plan(tmp, names=('one.bin', 'two.bin'))
            protected = Path(tmp) / 'family-photo.jpg'
            protected.write_bytes(b'irreplaceable')
            permission = actions.ActionPermission()
            permission.enable(actions.AUTHORIZATION_PHRASE)

            completed = actions.clean(document, permission, 'CLEAN:2')

            self.assertEqual(len(completed), 2)
            self.assertTrue(protected.exists())
            self.assertFalse((Path(tmp) / '.cache' / 'one.bin').exists())
            self.assertFalse((Path(tmp) / '.cache' / 'two.bin').exists())

    def test_shell_delete_defaults_to_preview_and_does_not_consume_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = self._disposable_plan(tmp)
            session = mock.Mock()
            session.ready = True
            session.root = str(Path(tmp).resolve())
            session.active_plan = document
            output = io.StringIO()
            shell = SanchayShell(session=session, stdout=output)
            shell.permission.enable(actions.AUTHORIZATION_PHRASE)

            shell.onecmd('/delete 1')

            target = Path(document['recommendations'][0]['path'])
            self.assertTrue(target.exists())
            self.assertTrue(shell.permission.enabled)
            self.assertIn('PREVIEW only', output.getvalue())

    def test_executed_shell_action_revokes_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = self._disposable_plan(tmp)
            session = mock.Mock()
            session.ready = True
            session.root = str(Path(tmp).resolve())
            session.active_plan = document
            output = io.StringIO()
            shell = SanchayShell(session=session, stdout=output)
            shell.permission.enable(actions.AUTHORIZATION_PHRASE)

            shell.onecmd('/delete 1 --execute --confirm DELETE:1')

            self.assertFalse(shell.permission.enabled)
            self.assertIn('Deleted verified candidate', output.getvalue())


if __name__ == '__main__':
    unittest.main()
