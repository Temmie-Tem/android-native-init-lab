"""Hostile host-only tests for the fixed normal-reboot journal fixture."""

from __future__ import annotations

import ast
from copy import deepcopy
import errno
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import signal
import stat
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/device-action/coordinators/"
    "s22plus_fyg8_pref1_normal_reboot_journal_h0.py"
)
REPORT = (
    ROOT
    / "docs/reports/"
    "S22PLUS_FYG8_PREF1_NORMAL_REBOOT_JOURNAL_H0_2026-08-29.md"
)
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"
GOAL = ROOT / "GOAL.md"


def load_module(name: str = "s22plus_pref1_reboot_journal_tested"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S22PlusPreF1NormalRebootJournalH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def root(self) -> Path:
        temporary = tempfile.TemporaryDirectory(prefix="s22-pref1-journal-test-")
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name).resolve() / "campaign"

    def initialize(self) -> Path:
        root = self.root()
        self.module.Journal.create(root)
        return root

    def activation(self, journal) -> bytes:
        return self.module._fixture_activation(
            journal.coordinator, journal.descriptor_digest
        )

    @staticmethod
    def observed(journal, state, boot: str):
        return {
            "target": dict(journal.coordinator.TARGET),
            "topology_sha256": state["topology_sha256"],
            "boot_id_sha256": boot,
            "healthy_android": True,
        }

    def open_campaign(self, root: Path) -> None:
        with self.module.Journal(root) as journal:
            journal.record_open(self.activation(journal), now=100)

    def intent(self, root: Path) -> None:
        with self.module.Journal(root) as journal:
            state, _ = journal._tail()
            self.assertIsNotNone(state)
            journal.record_intent(
                self.observed(journal, state, state["boot_id_sha256"]),
                now=101,
            )

    def test_fixed_descriptor_binds_reviewed_v3_and_derives_class_and_mode(self):
        descriptor = self.module.fixed_descriptor()
        self.assertEqual(descriptor["class_id"], "normal_android_reboot_health")
        self.assertEqual(descriptor["tier"], "D1")
        self.assertEqual(descriptor["proof_mode"], "new_boot_health")
        self.assertEqual(descriptor["executor"]["ordinal"], "d1-fresh-baseline-3")
        self.assertEqual(
            descriptor["executor"]["review_verdict"], self.module.REVIEW_VERDICT
        )
        self.assertEqual(
            descriptor["executor"]["binding"]["sha256"],
            "dcb869aeeebf877d669da0a1f45b8c1d56a65777c13c9d518c0ad2dace93fc10",
        )
        encoded = self.module.canonical_bytes(descriptor)
        self.assertNotIn(b"DEVICE-ACTION-D1", encoded)
        self.assertEqual(descriptor["device_commands"], [])
        self.assertFalse(descriptor["live_integration"])

    def test_descriptor_source_or_binding_drift_fails_closed(self):
        for key in ("coordinator", "executor", "binding"):
            original = deepcopy(self.module.EXPECTED_FILES[key])
            self.module.EXPECTED_FILES[key]["sha256"] = "0" * 64
            try:
                with self.subTest(key=key), self.assertRaises(
                    self.module.JournalError
                ):
                    if key == "coordinator":
                        self.module.load_coordinator()
                    else:
                        self.module.fixed_descriptor()
            finally:
                self.module.EXPECTED_FILES[key] = original

    def test_self_test_reopens_four_times_and_creates_no_authority(self):
        result = self.module.self_test()
        self.assertEqual(result["journal_record_count"], 4)
        self.assertEqual(result["restart_reopens"], 4)
        self.assertEqual(result["final_phase"], "CLOSED")
        self.assertEqual(
            result["journal_kinds"],
            [
                "CAMPAIGN_OPEN",
                "EFFECT_INTENT",
                "EFFECT_HEALTHY_RETURN",
                "CAMPAIGN_CLOSE",
            ],
        )
        for key in (
            "coordinator_active",
            "activation_manifest_present",
            "device_action_integration",
            "live_executor_integration",
            "live_authority",
            "device_contact",
            "approval_created",
        ):
            self.assertIs(result[key], False)

    def test_restart_reconstruction_validates_modes_chain_and_activation(self):
        root = self.initialize()
        self.open_campaign(root)
        self.intent(root)
        returned_boot = hashlib.sha256(b"returned-boot").hexdigest()
        with self.module.Journal(root) as journal:
            state, _ = journal._tail()
            journal.record_healthy_return(
                self.observed(journal, state, returned_boot), now=102
            )
        with self.module.Journal(root) as journal:
            journal.record_close(now=103)
        reloaded = load_module("s22plus_pref1_reboot_journal_reloaded")
        with reloaded.Journal(root) as journal:
            history = journal.history()
            state, intent = journal._tail()
        self.assertEqual(len(history), 4)
        self.assertEqual(state["phase"], "CLOSED")
        self.assertIsNone(intent)
        previous = self.module.ZERO_HASH
        for sequence, item in enumerate(history):
            record = item["record"]
            path = root / "journal" / item["receipt"]["path"]
            info = path.stat()
            self.assertEqual(record["sequence"], sequence)
            self.assertEqual(record["previous_record_sha256"], previous)
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
            self.assertEqual(info.st_nlink, 1)
            previous = item["receipt"]["sha256"]

    def test_class_and_proof_mode_are_not_caller_parameters(self):
        parameters = inspect.signature(self.module.Journal.record_intent).parameters
        self.assertNotIn("class_id", parameters)
        self.assertNotIn("proof_mode", parameters)
        root = self.initialize()
        self.open_campaign(root)
        self.intent(root)
        with self.module.Journal(root) as journal:
            history = journal.history()
        intent = history[-1]["record"]["payload"]["intent"]
        self.assertEqual(intent["class_id"], self.module.CLASS_ID)
        self.assertEqual(intent["proof_mode"], self.module.PROOF_MODE)

    def test_same_boot_result_fails_before_publication(self):
        root = self.initialize()
        self.open_campaign(root)
        self.intent(root)
        with self.module.Journal(root) as journal:
            state, _ = journal._tail()
            before = len(journal.history())
            with self.assertRaisesRegex(
                journal.coordinator.CoordinatorModelError, "reused its source boot"
            ):
                journal.record_healthy_return(
                    self.observed(journal, state, state["boot_id_sha256"]), now=102
                )
            self.assertEqual(len(journal.history()), before)

    def test_uncertain_cut_is_terminal_consumed_without_replay(self):
        root = self.initialize()
        self.open_campaign(root)
        self.intent(root)
        with self.module.Journal(root) as journal:
            journal.record_uncertain(reason="result_uncertain", now=102)
        with self.module.Journal(root) as journal:
            history = journal.history()
            self.assertEqual(history[-1]["record"]["kind"], "EFFECT_UNCERTAIN_PARK")
            result = history[-1]["record"]["payload"]["result"]
            self.assertEqual(result["status"], "UNCERTAIN_CONSUMED_NO_REPLAY")
            state, intent = journal._tail()
            self.assertEqual(state["phase"], "PARKED")
            self.assertIsNotNone(intent)
            with self.assertRaises(self.module.JournalError):
                journal.record_intent(
                    self.observed(journal, state, state["boot_id_sha256"]), now=103
                )

    def test_activation_descriptor_mismatch_fails_before_first_record(self):
        root = self.initialize()
        with self.module.Journal(root) as journal:
            activation = json.loads(self.activation(journal))
            activation["effect_core_sha256"] = "0" * 64
            with self.assertRaisesRegex(self.module.JournalError, "did not open"):
                journal.record_open(
                    journal.coordinator.canonical_bytes(activation), now=100
                )
            self.assertEqual(journal.history(), [])

    def test_record_time_cannot_move_backwards(self):
        root = self.initialize()
        self.open_campaign(root)
        self.intent(root)
        with self.module.Journal(root) as journal:
            state, _ = journal._tail()
            boot = hashlib.sha256(b"new-boot").hexdigest()
            journal.record_healthy_return(
                self.observed(journal, state, boot), now=102
            )
            with self.assertRaisesRegex(self.module.JournalError, "chain differs"):
                journal.record_close(now=101)
            self.assertEqual(len(journal.history()), 3)

    def test_atomic_publication_failure_leaves_no_final_record(self):
        root = self.initialize()
        with self.module.Journal(root) as journal, mock.patch.object(
            self.module,
            "_link_tmpfile",
            side_effect=OSError(errno.EIO, "fixture link cut"),
        ):
            with self.assertRaisesRegex(
                self.module.JournalError, "atomic publication failed"
            ):
                journal.record_open(self.activation(journal), now=100)
            self.assertEqual(list((root / "journal").iterdir()), [])

    def test_existing_final_is_never_replaced(self):
        root = self.initialize()
        self.open_campaign(root)
        with self.module.Journal(root) as journal:
            first = journal.history()[0]
            path = root / "journal" / first["receipt"]["path"]
            before = path.read_bytes()
            with self.assertRaisesRegex(
                self.module.JournalError, "final already exists"
            ):
                self.module._atomic_publish(path, before)
            self.assertEqual(path.read_bytes(), before)

    def test_second_coordinator_cannot_take_the_lease(self):
        root = self.initialize()
        first = self.module.Journal(root)
        second = self.module.Journal(root)
        with first:
            with self.assertRaisesRegex(
                self.module.JournalError, "exclusive coordinator lease"
            ):
                second.__enter__()
            first.record_open(self.activation(first), now=100)
        with second:
            self.assertEqual(len(second.history()), 1)

    def test_extra_symlink_or_malformed_record_fails_closed(self):
        root = self.initialize()
        (root / "extra").write_text("unexpected", encoding="utf-8")
        with self.assertRaisesRegex(self.module.JournalError, "namespace differs"):
            with self.module.Journal(root):
                pass
        (root / "extra").unlink()
        (root / "journal" / "000000-campaign-open.json").symlink_to("/dev/null")
        with self.assertRaises(self.module.JournalError):
            with self.module.Journal(root):
                pass

    def test_validly_named_fifo_is_rejected_without_blocking(self):
        root = self.initialize()
        fifo = root / "journal" / "000000-campaign-open.json"
        os.mkfifo(fifo, 0o400)

        def timeout(_number, _frame):
            raise TimeoutError("FIFO open blocked")

        previous = signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, 0.5)
        try:
            with self.assertRaisesRegex(self.module.JournalError, "metadata differs"):
                with self.module.Journal(root):
                    pass
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous)

    def test_deleted_middle_record_and_tampered_mode_fail_closed(self):
        root = self.initialize()
        self.open_campaign(root)
        self.intent(root)
        with self.module.Journal(root) as journal:
            state, _ = journal._tail()
            boot = hashlib.sha256(b"different-boot").hexdigest()
            journal.record_healthy_return(
                self.observed(journal, state, boot), now=102
            )
            names = [item["receipt"]["path"] for item in journal.history()]
        middle = root / "journal" / names[1]
        middle.unlink()
        with self.assertRaisesRegex(self.module.JournalError, "filename sequence"):
            with self.module.Journal(root):
                pass

        other = self.initialize()
        self.open_campaign(other)
        only = next((other / "journal").iterdir())
        only.chmod(0o600)
        with self.assertRaisesRegex(self.module.JournalError, "metadata differs"):
            with self.module.Journal(other):
                pass

    def test_strict_json_rejects_duplicate_noncanonical_bool_and_nonfinite(self):
        for raw in (
            b'{"x":1,"x":2}\n',
            b'{"x": 1}\n',
            b'{"x":NaN}\n',
        ):
            with self.subTest(raw=raw), self.assertRaises(self.module.JournalError):
                self.module.strict_json(raw, "fixture")
        root = self.initialize()
        with self.module.Journal(root) as journal:
            with self.assertRaises(self.module.JournalError):
                journal._append("CAMPAIGN_OPEN", {"state": {}}, now=True)
            self.assertEqual(journal.history(), [])

    def test_cli_and_source_have_no_live_or_device_execution_surface(self):
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertNotIn("subprocess", imports)
        for token in ("adb shell", "odin4", "fastboot"):
            self.assertNotIn(token, source)
        for argv in ([], ["--live"], ["--self-test", "--approval", "x"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                self.module.main(argv)

    def test_report_goal_and_ledger_keep_the_unit_review_pending_and_dormant(self):
        report = REPORT.read_text(encoding="utf-8")
        for token in (
            "INDEPENDENTLY REVIEWED / PASS_GO / NOT ACTIVE",
            "70b1157013",
            "61543c98b7",
            "8bfc6b6dab",
            "d1-fresh-baseline-3",
            "normal_android_reboot_health",
            "new_boot_health",
            "O_TMPFILE",
            "FRESH_BASELINE_MISSING",
            "activation-file loader",
            "no approval was created",
            "there was no device",
        ):
            self.assertIn(token, report)
        ledger = LEDGER.read_text(encoding="utf-8")
        ordinal = "h0-pref1-normal-reboot-journal-1"
        rows = [line for line in ledger.splitlines() if f" | {ordinal} | " in line]
        self.assertEqual(len(rows), 1)
        self.assertIn(
            "S22PLUS_FYG8_PREF1_NORMAL_REBOOT_JOURNAL_IMPLEMENTED_REVIEW_PENDING",
            rows[0],
        )
        self.assertNotIn("PASS_GO", rows[0])
        repair_ordinal = "h0-pref1-normal-reboot-journal-review-repair-1"
        repair_rows = [
            line
            for line in ledger.splitlines()
            if f" | {repair_ordinal} | " in line
        ]
        self.assertEqual(len(repair_rows), 1)
        self.assertIn(
            "PREF1_NORMAL_REBOOT_JOURNAL_FIFO_BOUND_REPAIR_UNDER_EXISTING_OBLIGATION",
            repair_rows[0],
        )
        self.assertNotIn("PASS_GO", repair_rows[0])
        self.assertNotIn("REVIEW_PENDING", repair_rows[0])
        review_ordinal = "h0-pref1-normal-reboot-journal-review-1"
        review_rows = [
            line
            for line in ledger.splitlines()
            if f" | {review_ordinal} | " in line
        ]
        self.assertEqual(len(review_rows), 1)
        self.assertIn(
            "PASS_GO_S22PLUS_FYG8_PREF1_NORMAL_REBOOT_JOURNAL_H0_CAPABILITY_V1",
            review_rows[0],
        )
        goal = GOAL.read_text(encoding="utf-8")
        self.assertEqual(len(goal.splitlines()), 900)
        self.assertIn(
            "fixed normal-reboot descriptor journal are independently reviewed H0-only "
            "`PASS_GO`",
            goal,
        )


if __name__ == "__main__":
    unittest.main()
