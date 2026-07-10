import importlib.util
import json
import sys
import unittest
import zlib
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3436_ramoops_positive_control_design.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_v3436_ramoops_positive_control_design", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3436RamoopsPositiveControlDesignTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.root = cls.module.repo_root()
        cls.contract = cls.module.build_contract(cls.root)
        cls.run_id = "0123456789abcdef0123456789abcdef"

    def test_committed_contract_is_current(self):
        committed = (self.root / self.module.OUTPUT).read_text(encoding="utf-8")
        expected = json.dumps(self.contract, indent=2, sort_keys=True) + "\n"
        self.assertEqual(committed, expected)

    def test_host_only_and_policy_inactive(self):
        self.assertEqual(self.contract["verdict"], "HOST_DESIGN_PASS_NO_LIVE")
        self.assertEqual(
            self.contract["safety"],
            {
                "host_only": True,
                "device_contact": False,
                "image_build": False,
                "flash": False,
                "panic": False,
                "reboot": False,
                "live_authorized": False,
                "agents_modified": False,
            },
        )
        policy = self.contract["policy_split"]
        self.assertFalse(policy["currently_active"])
        self.assertTrue(policy["both_required_before_live"])
        self.assertTrue(policy["independent_ack_tokens_required"])

    def test_final_goal_and_positive_control_order_are_explicit(self):
        objective = self.contract["objective"]
        self.assertIn("without Android userspace", objective["final_state"])
        self.assertIn("before direct PID1", objective["purpose"])
        self.assertIn("Android/Magisk", objective["first_live_target"])

    def test_artifacts_are_exact_and_dtbo_only(self):
        artifacts = self.contract["artifacts"]
        self.assertEqual(
            artifacts["candidate_ap_sha256"],
            "622ac0259eb61a7c9ef71eff44d4ea8bb3edbc6a90c3f2b237be7fdf88cb0264",
        )
        self.assertEqual(
            artifacts["rollback_ap_sha256"],
            "6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa",
        )
        self.assertEqual(artifacts["expected_member"], "dtbo.img.lz4")
        self.assertEqual(
            self.module.tar_members(self.root / self.module.CANDIDATE_AP),
            ["dtbo.img.lz4"],
        )
        self.assertEqual(
            self.module.tar_members(self.root / self.module.ROLLBACK_AP),
            ["dtbo.img.lz4"],
        )

    def test_layout_matches_v3435(self):
        self.assertEqual(
            self.contract["layout"],
            {
                "region_size": 0x200000,
                "pmsg_size": 0x100000,
                "console_size": 0x80000,
                "record_size": 0x40000,
                "dmesg_size": 0x80000,
                "dmesg_record_count": 2,
            },
        )
        self.assertEqual(
            self.contract["predecessor"]["sha256"],
            "ee5761c22f590ec01a398dc75bdb31e87e4c983d34b813d94b1428ca7b4e1680",
        )

    def test_full_state_path_and_evidence_first_rule(self):
        self.module.validate_transition_path(list(self.module.STATE_ORDER))
        with self.assertRaises(self.module.DesignError):
            self.module.validate_transition_path(
                ["STOCK_BASELINE", "CANDIDATE_TRANSFER", "CLASSIFIED"]
            )
        self.assertIn(
            "before stock DTBO rollback", self.contract["evidence_first_rule"]
        )
        recovery = self.contract["recovery"]
        self.assertIn("do not auto-rollback", recovery["post_panic_no_android"])
        self.assertEqual(recovery["collection_retry_limit"], 2)

    def test_timeline_uses_single_events_schema(self):
        timeline = self.contract["timeline"]
        self.assertEqual(timeline["schema"], "events:[{name,timestamp_utc}]")
        required = timeline["required_order"]
        for phase in (
            "candidate_flash_start",
            "candidate_flash_done",
            "candidate_boot_ready",
            "live_session_start",
            "live_session_end",
            "rollback_flash_start",
            "rollback_flash_done",
            "rollback_boot_ready",
        ):
            self.assertIn(phase, required)
        self.assertLess(required.index("evidence_collect_done"), required.index("rollback_flash_start"))
        self.assertTrue(timeline["ad_hoc_shapes_forbidden"])
        self.assertTrue(timeline["flush_after_every_event"])

    def test_marker_roundtrip_for_all_phases(self):
        for phase, sequence in self.module.PHASE_SEQUENCE.items():
            frame = self.module.encode_marker(self.run_id, phase)
            marker = self.module.decode_frame(frame)
            self.assertEqual(marker.run_id, self.run_id)
            self.assertEqual(marker.phase, phase)
            self.assertEqual(marker.sequence, sequence)
            self.assertEqual(marker.dtbo_sha256, self.module.PINS[self.module.CANDIDATE_RAW])
            self.assertEqual(marker.contract_sha256, self.module.CONTRACT_SHA256)

    def test_marker_rejects_crc_and_length_corruption(self):
        frame = bytearray(self.module.encode_marker(self.run_id, "PREPANIC_KMSG"))
        frame[-4] = ord("0") if frame[-4] != ord("0") else ord("1")
        with self.assertRaises(self.module.DesignError):
            self.module.decode_frame(bytes(frame))
        frame = bytearray(self.module.encode_marker(self.run_id, "PREPANIC_KMSG"))
        length_offset = len(self.module.FRAME_START)
        frame[length_offset : length_offset + 4] = b"0001"
        with self.assertRaises(self.module.DesignError):
            self.module.decode_frame(bytes(frame))

    def test_classifier_passes_console_or_dmesg_retention(self):
        frame = self.module.encode_marker(self.run_id, "PREPANIC_KMSG")
        result = self.module.classify_retained(
            self.run_id,
            {"baseline": b"clean"},
            {"console-ramoops-0": b"boot\n" + frame + b"\npanic"},
        )
        self.assertEqual(result["result"], "PASS_RAMOOPS_CONSOLE_DMESG_RETENTION")
        result = self.module.classify_retained(
            self.run_id,
            {"baseline": b"clean"},
            {"dmesg-ramoops-0": self.module.encode_marker(self.run_id, "TRIGGER_KMSG")},
        )
        self.assertEqual(result["result"], "PASS_RAMOOPS_CONSOLE_DMESG_RETENTION")

    def test_classifier_keeps_pmsg_only_partial(self):
        result = self.module.classify_retained(
            self.run_id,
            {},
            {"pmsg-ramoops-0": self.module.encode_marker(self.run_id, "PREPANIC_PMSG")},
        )
        self.assertEqual(result["result"], "PARTIAL_PMSG_ONLY_NO_CONSOLE_DMESG_PROOF")

    def test_classifier_distinguishes_no_proof_and_stale_collision(self):
        result = self.module.classify_retained(self.run_id, {}, {"other": b"none"})
        self.assertEqual(result["result"], "NO_PROOF_NO_CURRENT_RUN_FRAME")
        result = self.module.classify_retained(
            self.run_id, {"baseline": self.run_id.encode("ascii")}, {}
        )
        self.assertEqual(result["result"], "FAIL_STALE_OR_COLLISION")

    def test_classifier_rejects_wrong_bound_identity(self):
        payload = self.module.marker_payload(self.run_id, "PREPANIC_KMSG")
        wrong = payload.replace(
            self.module.PINS[self.module.CANDIDATE_RAW].encode("ascii"), b"0" * 64
        )
        crc = zlib.crc32(wrong) & 0xFFFFFFFF
        frame = (
            self.module.FRAME_START
            + f"{len(wrong):04x}|".encode("ascii")
            + wrong
            + f"|crc={crc:08x}".encode("ascii")
            + self.module.FRAME_END
        )
        result = self.module.classify_retained(
            self.run_id, {}, {"console-ramoops-0": frame}
        )
        self.assertEqual(result["result"], "FAIL_MALFORMED_OR_IDENTITY")

    def test_no_live_transport_or_policy_activation_path(self):
        source = (self.root / SCRIPT).read_text(encoding="utf-8")
        self.assertNotIn("adb ", source)
        self.assertNotIn("odin4 ", source)
        self.assertNotIn("--live", source)
        self.assertNotIn("/proc/sysrq-trigger", source)
        self.assertNotIn("reboot(", source)


if __name__ == "__main__":
    unittest.main()
