import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path("workspace/public/src/scripts/revalidation").resolve()
SCRIPT = SCRIPT_DIR / "s22plus_o1_stock_first_stage_control_live_gate.py"


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_o1_stock_first_stage_control_live_gate", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusO1StockFirstStageControlLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_active_agents_exception_has_every_required_marker(self):
        text = Path("AGENTS.md").read_text(encoding="utf-8")
        segment = self.module.active_exception_segment(text)
        self.assertTrue(segment)
        normalized = " ".join(segment.split())
        self.assertEqual(
            [marker for marker in self.module.policy_required_markers() if marker not in normalized],
            [],
        )
        self.assertNotIn("Consumed exception", segment)

    def test_manifest_matches_exact_o1_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            intended = [
                "overlay.d/s22plus_o1_control.rc",
                "overlay.d/sbin/s22plus_o1_service.sh",
                "overlay.d/sbin/s22plus_o1_tty_echo",
            ]
            manifest.write_text(
                json.dumps(
                    {
                        "hashes": {
                            "base_boot": self.module.EXPECTED_BASE_BOOT_SHA256,
                            "nochange_repack_boot": self.module.EXPECTED_BASE_BOOT_SHA256,
                            "boot_img": self.module.EXPECTED_O1_BOOT_SHA256,
                            "boot_img_lz4": self.module.EXPECTED_O1_BOOT_LZ4_SHA256,
                            "ap_tar_md5": self.module.EXPECTED_O1_AP_SHA256,
                            "kernel_before": self.module.EXPECTED_KERNEL_SHA256,
                            "kernel_after": self.module.EXPECTED_KERNEL_SHA256,
                            "original_magisk_init_before": self.module.EXPECTED_INIT_SHA256,
                            "original_magisk_init_after": self.module.EXPECTED_INIT_SHA256,
                            "overlay_rc": self.module.EXPECTED_RC_SHA256,
                            "overlay_service": self.module.EXPECTED_SERVICE_SHA256,
                            "o0_daemon": self.module.EXPECTED_DAEMON_SHA256,
                        },
                        "safety": {
                            "boot_only": True,
                            "host_only_build": True,
                            "live_flash_authorized": False,
                            "base_is_known_booting_magisk_boot": True,
                            "stock_first_stage_preserved": True,
                            "stock_magisk_init_preserved": True,
                            "kernel_preserved": True,
                            "configfs_write": False,
                            "sysfs_write": False,
                            "active_gadget_change": False,
                            "module_insertions": False,
                            "reboot_request": False,
                            "persistent_partition_mount": False,
                        },
                        "tar_members": [self.module.EXPECTED_MEMBER],
                        "ramdisk": {
                            "added_entries": intended,
                            "replaced_entries": [],
                            "listing_diff": {"added": sorted(intended), "removed": []},
                        },
                    }
                ),
                encoding="utf-8",
            )
            data = self.module.verify_o1_manifest(manifest, Path(tmp) / "gate.log")
        self.assertEqual(data["hashes"]["boot_img"], self.module.EXPECTED_O1_BOOT_SHA256)
        self.assertFalse(data["safety"]["live_flash_authorized"])

    def test_candidate_snapshot_classifier_is_fail_closed(self):
        snapshot = {
            "model": "SM-S906N",
            "device": "g0q",
            "incremental": "S906NKSS7FYG8",
            "boot_completed": "1",
            "boot_recovery": "0",
            "vbstate": "orange",
            "ttyGS0_char": "1",
            "boot_sha256": self.module.EXPECTED_O1_BOOT_SHA256,
            "uid": "0",
            "udc": "a600000.dwc3",
            "usb_config": "mtp,conn_gadget,adb",
        }
        self.assertEqual(self.module.candidate_snapshot_reasons(snapshot), [])
        snapshot["boot_sha256"] = self.module.EXPECTED_BASE_BOOT_SHA256
        self.assertEqual(self.module.candidate_snapshot_reasons(snapshot), ["boot_sha256-mismatch"])

    def test_volatile_result_requires_daemon_and_stock_restore(self):
        evidence = {
            "rc": 0,
            "values": {
                "marker": "1",
                "result": "pass",
                "daemon_rc": "0",
                "restore_rc": "0",
                "o1_service_state": "stopped",
                "o1_daemon_pid": "",
            },
        }
        stock = {"rc": 0, "state": "running", "pid_present": True, "tty_owner_count": 1}
        self.assertEqual(self.module.o1_evidence_reasons(evidence, stock), [])
        evidence["values"]["restore_rc"] = "1"
        self.assertEqual(self.module.o1_evidence_reasons(evidence, stock), ["restore_rc-mismatch"])
        evidence["values"]["restore_rc"] = "0"
        stock["tty_owner_count"] = 0
        self.assertEqual(
            self.module.o1_evidence_reasons(evidence, stock),
            ["stock-service-not-restored"],
        )

    def test_live_requires_both_ack_tokens(self):
        args = argparse.Namespace(live=True, ack=None, rollback_ack=None)
        with self.assertRaisesRegex(SystemExit, "--ack"):
            self.module.validate_live_authorization(args)
        args.ack = self.module.LIVE_ACK_TOKEN
        with self.assertRaisesRegex(SystemExit, "--rollback-ack"):
            self.module.validate_live_authorization(args)
        args.rollback_ack = self.module.ROLLBACK_ACK_TOKEN
        self.module.validate_live_authorization(args)

    def test_offline_contract_forbids_native_usb_mutation(self):
        contract = self.module.offline_contract()
        self.assertTrue(contract["boot_only"])
        self.assertTrue(contract["mandatory_rollback"])
        self.assertTrue(contract["stock_first_stage_preserved"])
        self.assertFalse(contract["configfs_write"])
        self.assertFalse(contract["sysfs_write"])
        self.assertFalse(contract["module_insertion"])
        self.assertFalse(contract["persistent_partition_mount"])

    def test_source_contains_canonical_flash_timeline_phases(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for name in self.module.REQUIRED_LIVE_TIMELINE_PHASES:
            self.assertIn(name, source)


if __name__ == "__main__":
    unittest.main()
