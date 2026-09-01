"""Regression tests for the shared closed-result publisher.

These cover the invariants that four run-specific finalizers had to satisfy
separately, and that drifted between copies: P3.23 kept the repairing journal
reopen that P3.24's review removed, because each finalizer was its own file.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import stat
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
PUBLISHER = REVALIDATION / "closed_result_publisher.py"
P326_FINALIZER = REVALIDATION / "s22plus_fyg8_p326_closed_result_finalizer.py"
LIVE_SOURCES = (
    REVALIDATION / "device_action_f1_v2.py",
    REVALIDATION / "device_action_f1_live_v2.py",
    REVALIDATION / "device_action_f1_evidence_v2.py",
)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    # Registration is required before exec so dataclass field resolution can
    # find the defining module.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def p326_spec(publisher, finalizer):
    def lane_shim(live):
        original = live._p324_typec_lane_value  # noqa: SLF001

        def stored(prepared, **_kwargs):
            return original(prepared, revalidate=False)

        live._p324_typec_lane_value = stored  # noqa: SLF001

        def restore():
            live._p324_typec_lane_value = original  # noqa: SLF001

        return restore

    return publisher.ClosedResultSpec(
        label="P3.26",
        schema=finalizer.SCHEMA,
        root=finalizer.ROOT,
        manifest=finalizer.MANIFEST,
        run_dir=finalizer.RUN_DIR,
        binding_sha256=finalizer.EXPECTED_BINDING,
        bundle_sha256=finalizer.EXPECTED_BUNDLE,
        journal=publisher.JournalShape(
            records=19,
            terminal_sequence=18,
            terminal_sha256=finalizer.EXPECTED_TERMINAL_RECORD_SHA256,
        ),
        state=publisher.Artifact(
            finalizer.EXPECTED_STATE_SIZE, finalizer.EXPECTED_STATE_SHA256
        ),
        result=publisher.Artifact(
            finalizer.EXPECTED_RESULT_SIZE, finalizer.EXPECTED_RESULT_SHA256
        ),
        verdict=finalizer.EXPECTED_RESULT_VERDICT,
        outcome=finalizer.EXPECTED_OUTCOME,
        audit_verdict=finalizer.AUDIT_VERDICT,
        exact_files=finalizer.EXACT_FILES,
        state_expectations={
            "candidate_classification": "odin_transfer_completed",
            "candidate_completed": True,
            "candidate_observer_classification": "accepted",
            "candidate_observer_accepted": True,
            "candidate_observer_guard_release_status": "released",
            "candidate_observer_guard_released": True,
            "download_endpoint_absent": True,
            "rollback_classification": "odin_transfer_completed",
            "rollback_completed": True,
            "final_verified": True,
            "p326_proof_class": "NO_PROOF_OBSERVER",
        },
        projection=publisher.ProjectionSpec(
            method="_candidate_arrival_proof_projection",
            expected={
                "proof": True,
                "banner_size": 145,
                "pid1_bidirectional_proof": True,
                "busybox_shell_roundtrip_proof": True,
                "supplemental_carrier": None,
            },
            state_key="candidate_arrival_proof",
        ),
        lane_shim=lane_shim,
    )


class PublisherSourceTest(unittest.TestCase):
    """Checks that need no run evidence and touch nothing."""

    @classmethod
    def setUpClass(cls):
        cls.source = PUBLISHER.read_text()
        cls.tree = ast.parse(cls.source)

    def test_live_runtime_never_imports_the_publisher(self):
        # The 64 KiB path must be unreachable from the live path.  A one-way
        # dependency is what keeps this a lifecycle-scoped bound rather than a
        # wider record bound.
        for path in LIVE_SOURCES:
            self.assertNotIn(
                "closed_result_publisher",
                path.read_text(),
                f"{path.name} must not reach the closed-result publisher",
            )

    def test_publisher_imports_no_device_capable_module(self):
        # Checked against imports rather than raw text: the report keys name
        # adb and odin precisely in order to declare them false.
        imported = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        for forbidden in ("subprocess", "socket", "shutil", "ctypes", "fcntl", "termios"):
            self.assertNotIn(forbidden, imported)
        # The two runtime imports are deliberate and are pinned by digest
        # before they happen.
        self.assertTrue(imported.issuperset({"os", "json", "hashlib"}))

    def test_publisher_calls_no_process_or_device_entry(self):
        called = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                target = node.func
                if isinstance(target, ast.Attribute):
                    called.add(target.attr)
                elif isinstance(target, ast.Name):
                    called.add(target.id)
        for forbidden in ("system", "popen", "run", "spawn", "execv", "fork", "kill"):
            self.assertNotIn(forbidden, called, f"publisher must not call {forbidden}")

    def test_bounds_are_separate_constants(self):
        publisher = load("publisher_bounds", PUBLISHER)
        self.assertEqual(publisher.CORE_MAX_RECORD, 32 * 1024)
        self.assertEqual(publisher.MAX_CLOSED_RESULT, 64 * 1024)
        self.assertNotEqual(publisher.CORE_MAX_RECORD, publisher.MAX_CLOSED_RESULT)

    def test_read_only_journal_does_not_use_reopen(self):
        # P3.24's review found the repairing reopen rewrote identical
        # journal-head bytes and moved inode and timestamps.  P3.23 still has
        # that defect because it is a separate copy; this is the shared fix.
        function = next(
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef) and node.name == "read_only_journal"
        )
        attributes = {
            node.attr for node in ast.walk(function) if isinstance(node, ast.Attribute)
        }
        self.assertNotIn("reopen", attributes)
        self.assertIn("records", attributes)

    def test_reopen_is_replaced_and_restored_around_validation(self):
        function = next(
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_read_only_journals"
        )
        body = ast.dump(function)
        self.assertIn("Try", body, "reopen replacement must restore in a finally block")
        self.assertIn("reopen", body)


class PublisherBehaviourTest(unittest.TestCase):
    """Read-only checks against the exact P3.26 closed run."""

    @classmethod
    def setUpClass(cls):
        cls.publisher = load("publisher_behaviour", PUBLISHER)
        cls.finalizer = load("p326_behaviour", P326_FINALIZER)
        cls.spec = p326_spec(cls.publisher, cls.finalizer)

    def test_reproduces_the_published_p326_result_byte_for_byte(self):
        _value, payload, *_rest = self.publisher.reconstruct(self.spec)
        self.assertEqual(len(payload), self.finalizer.EXPECTED_RESULT_SIZE)
        self.assertEqual(
            self.publisher.sha256(payload), self.finalizer.EXPECTED_RESULT_SHA256
        )

    def test_matches_the_run_specific_finalizer_exactly(self):
        _own_value, own_payload, *_ = self.finalizer.reconstruct()
        _new_value, new_payload, *_ = self.publisher.reconstruct(self.spec)
        self.assertEqual(own_payload, new_payload)

    def test_audit_only_publishes_nothing_and_leaves_the_result_untouched(self):
        target = self.spec.result_path
        before = os.stat(target)
        report = self.publisher.finalize(self.spec, audit_only=True)
        after = os.stat(target)
        self.assertFalse(report["created"])
        self.assertTrue(report["already_present"])
        self.assertEqual(report["verdict"], self.finalizer.AUDIT_VERDICT)
        self.assertEqual(
            (before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode),
            (after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode),
        )
        self.assertEqual(stat.S_IMODE(after.st_mode), 0o400)
        self.assertEqual(after.st_nlink, 1)

    def test_report_declares_no_device_action(self):
        report = self.publisher.finalize(self.spec, audit_only=True)
        for flag in (
            "device_contact",
            "adb_invoked",
            "usb_revalidated",
            "odin_invoked",
            "candidate_transfer",
            "rollback_transfer",
            "live_authorized",
        ):
            self.assertFalse(report[flag], flag)

    def test_source_drift_stops_fail_closed(self):
        # This is the P3.25 situation: P3.26 changed the shared runners and the
        # earlier pins no longer match, so re-audit must stop rather than audit
        # against different code.
        drifted = dict(self.spec.exact_files)
        path, size, _digest = drifted["live_source"]
        drifted["live_source"] = (path, size, "0" * 64)
        spec = self.publisher.ClosedResultSpec(
            **{
                **{f.name: getattr(self.spec, f.name) for f in self.spec.__dataclass_fields__.values()},
                "exact_files": drifted,
            }
        )
        with self.assertRaises(self.publisher.PublicationError) as caught:
            self.publisher.reconstruct(spec)
        self.assertIn("identity differs", str(caught.exception))

    def test_a_result_that_fits_the_live_bound_is_refused(self):
        # The 64 KiB path exists because 32 KiB was not enough.  If a run's
        # result would have fit, this path must not be usable for it.
        undersized = self.publisher.ClosedResultSpec(
            **{
                **{f.name: getattr(self.spec, f.name) for f in self.spec.__dataclass_fields__.values()},
                "result": self.publisher.Artifact(1024, "0" * 64),
            }
        )
        with self.assertRaises(self.publisher.PublicationError):
            self.publisher.reconstruct(undersized)


if __name__ == "__main__":
    unittest.main()
