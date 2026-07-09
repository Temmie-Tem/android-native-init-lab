import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_o3_minimal_acm_live_gate.py"
MANIFEST = ROOT / "workspace/private/outputs/s22plus_native_init/o3_minimal_acm_v0_1/manifest.json"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location("s22plus_o3_minimal_acm_live_gate_tested", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusO3MinimalAcmLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    @unittest.skipUnless(MANIFEST.is_file(), "O3 build manifest unavailable")
    def test_real_manifest_matches_exact_live_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "gate.log"
            data = self.module.verify_manifest(MANIFEST, log)
        self.assertEqual(data["hashes"]["ap_tar_md5"], self.module.EXPECTED_AP_SHA256)
        self.assertEqual(data["plan"]["module_count"], 59)
        self.assertFalse(data["safety"]["live_flash_authorized"])

    def test_status_contract_accepts_only_complete_ready_bundle(self):
        values = {
            "marker": self.module.EXPECTED_MARKER,
            "version": "0.1",
            "phase": "control-ready",
            "result": "ready",
            "rc": "0",
            "plan_count": "59",
            "module_attempted": "59",
            "module_loaded": "57",
            "module_eexist": "2",
            "module_failed": "0",
            "proc_registration_rc": "0",
            "proc_eof": "1",
            "proc_found": "59",
            "gate_mask": "0xff",
            "gate_count": "8",
            "configfs_rc": "0",
            "ssusb_mode_write_rc": "0",
            "ssusb_mode_readback_ok": "1",
            "udc_bind_rc": "0",
            "udc_readback_ok": "1",
            "ttyGS0_ready": "1",
            "gadget_function": "acm.usb0",
            "udc": "a600000.dwc3",
            "protocol_result": "pass",
            "protocol_handled": "128",
            "protocol_invalid": "0",
            "protocol_crc_errors": "0",
            "protocol_seq_errors": "0",
        }
        self.assertEqual(self.module.status_reasons(values), [])
        values["gate_mask"] = "0x7f"
        self.assertIn("gate_mask-mismatch:'0x7f'", self.module.status_reasons(values))

    def test_agents_exception_requires_every_pin_and_rejects_consumed_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "gate.log"
            segment = self.module.ACTIVE_EXCEPTION_HEADING + "\n" + "\n".join(
                self.module.policy_markers()
            )
            (root / "AGENTS.md").write_text(segment + "\n", encoding="utf-8")
            self.module.verify_agents_exception(root, log)
            (root / "AGENTS.md").write_text(
                segment + "\nConsumed/retired\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(SystemExit, "absent or consumed"):
                self.module.verify_agents_exception(root, log)

    def test_live_requires_independent_candidate_and_rollback_tokens(self):
        good = argparse.Namespace(
            ack=self.module.LIVE_ACK_TOKEN,
            rollback_ack=self.module.ROLLBACK_ACK_TOKEN,
        )
        self.module.validate_live_tokens(good)
        bad_live = argparse.Namespace(ack="wrong", rollback_ack=self.module.ROLLBACK_ACK_TOKEN)
        with self.assertRaisesRegex(SystemExit, "--live requires --ack"):
            self.module.validate_live_tokens(bad_live)
        bad_rollback = argparse.Namespace(ack=self.module.LIVE_ACK_TOKEN, rollback_ack="wrong")
        with self.assertRaisesRegex(SystemExit, "--rollback-ack"):
            self.module.validate_live_tokens(bad_rollback)

    def test_source_pins_canonical_timeline_and_attended_rollback(self):
        text = SCRIPT.read_text(encoding="ascii")
        for phase in self.module.REQUIRED_TIMELINE_PHASES:
            self.assertIn(f'"{phase}"', text)
        self.assertIn('"events"', (SCRIPT_DIR / "s22plus_m25_hs_only_usb2_acm_live_gate.py").read_text())
        self.assertIn("manual-rollback-wait", text)
        self.assertIn("perform_rollback(", text)
        self.assertIn("verify_partition_hash(", text)
        self.assertIn("collect_retained(run_dir", text)
        self.assertLess(text.index("manual-rollback-wait"), text.rindex("perform_rollback("))


if __name__ == "__main__":
    unittest.main()
