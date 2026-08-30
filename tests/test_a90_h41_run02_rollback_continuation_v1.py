"""Host-only tests for the exact H41 run-02 rollback continuation."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "workspace/public/src/scripts/server-distro/a90_h41_run02_rollback_continuation_v1.py"


def load():
    spec = importlib.util.spec_from_file_location("a90_h41_run02_rollback_continuation_v1_tested", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class H41Run02RollbackContinuationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = load()

    def test_exact_incident_binding(self):
        self.assertEqual(self.R.RUN_ID, "a90-h41-f1-20260830-02")
        self.assertEqual(
            self.R.ORIGINAL_ROLLBACK_INTENT_SHA256,
            "852f2ad6eb9cdaf6f7c9fc7e1396d5286276bd18a3d47106bc1b2ee57b953953",
        )
        self.assertEqual(
            tuple(self.R.ORIGINAL_RECORD_HASHES),
            (
                "00-transaction-intent.json", "10-late-recovery-ready.json",
                "20-candidate-intent.json", "21-candidate-launched.json",
                "22-candidate-result.json", "23-demo-window.json",
                "30-rollback-intent.json", "31-rollback-launched.json",
            ),
        )
        self.assertEqual(
            set(self.R.ORIGINAL_ROLLBACK_LOG_HASHES),
            {"001-effect-usb-inventory.stdout", "001-effect-usb-inventory.stderr"},
        )
        self.assertNotIn("flash-rollback.stdout", self.R.ORIGINAL_ROLLBACK_LOG_HASHES)

    def test_original_private_evidence_is_exact(self):
        if not self.R.ORIGINAL_SIDE_ROOT.is_dir():
            self.skipTest("private H41 evidence is absent")
        manifest = self.R._fixed_incident_evidence()
        self.assertEqual(manifest["rollback"]["sha256"], self.R.ROLLBACK_SHA256)

    def test_empty_stderr_reader_is_strict_but_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "stderr"
            path.write_bytes(b"")
            path.chmod(0o600)
            self.assertEqual(self.R._read_log(path), b"")
            path.chmod(0o644)
            with self.assertRaisesRegex(self.R.RecoveryError, "identity changed"):
                self.R._read_log(path)

    def test_approval_binds_both_phases_and_current_closure(self):
        token = self.R._approval("a" * 64, "b" * 64)
        self.assertTrue(token.startswith(self.R.APPROVAL_PREFIX))
        with mock.patch.object(self.R.owner, "canonical_json", wraps=self.R.owner.canonical_json) as canonical:
            self.R._approval("a" * 64, "b" * 64)
        payload = canonical.call_args.args[0]
        self.assertEqual(payload["phases"], ["one-v2321-rollback", "one-post-menu-close-health"])
        self.assertEqual(payload["originalRollbackIntentSha256"], self.R.ORIGINAL_ROLLBACK_INTENT_SHA256)

    def test_closure_detects_each_execution_input(self):
        original = Path.read_bytes
        current = self.R.execution_closure_sha256()
        for target in self.R.CLOSURE_PATHS:
            with self.subTest(target=target):
                def altered(path: Path, target=target):
                    raw = original(path)
                    return b"X" + raw[1:] if path == target else raw
                with mock.patch.object(Path, "read_bytes", new=altered):
                    self.assertNotEqual(self.R.execution_closure_sha256(), current)

    def test_publication_is_no_replace_and_canonical(self):
        with tempfile.TemporaryDirectory() as temporary:
            old = self.R.CONT_DIR
            self.R.CONT_DIR = Path(temporary)
            try:
                digest = self.R._publish("00.json", {"attempt": 1})
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
                self.assertEqual(self.R._continuation_record("00.json"), {"attempt": 1})
                with self.assertRaises(self.R.RecoveryError):
                    self.R._publish("00.json", {"attempt": 1})
            finally:
                self.R.CONT_DIR = old

    def test_prepare_rejects_any_consumed_surface(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = (self.R.CONT_DIR, self.R.ROLLBACK_LOG_DIR, self.R.HEALTH_LOG_DIR)
            try:
                for index, attribute in enumerate(("CONT_DIR", "ROLLBACK_LOG_DIR", "HEALTH_LOG_DIR")):
                    setattr(self.R, attribute, root / str(index))
                with mock.patch.object(self.R, "_original_context", return_value=({}, "a" * 64, "b" * 64)):
                    self.assertTrue(self.R.prepare().startswith(self.R.APPROVAL_PREFIX))
                    self.R.ROLLBACK_LOG_DIR.mkdir()
                    with self.assertRaisesRegex(self.R.RecoveryError, "already consumed"):
                        self.R.prepare()
            finally:
                self.R.CONT_DIR, self.R.ROLLBACK_LOG_DIR, self.R.HEALTH_LOG_DIR = old

    def test_execute_requires_native_role_before_intent(self):
        source = MODULE.read_text()
        inventory = source.index("fixed._effect_inventory(rollback=True)")
        role_check = source.index("role != adapter.ADB_ROLE_NATIVE", inventory)
        publish = source.index('_publish("00-continuation-intent.json"', role_check)
        flash = source.index("effect = fixed.flash(", publish)
        result = source.index('_publish("10-rollback-result.json"', flash)
        self.assertLess(inventory, role_check)
        self.assertLess(role_check, publish)
        self.assertLess(publish, flash)
        self.assertLess(flash, result)

    def test_no_candidate_or_unbound_flash_path(self):
        source = MODULE.read_text()
        start = source.index("def execute(")
        body = source[start:source.index("def finalize(", start)]
        self.assertNotIn("flash-candidate", body)
        self.assertNotIn("manifest[\"candidate\"]", body)
        self.assertNotIn("rollback=False", body)
        self.assertIn("owner_usb_inventory_sha256=usb_digest", body)
        self.assertIn("owner_adb_role=role", body)

    def test_finalize_has_durable_health_intent_and_no_effect(self):
        source = MODULE.read_text()
        start = source.index("def finalize(")
        body = source[start:source.index("def main(", start)]
        self.assertLess(
            body.index('_publish("15-health-intent.json"'),
            body.index("snapshot = fixed.observe("),
        )
        self.assertNotIn("fixed.flash(", body)
        self.assertNotIn("native_init_flash", body)

    def test_finalize_rejects_missing_physical_confirmation_before_context(self):
        token = self.R.APPROVAL_PREFIX + "a" * 64
        for attended, closed in ((False, False), (True, False), (False, True)):
            with self.subTest(attended=attended, closed=closed):
                with mock.patch.object(self.R, "_original_context") as context:
                    with mock.patch.object(self.R, "_resume_final") as resume:
                        with self.assertRaisesRegex(self.R.RecoveryError, "closed-menu"):
                            self.R.finalize(
                                token,
                                operator_attended=attended,
                                menu_closed_confirmed=closed,
                            )
                    context.assert_not_called()
                    resume.assert_not_called()

    def test_final_resume_precedes_new_health_context_or_contact(self):
        source = MODULE.read_text()
        start = source.index("def finalize(")
        body = source[start:source.index("def main(", start)]
        self.assertLess(body.index("_resume_final(approval)"), body.index("manifest, review_sha"))
        resume_start = source.index("def _resume_final(")
        resume_body = source[resume_start:source.index("def prepare(", resume_start)]
        self.assertNotIn("HostRunner", resume_body)
        self.assertNotIn("fixed.observe", resume_body)
        self.assertNotIn("fixed.flash", resume_body)

    def test_final_validator_rejects_extra_keys_and_boolean_counters(self):
        approval = self.R.APPROVAL_PREFIX + "a" * 64
        review_sha, closure = "b" * 64, "c" * 64
        intent = {
            "approvalSha256": self.R._sha(approval.encode("ascii")),
            "reviewSha256": review_sha,
            "executionClosureSha256": closure,
            "originalRollbackIntentSha256": self.R.ORIGINAL_ROLLBACK_INTENT_SHA256,
            "rollbackSha256": self.R.ROLLBACK_SHA256,
            "ownerUsbInventorySha256": "d" * 64,
            "ownerAdbRole": self.R.adapter.ADB_ROLE_NATIVE,
            "continuationWriteCount": 1,
            "candidateReplay": False,
            "originalRollbackReplay": False,
        }
        effect_payload = {
            "returncode": 0, "completed": True, "quiescent": True,
            "receiptSha256": "e" * 64,
            "outcome": "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
        }
        effect = SimpleNamespace(
            receipt_sha256="e" * 64,
            payload=lambda: effect_payload,
        )
        health = {
            "approvalSha256": self.R._sha(approval.encode("ascii")),
            "reviewSha256": review_sha,
            "executionClosureSha256": closure,
            "rollbackReceiptSha256": "e" * 64,
            "healthObservationCount": 1,
            "operatorAttended": True,
            "menuClosedConfirmed": True,
            "candidateReplay": False,
            "rollbackReplay": False,
        }
        final = {
            "decision": "V2321_HEALTHY_H41_RUN02_RECOVERED",
            "candidateReplay": False,
            "originalRollbackReplay": False,
            "continuationRollbackReplay": False,
            "incidentContinuationWriteCount": 1,
            "rollbackResult": effect_payload,
            "snapshot": {},
            "rollbackLogHashes": {"001-x.stdout": "f" * 64},
            "healthLogHashes": {"001-y.stdout": "0" * 64},
        }
        manifest = {"qualification": {"review": {"sha256": "1" * 64}}, "rollback": {}}
        with tempfile.TemporaryDirectory() as temporary:
            old = self.R.CONT_DIR
            self.R.CONT_DIR = Path(temporary)
            self.R.CONT_DIR.chmod(0o700)
            for name in (
                "00-continuation-intent.json", "10-rollback-result.json",
                "15-health-intent.json", "20-final.json",
            ):
                (self.R.CONT_DIR / name).write_bytes(b"x")
            records = {
                "00-continuation-intent.json": intent,
                "15-health-intent.json": health,
                "20-final.json": final,
            }
            try:
                patches = (
                    mock.patch.object(self.R, "_continuation_record", side_effect=lambda name: records[name]),
                    mock.patch.object(self.R, "_effect_result", return_value=effect),
                    mock.patch.object(
                        self.R, "_current_log_hashes",
                        side_effect=(final["rollbackLogHashes"], final["healthLogHashes"]),
                    ),
                    mock.patch.object(self.R, "_snapshot_from_payload", return_value=object()),
                    mock.patch.object(self.R, "_healthy_snapshot", return_value=True),
                )
                for mutation in ("extra", "intent-bool", "health-bool", "final-bool"):
                    with self.subTest(mutation=mutation):
                        changed_intent = dict(intent)
                        changed_health = dict(health)
                        changed_final = dict(final)
                        if mutation == "extra":
                            changed_intent["extra"] = False
                        elif mutation == "intent-bool":
                            changed_intent["continuationWriteCount"] = True
                        elif mutation == "health-bool":
                            changed_health["healthObservationCount"] = True
                        else:
                            changed_final["incidentContinuationWriteCount"] = True
                        records.update({
                            "00-continuation-intent.json": changed_intent,
                            "15-health-intent.json": changed_health,
                            "20-final.json": changed_final,
                        })
                        with patches[0], patches[1], patches[2], patches[3], patches[4]:
                            with self.assertRaises(self.R.RecoveryError):
                                self.R._validate_final_prefix(
                                    manifest, approval, review_sha, closure
                                )
            finally:
                self.R.CONT_DIR = old

    def test_final_resume_revalidates_lease_before_release(self):
        approval = self.R.APPROVAL_PREFIX + "a" * 64
        manifest = {}
        with mock.patch.object(
            self.R, "_original_context",
            side_effect=((manifest, "b" * 64, "c" * 64), (manifest, "d" * 64, "c" * 64)),
        ) as context:
            with mock.patch.object(self.R, "_approval", return_value=approval):
                with mock.patch.object(self.R, "_validate_final_prefix", return_value={}):
                    with mock.patch.object(self.R.owner, "_release_active_guard") as release:
                        with self.assertRaisesRegex(self.R.RecoveryError, "lease changed"):
                            self.R._resume_final(approval)
        self.assertEqual(context.call_count, 2)
        release.assert_not_called()

    def test_effect_result_rejects_shape_drift(self):
        with mock.patch.object(self.R, "_continuation_record", return_value={"completed": True}):
            with self.assertRaisesRegex(self.R.RecoveryError, "shape changed"):
                self.R._effect_result()


if __name__ == "__main__":
    unittest.main()
