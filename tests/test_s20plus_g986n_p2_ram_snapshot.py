import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
NATIVE = ROOT / "workspace/public/src/native-init"
sys.path.insert(0, str(SCRIPTS))
import s20plus_g986n_p2_ram_snapshot as codec

BOOT = "11111111-2222-4333-8444-555555555555"
BOOT_SHA = hashlib.sha256(BOOT.encode()).hexdigest()


class SnapshotProducerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.tmp.name) / "harness"
        cls.arm_binary = Path(cls.tmp.name) / "harness-arm64"
        source = ROOT / "tests/s20plus_p2_ram_snapshot_harness.c"
        flags = ["-std=gnu11", "-O2", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function",
                 "-I", str(NATIVE), str(source)]
        subprocess.run(["gcc", *flags, "-o", str(cls.binary)], check=True, capture_output=True)
        subprocess.run(["aarch64-linux-gnu-gcc", "-static", *flags, "-o", str(cls.arm_binary)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_case(self, scenario="happy", *, arm64=False, setup=None):
        # Actual tmpfs file open/write/readback/fsync/no-replace rename/read.
        with tempfile.TemporaryDirectory(dir="/dev/shm", prefix="s20p2-h0-") as temp:
            root = Path(temp)
            (root / "overlay.d/sbin").mkdir(parents=True)
            (root / "debug_ramdisk").mkdir()
            if setup:
                setup(root)
            argv = (["qemu-aarch64", str(self.arm_binary)] if arm64 else [str(self.binary)])
            run = subprocess.run([*argv, scenario, str(root)], check=True,
                                 capture_output=True, text=True, timeout=15)
            summary = json.loads(run.stdout)
            data = (root / "reader.raw").read_bytes()
        result = codec.analyze(data, expected_boot_id_sha256=BOOT_SHA,
                               returncode=summary["reader_returncode"])
        return summary, data, result

    def test_actual_producer_snapshot_reader_and_codec_join(self):
        summary, data, result = self.run_case()
        self.assertEqual(summary["first_syscall"], 172)
        self.assertEqual((summary["ending"], summary["handoff"], summary["vectors_ok"]), ("exec", 1, 1))
        self.assertEqual(result["structural_verdict"], "MATCH")
        self.assertEqual(result["records"], 3)
        self.assertEqual(result["capture_source"], "pre-exec-ram-kmsg-v1")
        self.assertIs(result["live_authority"], False)
        self.assertIs(result["requires_owner_transfer_and_acquisition_binding"], True)
        self.assertEqual(codec.parse_reader(data)["mode"], 0o100600)

    def test_non_pid1_performs_no_producer_filesystem_effect(self):
        summary, _, result = self.run_case("not-pid1")
        # getpid and the terminal park's nanosleep only.
        self.assertEqual(summary["producer_calls"], 2)
        self.assertEqual(summary["handoff"], 0)
        self.assertEqual(result["structural_verdict"], "NO_PROOF")

    def test_real_arm64_flags_struct_layout_and_file_syscalls(self):
        for scenario, expected in [("happy", "MATCH"), ("write-short", "MATCH"),
                                   ("readback-bad", "NO_PROOF")]:
            with self.subTest(scenario=scenario):
                summary, _, result = self.run_case(scenario, arm64=True)
                self.assertEqual(summary["ending"], "exec")
                self.assertEqual(result["structural_verdict"], expected)

    def test_short_and_interrupted_file_writes_complete(self):
        for scenario in ("write-short", "write-eintr"):
            with self.subTest(scenario=scenario):
                _, _, result = self.run_case(scenario)
                self.assertEqual(result["structural_verdict"], "MATCH")

    def test_publication_failures_keep_partial_and_still_handoff(self):
        for scenario in ("write-zero", "write-error", "readback-bad", "fsync-fail",
                         "close-fail", "rename-file"):
            with self.subTest(scenario=scenario):
                summary, data, result = self.run_case(scenario)
                self.assertEqual(summary["ending"], "exec")
                reader = codec.parse_reader(data)
                self.assertEqual(reader["partial"], 1)
                self.assertTrue(reader["snapshot"])
                self.assertEqual(result["structural_verdict"], "NO_PROOF")

    def test_ram_path_and_exclusive_creation_fail_closed(self):
        for scenario in ("root-not-ram", "overlay-symlink", "part-open", "clock-fail"):
            with self.subTest(scenario=scenario):
                summary, _, result = self.run_case(scenario)
                self.assertEqual(summary["ending"], "exec")
                self.assertEqual(result["structural_verdict"], "NO_PROOF")
        def existing(root):
            p = root / "overlay.d/sbin" / codec.SNAPSHOT_NAME
            p.write_bytes(b"preexisting")
            p.chmod(0o600)
        summary, data, result = self.run_case(setup=existing)
        self.assertEqual(summary["ending"], "exec")
        self.assertEqual(codec.parse_reader(data)["status"], 7)
        self.assertEqual(codec.parse_reader(data)["snapshot"], b"preexisting")
        self.assertEqual(result["structural_verdict"], "NO_PROOF")

    def test_capture_failures_publish_diagnostic_prefix(self):
        expected = {"kmsg-open": 1, "emit-short": 2, "kmsg-eagain": 3,
                    "kmsg-epipe": 4, "kmsg-eio": 5, "capture-deadline": 8}
        for scenario, status in expected.items():
            with self.subTest(scenario=scenario):
                summary, data, result = self.run_case(scenario)
                self.assertEqual(summary["ending"], "exec")
                snapshot = codec.parse_snapshot(codec.parse_reader(data)["snapshot"])
                self.assertEqual(snapshot["status"], status)
                if scenario.startswith("kmsg-e") or scenario == "capture-deadline":
                    self.assertIn(b"Linux version fixture", snapshot["raw"])
                self.assertEqual(result["structural_verdict"], "NO_PROOF")

    def test_missing_head_and_sequence_gap_remain_rejected(self):
        for scenario, reason in [("prefix-lost", "ring-head-evicted"), ("prefix-gap", "capture-sequence-gap")]:
            with self.subTest(scenario=scenario):
                _, _, result = self.run_case(scenario)
                self.assertEqual(result["reason"], reason)

    def test_failed_init_restore_does_not_reexec_witness(self):
        summary, _, _ = self.run_case("rename-init")
        self.assertEqual((summary["ending"], summary["handoff"]), ("park", 0))
        summary, _, _ = self.run_case("exec-fail")
        self.assertEqual((summary["ending"], summary["handoff"]), ("park", 1))

    def test_reader_metadata_filesystem_and_boot_fail_closed(self):
        for scenario in ("reader-metadata", "reader-changed", "reader-not-ram", "reader-boot"):
            with self.subTest(scenario=scenario):
                _, _, result = self.run_case(scenario)
                self.assertEqual(result["structural_verdict"], "NO_PROOF")

    def test_reader_preserves_partial_read_bytes(self):
        _, data, result = self.run_case("reader-short-io")
        reader = codec.parse_reader(data)
        self.assertEqual(reader["status"], 5)
        self.assertEqual(len(reader["snapshot"]), 40)
        self.assertEqual(result["structural_verdict"], "NO_PROOF")

    def test_corrupt_framing_extent_candidate_and_boot_rejected(self):
        summary, original, _ = self.run_case()
        mutations = []
        for offset in (0, 16, 24, 32, 56, 60, 64, 72, 80, 116, 152,
                       codec.READER_HEADER, codec.READER_HEADER + 16,
                       codec.READER_HEADER + 24, codec.READER_HEADER + 32,
                       codec.READER_HEADER + 56, codec.READER_HEADER + 88,
                       codec.READER_HEADER + 124):
            data = bytearray(original); data[offset] ^= 1; mutations.append(bytes(data))
        mutations.extend((original[:-1], original + b"\0", original[:100]))
        for data in mutations:
            result = codec.analyze(data, expected_boot_id_sha256=BOOT_SHA, returncode=summary["reader_returncode"])
            self.assertEqual(result["structural_verdict"], "NO_PROOF")
        self.assertEqual(codec.analyze(original, expected_boot_id_sha256="0" * 64, returncode=0)["structural_verdict"], "NO_PROOF")
        self.assertEqual(codec.analyze(original, expected_boot_id_sha256=BOOT_SHA, returncode=True)["structural_verdict"], "NO_PROOF")


if __name__ == "__main__":
    unittest.main()
