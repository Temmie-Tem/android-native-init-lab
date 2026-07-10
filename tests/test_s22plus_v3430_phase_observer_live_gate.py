import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3430_phase_observer_live_gate.py"
)


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_v3430_phase_observer_live_gate", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3430PhaseObserverLiveGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.root = cls.module.observer.repo_root()

    def test_candidate_artifact_and_marker_roundtrip(self):
        expectation, markers = self.module.load_candidate(self.root)
        self.assertEqual(expectation.run_id, self.module.EXPECTED_RUN_ID)
        self.assertEqual(markers["run_id"], self.module.EXPECTED_RUN_ID)
        self.assertEqual(
            self.module.tar_members(self.root / self.module.CANDIDATE_AP),
            ["boot.img.lz4"],
        )

    def test_offline_plan_is_not_live_authorization(self):
        plan = self.module.offline_plan(self.root)
        self.assertEqual(plan["schema"], self.module.SCHEMA)
        self.assertTrue(plan["candidate_flash"])
        self.assertTrue(plan["manual_transition"])
        self.assertFalse(plan["live_authorized_by_plan"])
        self.assertEqual(
            plan["candidate_ap_sha256"],
            self.module.EXPECTED_CANDIDATE_AP_SHA256,
        )

    def test_active_exception_is_present_and_fully_pinned(self):
        self.module.verify_agents_exception(self.root)
        segment = self.module.active_exception_segment(
            (self.root / "AGENTS.md").read_text(encoding="utf-8")
        )
        self.assertNotIn("Consumed/retired", segment)
        self.assertNotIn("Consumed exception", segment)

    def test_consumed_exception_is_rejected_for_new_live(self):
        heading = self.module.ACTIVE_EXCEPTION_HEADING
        segment = heading + "\n   Consumed/retired " + " ".join(
            self.module.policy_markers(self.root)
        )
        with self.assertRaisesRegex(self.module.LiveGateError, "already consumed"):
            self.module.validate_exception_segment(
                segment,
                self.module.policy_markers(self.root),
                allow_consumed=False,
            )
        self.module.validate_exception_segment(
            segment,
            self.module.policy_markers(self.root),
            allow_consumed=True,
        )

    def test_bad_live_ack_stops_before_policy_or_device(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                self.module.LiveGateError, "live acknowledgement token mismatch"
            ):
                self.module.live_run(
                    self.root,
                    Path(temp),
                    "wrong-token",
                    self.module.MAX_MANUAL_WAIT_SEC,
                )

    def test_file_pin_detects_post_verification_change(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "artifact"
            path.write_bytes(b"before")
            pin = self.module.file_pin(path)
            path.write_bytes(b"after-longer")
            with self.assertRaisesRegex(
                self.module.LiveGateError, "pinned file changed"
            ):
                self.module.require_unchanged(pin)

    def test_run_directory_uses_v3430_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = self.module.allocate_run_dir(root, None)
            self.assertTrue(run_dir.name.startswith("s22plus_v3430_phase_observer_"))

    def test_timeline_uses_canonical_eight_phase_names(self):
        self.assertEqual(
            self.module.control.TIMELINE_REQUIRED_NAMES,
            (
                "live_session_start",
                "candidate_flash_start",
                "candidate_flash_done",
                "candidate_boot_ready",
                "rollback_flash_start",
                "rollback_flash_done",
                "rollback_boot_ready",
                "live_session_end",
            ),
        )

    def test_source_contract_is_boot_only_and_attended(self):
        source = (self.root / SCRIPT).read_text(encoding="utf-8")
        self.assertIn('reboot", "download"', source)
        self.assertIn("MANUAL_ACTION_REQUIRED enter Samsung RDX/Download", source)
        self.assertIn("first_boot_capture", source)
        self.assertIn("candidate AP must contain exactly boot.img.lz4", source)
        self.assertNotIn("emit_marker(", source)
        self.assertNotIn("/dev/block/by-name/", source)
        self.assertNotIn("/sys/module/", source)
        self.assertNotIn("usb_gadget", source)


if __name__ == "__main__":
    unittest.main()
