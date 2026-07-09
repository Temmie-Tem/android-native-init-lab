import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_o3r1_native_retained_sysrq_live_gate.py"
MANIFEST = ROOT / "workspace/private/outputs/s22plus_native_init/o3r1_native_retained_sysrq_v0_1/manifest.json"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_o3r1_native_retained_sysrq_live_gate_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusO3R1NativeRetainedSysrqLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    @unittest.skipUnless(MANIFEST.is_file(), "O3R1 build manifest unavailable")
    def test_real_manifest_matches_exact_live_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self.module.verify_manifest(MANIFEST, Path(tmp) / "gate.log")
        self.assertEqual(data["hashes"]["ap_tar_md5"], self.module.EXPECTED_AP_SHA256)
        self.assertEqual(data["hashes"]["init"], self.module.EXPECTED_INIT_SHA256)
        self.assertEqual(data["tar_members"], ["boot.img.lz4"])
        self.assertFalse(data["safety"]["live_flash_authorized"])
        self.assertEqual(data["safety"]["procfs_write_allowlist"], ["/proc/sysrq-trigger=c"])

    def test_classifier_requires_exact_marker_and_sysrq_panic(self):
        payload = (
            f"{self.module.EXPECTED_MARKER} version=0.1 phase=before-sysrq-c rc=0 "
            "action=intentional-kernel-panic\n"
            "sysrq: Trigger a crash\n"
            "Kernel panic - not syncing: sysrq triggered crash\n"
        ).encode()
        result = self.module.classify_retained({"last_kmsg.bin": payload})
        self.assertTrue(result["exact_pass"])
        self.assertTrue(result["channel_proven"])
        self.assertEqual(result["verdict"], "pass-marker-and-sysrq-panic")

    def test_classifier_separates_pid1_fallback(self):
        payload = (
            f"{self.module.EXPECTED_MARKER} version=0.1 phase=sysrq-returned rc=-22 "
            "action=pid1-exit-group-panic\n"
            "Kernel panic - not syncing: Attempted to kill init!\n"
        ).encode()
        result = self.module.classify_retained({"last_kmsg.bin": payload})
        self.assertFalse(result["exact_pass"])
        self.assertTrue(result["channel_proven"])
        self.assertEqual(result["verdict"], "marker-retained-sysrq-failed-init-death-panic")

    def test_classifier_does_not_promote_panic_without_marker(self):
        result = self.module.classify_retained(
            {"last_kmsg.bin": b"Kernel panic - not syncing: Attempted to kill init!\n"}
        )
        self.assertFalse(result["exact_pass"])
        self.assertFalse(result["channel_proven"])
        self.assertEqual(result["verdict"], "init-death-panic-without-marker")

    def test_agents_exception_is_exact_and_consumption_aware(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "gate.log"
            segment = self.module.ACTIVE_EXCEPTION_HEADING + "\n" + "\n".join(
                self.module.policy_markers()
            )
            (root / "AGENTS.md").write_text(segment + "\n", encoding="utf-8")
            self.module.verify_agents_exception(root, log)
            (root / "AGENTS.md").write_text(segment + "\nConsumed/retired\n", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "absent or consumed"):
                self.module.verify_agents_exception(root, log)
            self.module.verify_agents_exception(root, log, allow_consumed=True)

    def test_live_requires_three_independent_confirmations(self):
        good = argparse.Namespace(
            ack=self.module.LIVE_ACK_TOKEN,
            rollback_ack=self.module.ROLLBACK_ACK_TOKEN,
            confirm_debug_level_mid=self.module.DEBUG_LEVEL_CONFIRM_TOKEN,
        )
        self.module.validate_live_tokens(good)
        for field in ("ack", "rollback_ack", "confirm_debug_level_mid"):
            values = vars(good).copy()
            values[field] = "wrong"
            with self.assertRaises(SystemExit):
                self.module.validate_live_tokens(argparse.Namespace(**values))

    def test_source_keeps_attended_rollback_and_canonical_timeline(self):
        text = SCRIPT.read_text(encoding="ascii")
        for phase in self.module.REQUIRED_TIMELINE_PHASES:
            self.assertIn(f'"{phase}"', text)
        self.assertIn("o3r1-manual-rollback-wait", text)
        self.assertIn("base.perform_rollback(", text)
        self.assertIn("base.verify_partition_hash(", text)
        self.assertIn("assert_sec_debug_mid_state(", text)
        self.assertNotIn("/dev/pmsg0", text)


if __name__ == "__main__":
    unittest.main()
