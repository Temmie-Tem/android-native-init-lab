import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_health_h0.py"
REPORT = ROOT / "docs/reports/S20PLUS_G986N_AUTONOMOUS_HEALTH_H0_2026-08-23.md"


def load_module():
    spec = importlib.util.spec_from_file_location("s20plus_autonomous_health_h0_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class S20PlusAutonomousHealthH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def result(self):
        properties = {key: "" for key in self.module.INVENTORY_CONTRACT["property_keys"] if key != "boot_id"}
        properties.update({
            "model": "SM-G986N", "device": "y2q", "product_name": "y2qksx",
            "build_product": "y2q", "incremental": "G986NKSS8IYC2",
            "fingerprint": "samsung/y2qksx/y2q:13/TP1A/G986NKSS8IYC2:user/release-keys",
            "boot_completed": "1", "bootanim": "stopped", "selinux": "Enforcing",
            "shell_identity": "uid=2000(shell) gid=2000(shell)",
        })
        return {
            "schema": self.module.INVENTORY_CONTRACT["schema"],
            "version": self.module.INVENTORY_CONTRACT["version"],
            "mode": "connected-read-only",
            "target": {"model": "SM-G986N", "adb_serial_sha256": "1" * 64, "usb_topology_sha256": "2" * 64, "other_serial_sha256": [], "inventory_sha256": "3" * 64},
            "properties": properties,
            "boot_id_sha256": "4" * 64,
            "usb_debugging_verified": True,
            "adb_authorization_state": "device",
            "host_tool": {"path": self.module.INVENTORY_CONTRACT["expected_adb_path"], "device": 1, "inode": 2, "mtime_ns": 3, "size": 4, "sha256": "5" * 64, "version_output_sha256": "6" * 64},
            "host_command_count": 6, "inventory_command_count": 2, "selected_target_command_count": 3,
            "other_target_command_count": 0, "s22plus_command_count": 0, "a90_command_count": 0,
            "device_writes": False, "root_used": False, "reboot_requested": False,
            "mode_transition_requested": False, "payload_transfer": False, "partition_access": False,
            "d1_authorized": False, "f1_authorized": False, "verdict": self.module.INVENTORY_CONTRACT["verdict"],
        }

    def setUp(self):
        self.old_active = self.module.HEALTH_ACTIVE
        self.old_live = self.module.LIVE_AUTHORITY
        self.old_mechanical = self.module.MECHANICALLY_ACTIVATABLE
        self.old_evidence = self.module.DURABLE_EVIDENCE_INTEGRATED
        self.addCleanup(self.restore)

    def restore(self):
        self.module.HEALTH_ACTIVE = self.old_active
        self.module.LIVE_AUTHORITY = self.old_live
        self.module.MECHANICALLY_ACTIVATABLE = self.old_mechanical
        self.module.DURABLE_EVIDENCE_INTEGRATED = self.old_evidence

    def test_render_is_dormant_and_commandless(self):
        plan = self.module.render_plan()
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertFalse(plan["mechanically_activatable"])
        self.assertFalse(plan["durable_evidence_integrated"])
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["device_effects"], [])
        self.assertEqual(len(plan["fixed_transcript"]), 6)

    def test_direct_observer_gates_before_command(self):
        with self.assertRaisesRegex(self.module.HealthH0Error, "dormant"):
            self.module.observe_once()

    def test_all_four_activation_gates_are_mandatory_for_every_bound_observer(self):
        closures = (self.module._BOUND_OBSERVE, self.module._load_inventory()[0])
        fields = (
            "HEALTH_ACTIVE",
            "LIVE_AUTHORITY",
            "MECHANICALLY_ACTIVATABLE",
            "DURABLE_EVIDENCE_INTEGRATED",
        )
        for missing in fields:
            for field in fields:
                setattr(self.module, field, field != missing)
            for closure in closures:
                with self.subTest(missing=missing, closure=closure), self.assertRaisesRegex(
                    self.module.HealthH0Error, "dormant"
                ):
                    closure()

    def test_sanitized_observation_is_exact_and_read_only(self):
        result = self.module.validate_health_result(self.result())
        self.assertEqual(result["target"]["model"], "SM-G986N")
        self.assertEqual(result["properties"]["incremental"], "G986NKSS8IYC2")
        self.assertEqual(result["properties"]["selinux"], "Enforcing")
        self.assertFalse(result["device_writes"])
        self.assertEqual(result["other_target_command_count"], 0)

    def test_public_runtime_accepts_no_callback_or_path(self):
        with self.assertRaises(TypeError):
            self.module.observe_once(lambda *_: None)
        with self.assertRaises(TypeError):
            self.module.observe_once(path="/tmp/x")

    def test_target_build_selinux_and_bool_integer_drift_reject(self):
        result = self.result()
        for key, value in (("model", "SM-G986B"), ("incremental", "WRONG"), ("selinux", "Permissive"), ("build_product", "foreign"), ("fingerprint", "foreign"), ("shell_identity", "uid=2000(shell) gid=0(root)")):
            hostile = {**result, "properties": dict(result["properties"])}
            if key == "model":
                hostile["target"] = dict(result["target"])
                hostile["target"]["model"] = value
            else:
                hostile["properties"][key] = value
            with self.subTest(key=key), self.assertRaises(self.module.HealthH0Error):
                self.module.validate_health_result(hostile)
        hostile = dict(result)
        hostile["host_command_count"] = True
        with self.assertRaises(self.module.HealthH0Error):
            self.module.validate_health_result(hostile)

    def test_hash_and_extra_key_drift_reject(self):
        result = self.result()
        hostile = {**result, "boot_id_sha256": "X" * 64}
        with self.assertRaises(self.module.HealthH0Error):
            self.module.validate_health_result(hostile)
        hostile = {**result, "extra": 1}
        with self.assertRaises(self.module.HealthH0Error):
            self.module.validate_health_result(hostile)

    def test_source_receipts_are_current(self):
        receipts = self.module.source_receipts()
        self.assertEqual(receipts["coordinator"]["sha256"], self.module.SOURCES["coordinator"]["sha256"])
        self.assertEqual(receipts["inventory"]["sha256"], self.module.SOURCES["inventory"]["sha256"])

    def test_arbitrary_source_request_is_rejected_before_open(self):
        with self.assertRaisesRegex(self.module.HealthH0Error, "not allowlisted"):
            self.module._read_exact_source({"path": "/etc/passwd", "size": 1, "sha256": "0" * 64}, "foreign")

    def test_report_records_pass_go_not_active(self):
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("PASS_GO_NOT_ACTIVE", report)
        self.assertIn("durable evidence publication is not implemented", report)
        self.assertIn("reboot and Download control are not implemented", report)


if __name__ == "__main__":
    unittest.main()
