"""Offline tests for the stock-kernel handoff control."""

from contextlib import ExitStack
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
HERE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/stock-direct"
AVAILABLE = (
    ROOT
    / "workspace/private/analysis/s20plus-y2q-stock-direct-20261126/packaged3/pair.json"
).is_file()
if AVAILABLE:
    import s20plus_g986n_stock_direct_f1 as m


class Capsule(unittest.TestCase):
    def test_status_tag_uses_single_byte_and_static_original_source(self):
        self.assertIn(
            'STOCK_CONTROL_NONCE ":U"', (HERE / "stock-control-fdt.h").read_text()
        )
        self.assertIn(
            "e6dcf2a313c5e36429cac9f009141c240a6e30e9",
            (HERE / "build_control.py").read_text(),
        )
        patch_text = (HERE / "handoff.patch").read_text()
        self.assertIn("strb w11,[x26]", patch_text)
        self.assertNotIn("diff --git a/early-pair.S.inc", patch_text)


@unittest.skipUnless(AVAILABLE, "retained private AP and reader required")
class StockDirect(unittest.TestCase):
    def test_reader_normal_and_foreign_tags(self):
        nonce = "ae" * 16
        code = m.tag_script(nonce, "c" * 64)
        start = code.index("prop=/sys/")
        with tempfile.TemporaryDirectory() as tmp:
            chosen = Path(tmp)
            prop = chosen / "property"
            body = "set -eu\nset -o pipefail\nsame_boot() { return 0; }\n" + code[
                start:
            ].replace(m.PROP, str(prop))
            for app in ("od", "head", "tr", "printf"):
                body = body.replace("/system/bin/" + app, app)
            for raw, want in (
                (None, "ABSENT"),
                ((nonce + ":U").encode() + b"\0", "U"),
                ((nonce + ":C").encode() + b"\0", "C"),
                ((nonce + ":C").encode(), "FOREIGN"),
                ((nonce + ":C").encode() + b"\0extra", "FOREIGN"),
                (b"other\0", "FOREIGN"),
            ):
                if raw is not None:
                    prop.write_bytes(raw)
                result = subprocess.run(
                    ["/bin/bash", "-c", body], capture_output=True, check=True
                )
                self.assertFalse(result.stderr)
                self.assertEqual(m.tag_parse(result.stdout), want)
            prop.unlink()
            prop.symlink_to(chosen / "absent")
            self.assertNotEqual(
                subprocess.run(
                    ["/bin/bash", "-c", body], capture_output=True
                ).returncode,
                0,
            )
        with self.assertRaises(ValueError):
            m.tag_parse(b"Y2Q_TAG_C\n\n")

    def test_composite_claim(self):
        single = dict(state="prebranch_only", prebranch_count=1, primary_entry_count=0)
        self.assertTrue(m.classify({"state": "C"}, single))
        for tag in ("U", "ABSENT", "FOREIGN", "capture_gap", "read_failed"):
            self.assertFalse(m.classify({"state": tag}, single))
        for scan in (
            {"state": "capture_gap"},
            dict(single, primary_entry_count=1),
            dict(single, prebranch_count=2),
            dict(single, state="no_record"),
        ):
            self.assertFalse(m.classify({"state": "C"}, scan))

    def test_payloads_and_physical_source(self):
        pair = m.pair()
        for role, pin in [("candidate", m.CANDIDATE), ("rollback", m.base.ORIGINAL)]:
            self.assertEqual(
                hashlib.sha256(Path(pair[role]["ap"]["path"]).read_bytes()).hexdigest(),
                pin,
            )
        self.assertEqual(set(m.calibrated_identity()), set(m.stage.IDENTITY))

    def test_candidate_tag_required_even_after_health(self):
        with ExitStack() as scope:
            scope.enter_context(patch.object(m.owner, "transfer_receipt"))
            scope.enter_context(patch.object(m.owner, "engine", Mock(), create=True))
            h = {"boot_id_sha256": "a" * 64}
            scope.enter_context(
                patch.object(m.owner, "candidate_health", return_value=(h, "serial"))
            )
            cap = scope.enter_context(
                patch.object(m, "acquire", return_value={"state": "ABSENT"})
            )
            result, serial = m.observe(
                Path("/fixture"), {"binding_sha256": "k", "binding": {"preflight": {}}}
            )
            self.assertIsNone(serial)
            self.assertFalse(result["transport_authorized"])
            self.assertEqual(result["boot_id_sha256"], h["boot_id_sha256"])
            self.assertEqual(cap.call_count, 1)

    def test_terminal_and_uncertain_rollback_cuts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            with (
                patch.object(m.owner, "engine", Mock(), create=True) as e,
                patch.object(m, "old_restore") as old,
            ):
                (run / "terminal.json").write_text("{}")
                m.restore(run)
                e.finalize_resident.assert_called_once_with(run)
                e.resume_run.assert_not_called()
                old.assert_not_called()
                (run / "terminal.json").unlink()
                (run / "rollback-intent.json").write_text("{}")
                m.restore(run)
                old.assert_not_called()
                self.assertEqual(e.finalize_resident.call_count, 2)
                e.resume_run.assert_not_called()


@unittest.skipUnless(AVAILABLE, "private owner fixtures required")
class AutomaticRecovery(unittest.TestCase):
    def test_accepted_adb_arrival_uses_original_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            for n in (
                "candidate-intent",
                "candidate-observation",
                "rollback-download-arrival",
            ):
                (run / (n + ".json")).write_text("{}")
            with (
                patch.object(m.owner, "engine", Mock(), create=True) as e,
                patch.object(m, "old_restore") as physical,
            ):
                e.read_json.return_value = {"transport_authorized": True}
                e.resume_run.side_effect = lambda r: (r / "terminal.json").write_text(
                    "{}"
                )
                m.restore(run)
                e.resume_run.assert_called_once_with(run)
                e.finalize_resident.assert_called_once_with(run)
                physical.assert_not_called()


@unittest.skipUnless(AVAILABLE, "private prior owner required")
class RecoveryAuthorization(unittest.TestCase):
    def test_rejected_tag_cannot_promote_an_apparent_arrival(self):
        from types import SimpleNamespace
        import json

        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            run = Path(tmp)
            ticket = run / "ticket"
            ticket.mkdir()
            h = {
                "boot_id_sha256": "boot",
                "serial_sha256": "serial",
                "topology_sha256": "port",
            }
            obs = {
                "environment": "resident-android",
                "transport_authorized": True,
                "resident_health": h,
            }
            intent = {
                "binding_sha256": "k",
                "source_serial_sha256": "serial",
                "source_boot_id_sha256": "boot",
            }
            records = {
                "candidate-observation.json": obs,
                "prepared.json": {"binding_sha256": "k", "binding": {"preflight": h}},
                "rollback-download-intent.json": intent,
            }
            e = Mock()
            e.read_json.side_effect = lambda path, desc: records[path.name]
            e.digest.return_value = "intent-key"
            stack.enter_context(patch.object(m.owner, "engine", e, create=True))
            stack.enter_context(patch.object(m, "validate_observation"))
            stack.enter_context(patch.object(m.base, "ticket_dir", return_value=ticket))
            recovery_state = ["ABSENT"]

            def tag(r, phase, health):
                return {
                    "state": recovery_state[0] if phase == "recovery-tag" else "C",
                    "raw_sha256": "read-digest",
                }

            stack.enter_context(patch.object(m, "receipt", side_effect=tag))
            proof = {
                "binding_sha256": "k",
                "tag": "read-digest",
                "identity": h,
                "intent": "intent-key",
            }
            stack.enter_context(patch.object(m.base, "get", return_value=proof))
            with self.assertRaises(m.owner.Stop):
                m.automatic_proof(run)
            recovery_state[0] = "C"
            cap = Mock()
            handle = SimpleNamespace(
                name="rollback-reboot",
                stdout_path=run / "rollback-reboot.stdout",
                stderr_path=run / "rollback-reboot.stderr",
                receipt_path=run / "rollback-reboot.capture.json",
                returncode=0,
            )
            handle.receipt_path.write_text(json.dumps({"fixture": True}))
            cap.load_handle.return_value = handle
            cap.read_stderr.return_value = cap.read_stdout.return_value = b""
            ce = Mock(raw_capture=cap, MAX_ADB_BYTES=4096)
            ce.raw_dispatch_proved.return_value = True
            stack.enter_context(patch.object(m.cal, "engine", ce, create=True))
            empty = hashlib.sha256(b"").hexdigest()
            records["rollback-download-result.json"] = {
                "capture_receipt": {
                    "path": str(handle.receipt_path),
                    **m.owner.receipt(handle.receipt_path),
                },
                "outcome": "uncertain",
                "returncode": 0,
                "replay_permitted": False,
                "stdout_sha256": empty,
                "stderr_sha256": empty,
            }
            with self.assertRaises(m.owner.Stop):
                m.automatic_proof(run)
            records["rollback-download-result.json"]["outcome"] = "dispatched"
            m.automatic_proof(run)
            handle.stdout_path = run / "other.stdout"
            with self.assertRaises(m.owner.Stop):
                m.automatic_proof(run)
