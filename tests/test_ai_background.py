import io
from concurrent.futures import CancelledError
import os
from pathlib import Path
import threading
import tempfile
import unittest
from unittest import mock

from sanchay import intelligence, paths, plan, scan
from sanchay.palette import background_status_toolbar
from sanchay.shell import SanchayShell
from prompt_toolkit.formatted_text import fragment_list_to_text


class TestLearnedRecommendations(unittest.TestCase):
    NOW = 2_000_000_000

    @staticmethod
    def info(path, *, age_days, atime_days=None, inode=1):
        mtime = TestLearnedRecommendations.NOW - age_days * 86400
        atime = mtime if atime_days is None else (
            TestLearnedRecommendations.NOW - atime_days * 86400)
        return scan.FileInfo(
            path, 100 * 1024 * 1024, atime, mtime, inode,
            allocated_size=100 * 1024 * 1024,
        )

    def test_model_is_local_learned_and_discloses_bootstrap_boundary(self):
        card = intelligence.model_card()

        self.assertTrue(card["learned_inference"])
        self.assertEqual(card["type"], "multiclass_logistic_regression")
        self.assertGreater(card["training"]["examples"], 30)
        self.assertIn("not a production accuracy", card["training"]["validation_boundary"])
        self.assertFalse(card["privacy"]["file_contents_used"])
        self.assertFalse(card["privacy"]["personal_attributes_used"])
        self.assertFalse(card["privacy"]["network_required"])
        self.assertFalse(
            card["responsible_use"]["protected_or_owner_attributes_used"])
        self.assertIn("abstain to keep", card["responsible_use"]["uncertainty_policy"])

    def test_positive_recent_use_changes_an_old_unique_file_from_archive_to_keep(self):
        cold = self.info("/data/thesis.pdf", age_days=400, inode=1)
        recently_used = self.info(
            "/data/thesis.pdf", age_days=400, atime_days=2, inode=2)

        cold_result = intelligence.assess(cold, "unique", self.NOW)
        used_result = intelligence.assess(recently_used, "unique", self.NOW)

        self.assertEqual(cold_result["recommended_action"], "archive_review")
        self.assertEqual(used_result["recommended_action"], "keep")
        self.assertGreater(
            used_result["probabilities"]["keep"],
            cold_result["probabilities"]["keep"],
        )
        self.assertEqual(
            cold_result["usage_assessment"]["state"],
            "potentially_cold_review",
        )
        self.assertEqual(
            used_result["usage_assessment"]["state"],
            "active_or_uncertain",
        )

    def test_unique_files_can_be_archived_but_never_enter_cleanup(self):
        unique = self.info("/data/thesis.pdf", age_days=400)
        document = plan.build([unique], [], "/data", now=self.NOW)

        self.assertEqual(document["recommendations"], [])
        self.assertEqual(len(document["archive_recommendations"]), 1)
        archive = document["archive_recommendations"][0]
        self.assertFalse(archive["cleanup_eligible"])
        self.assertTrue(archive["destination"]["operator_selection_required"])
        self.assertFalse(archive["destination"]["durability_inferred"])

    def test_plan_verification_rechecks_archive_candidate_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document_path = root / "old-report.pdf"
            document_path.write_bytes(b"important")
            old = self.NOW - 400 * 86400
            os.utime(document_path, (old, old))
            files = scan.scan(root)
            review = plan.build(files, [], root, now=self.NOW)

            self.assertEqual(len(review["archive_recommendations"]), 1)
            self.assertTrue(plan.verify(review)["valid"])
            document_path.write_bytes(b"changed")
            verified = plan.verify(review)

        self.assertFalse(verified["valid"])
        self.assertTrue(any(
            "archive candidate" in reason
            for reason in verified["archive_recommendations"][0]["reasons"]
        ))

    def test_wsl_windows_drive_paths_translate_or_report_missing_mount(self):
        with mock.patch.object(paths, "_running_under_wsl", return_value=True), \
                mock.patch.object(Path, "is_dir", return_value=True):
            self.assertEqual(paths.scan_target("E:"), "/mnt/e")
            self.assertEqual(
                paths.scan_target(r"E:\folder\file"),
                "/mnt/e/folder/file",
            )

        with mock.patch.object(paths, "_running_under_wsl", return_value=True), \
                mock.patch.object(Path, "is_dir", return_value=False):
            with self.assertRaisesRegex(ValueError, "not mounted at /mnt/e"):
                paths.scan_target("E:/")


class _BlockingSession:
    def __init__(self):
        self.ready = False
        self.stale = False
        self.root = None
        self.cross_filesystems = False
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = []

    def scan(self, root, cross_filesystems=False, cancel_event=None,
             advisor_config=None):
        self.calls.append(root)
        self.started.set()
        while not self.release.wait(0.01):
            if cancel_event is not None and cancel_event.is_set():
                raise CancelledError
        if cancel_event is not None and cancel_event.is_set():
            raise CancelledError
        self.root = root
        self.ready = True
        return {
            "root": root,
            "file_entries": 0,
            "allocated_bytes": 0,
            "duplicate_groups": 0,
            "duplicate_reclaimable_bytes": 0,
            "candidate_count": 0,
            "archive_candidate_count": 0,
            "protected_unique_files": 0,
            "coverage": {"complete": True},
        }


class TestBackgroundInteractiveWork(unittest.TestCase):
    def _start(self):
        session = _BlockingSession()
        output = io.StringIO()
        shell = SanchayShell(session=session, stdout=output)
        shell.background_work_enabled = True
        shell.onecmd('/scan "scan target"')
        self.assertTrue(session.started.wait(1))
        task = shell.background_tasks.latest_cancellable()
        self.assertIsNotNone(task)
        return shell, session, output, task

    def test_scan_returns_prompt_control_and_publishes_only_after_success(self):
        shell, original, output, task = self._start()

        self.assertIs(shell.session, original)
        self.assertIn("/ps to view", shell.background_tasks.status_line())
        self.assertIn("Esc to interrupt", shell.background_tasks.status_line())
        toolbar = background_status_toolbar(shell, tick=0)
        rendered = fragment_list_to_text(toolbar)
        self.assertIn("⠋ Working (", rendered)
        self.assertIn("Esc to interrupt", rendered)
        self.assertIn("/ps to view", rendered)
        self.assertIn("class:bottom-toolbar.spinner", {
            style for style, _ in toolbar
        })
        # The highlight sweeps the word, so a later frame styles it differently.
        self.assertNotEqual(
            [style for style, _ in toolbar],
            [style for style, _ in background_status_toolbar(shell, tick=4)])
        original.release.set()
        task.alive_callback.__self__.thread.join(2)

        self.assertIsNot(shell.session, original)
        self.assertEqual(shell.session.root, "scan target")
        self.assertIn("Background task 1 complete", output.getvalue())
        self.assertEqual(shell.background_tasks.status_line(), "")

    def test_toolbar_changes_to_cancelling_and_removes_escape_hint(self):
        shell, original, _output, task = self._start()

        self.assertTrue(shell.cancel_latest_background())
        rendered = fragment_list_to_text(background_status_toolbar(shell))

        self.assertIn("Cancelling", rendered)
        self.assertNotIn("Esc to interrupt", rendered)
        original.release.set()
        task.alive_callback.__self__.thread.join(2)

    def test_cancel_preserves_previous_session_and_a_second_scan_is_refused(self):
        shell, original, output, task = self._start()
        shell.onecmd('/scan "second target"')

        self.assertEqual(original.calls, ["scan target"])
        self.assertTrue(shell.cancel_latest_background())
        task.alive_callback.__self__.thread.join(2)

        self.assertIs(shell.session, original)
        self.assertIn("already running", output.getvalue())
        self.assertIn("No partial scan will be published", output.getvalue())
        self.assertEqual(shell.background_tasks.status_line(), "")


if __name__ == "__main__":
    unittest.main()
