import copy
import hashlib
import importlib.util
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1a_stream_oracle_qualification.py"
)


def load_module():
    script_dir = str(SCRIPT.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_r4w1a_stream_oracle_qualification_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R4W1AStreamOracleQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_real_retained_evidence_qualifies_host_only(self):
        result = self.module.qualify(ROOT)
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertTrue(result["decision"]["baseline_observer_qualified"])
        self.assertFalse(result["decision"]["second_live_baseline_required"])
        self.assertFalse(result["decision"]["candidate_live_authorized"])
        self.assertEqual(
            result["contract"]["historical_live_verdict_preserved"],
            "FAIL_R4W1A_ORACLE_DRY_RUN_CLEANUP_OR_SHAPE",
        )
        self.assertEqual(
            result["contract"]["fresh_parser"]["marker"]["classification"],
            "MARKER_FAMILY_ABSENT",
        )
        self.assertEqual(
            result["safety"],
            {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "flash": False,
                "policy_activation": False,
                "promotion_record_created": False,
            },
        )

    def test_capture_requires_exact_clean_stream_only_shape(self):
        run = ROOT / self.module.RUN_RELATIVE
        capture = self.module.load_json_bytes(
            (run / "oracle_capture.json").read_bytes(), "oracle_capture.json"
        )
        self.module.validate_capture(capture)
        for mutation in (
            {"after": {"/bugreports/leftover.zip": {}}},
            {"cleanup_attempted": True},
            {"success": True},
            {"errors": []},
        ):
            changed = copy.deepcopy(capture)
            changed.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(
                self.module.QualificationError
            ):
                self.module.validate_capture(changed)

    def test_timeline_rejects_reorder_extra_shape_and_duplicate_time(self):
        run = ROOT / self.module.RUN_RELATIVE
        original = self.module.load_json_bytes(
            (run / "timeline.json").read_bytes(), "timeline.json"
        )
        self.module.validate_timeline(original)

        reordered = copy.deepcopy(original)
        reordered["events"][1], reordered["events"][2] = (
            reordered["events"][2],
            reordered["events"][1],
        )
        extra = copy.deepcopy(original)
        extra["steps"] = []
        duplicate = copy.deepcopy(original)
        duplicate["events"][2]["timestamp_utc"] = duplicate["events"][1]["timestamp_utc"]
        for changed in (reordered, extra, duplicate):
            with self.subTest(changed=changed), self.assertRaises(
                self.module.QualificationError
            ):
                self.module.validate_timeline(changed)

    def test_consumed_timestamp_is_strictly_inside_precapture_interval(self):
        run = ROOT / self.module.RUN_RELATIVE
        timeline = self.module.load_json_bytes(
            (run / "timeline.json").read_bytes(), "timeline.json"
        )
        timestamps, _ = self.module.validate_timeline(timeline)
        consumed = self.module.parse_utc("2026-07-13T09:57:55.901663Z")
        self.assertLess(timestamps[0], consumed)
        self.assertLess(consumed, timestamps[1])
        self.assertGreater(timestamps[1] - timestamps[0], timedelta(0))

    def test_marker_absence_rejects_family_id_phase_and_pid_path(self):
        self.assertEqual(
            self.module.validate_marker_absence(b"ordinary retained log", "clean"),
            {"family_prefix": 0, "marker_id": 0, "phase": 0, "pid_path": 0},
        )
        for token in (
            self.module.oracle.MARKER_FAMILY_PREFIX,
            b"9ed5923b08c5eedbbdb0aaa6f6a5200c",
            b"RAMDISK_EXEC_ACCEPTED",
            b"pid=1|path=/init",
        ):
            with self.subTest(token=token), self.assertRaises(
                self.module.QualificationError
            ):
                self.module.validate_marker_absence(b"prefix" + token + b"suffix", "bad")

    def test_android_contract_is_exact(self):
        self.module.validate_android(self.module.EXPECTED_ANDROID, "baseline")
        for key in ("boot_sha256", "root", "dtbo_sha256", "boot_completed"):
            changed = dict(self.module.EXPECTED_ANDROID)
            changed[key] = "wrong"
            with self.subTest(key=key), self.assertRaises(self.module.QualificationError):
                self.module.validate_android(changed, "baseline")

    def test_source_has_no_device_transport_or_promotion_write(self):
        source = SCRIPT.read_text(encoding="utf-8")
        lowered = source.lower()
        self.assertNotIn("import subprocess", lowered)
        self.assertNotIn("import pyusb", lowered)
        self.assertNotIn("adb devices", lowered)
        self.assertNotIn("odin4 -", lowered)
        self.assertNotIn("oracle_dry_run_pass.json\", result", lowered)
        self.assertIn('"device_contact": False', source)
        self.assertIn('"candidate_live_authorized": False', source)
        self.assertIn('"promotion_record_created": False', source)

    def test_output_is_exclusive_create_and_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "qualification.json"
            payload = {"schema": self.module.SCHEMA, "verdict": self.module.VERDICT}
            self.module.write_new(output, payload)
            self.assertEqual(
                self.module.load_json_bytes(output.read_bytes(), "qualification.json"),
                payload,
            )
            with self.assertRaises(self.module.QualificationError):
                self.module.write_new(output, payload)

    def test_pinned_file_rejects_size_hash_and_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence.bin"
            evidence.write_bytes(b"exact evidence")
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
            metadata, data = self.module.read_pinned_file(
                evidence, evidence.stat().st_size, digest
            )
            self.assertEqual(data, b"exact evidence")
            self.assertEqual(metadata["sha256"], digest)
            with self.assertRaises(self.module.QualificationError):
                self.module.read_pinned_file(evidence, 1, digest)
            with self.assertRaises(self.module.QualificationError):
                self.module.read_pinned_file(evidence, evidence.stat().st_size, "0" * 64)
            link = root / "evidence-link.bin"
            link.symlink_to(evidence)
            with self.assertRaises(self.module.QualificationError):
                self.module.read_pinned_file(link, evidence.stat().st_size, digest)

    def test_policy_gate_requires_retired_and_no_promotion_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            agents = root / "AGENTS.md"
            agents.write_text(f"`{self.module.RETIRED_SENTINEL}`\n", encoding="utf-8")
            self.module.validate_policy_state(root)

            agents.write_text(
                f"`{self.module.RETIRED_SENTINEL}`\n`{self.module.ACTIVE_SENTINEL}`\n",
                encoding="utf-8",
            )
            with self.assertRaises(self.module.QualificationError):
                self.module.validate_policy_state(root)

            agents.write_text(f"`{self.module.RETIRED_SENTINEL}`\n", encoding="utf-8")
            promotion = root / self.module.ORACLE_PASS_RELATIVE
            promotion.parent.mkdir(parents=True)
            promotion.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(self.module.QualificationError):
                self.module.validate_policy_state(root)


if __name__ == "__main__":
    unittest.main()
