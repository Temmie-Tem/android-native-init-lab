from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "build_s20plus_g986n_twrp_identical_resident_write_q0_h0.py"
)
SOURCE = ROOT / (
    "workspace/public/src/native-init/"
    "s20plus_twrp_identical_resident_write_q0.c"
)
OUTPUT = ROOT / (
    "workspace/private/outputs/s20plus_g986n/"
    "twrp_identical_resident_write_q0_h0"
)
PRIVATE_TMP = ROOT / "workspace/private/tmp"
SCRIPT_DIR = SCRIPT.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_s20plus_g986n_twrp_identical_resident_write_q0_h0_tested",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S20PlusTwrpIdenticalResidentWriteQ0H0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.manifest_bytes = (OUTPUT / "manifest.json").read_bytes()
        cls.manifest = json.loads(cls.manifest_bytes)
        cls.backend = OUTPUT / cls.module.Q0_BACKEND_FILENAME

    def test_source_contract_is_exact_s20plus_fixed_input_and_ordered(self):
        contract = self.module.source_contract()
        self.assertEqual(contract["path"], str(SOURCE))
        self.assertFalse(contract["caller_arguments"])
        self.assertEqual(contract["pwrite_call_sites"], 1)
        text = SOURCE.read_text(encoding="ascii")
        self.assertEqual(text.count('"/dev/block/sda23"'), 1)
        self.assertEqual(text.count("pwrite("), 1)
        self.assertIn('"/sys/dev/block/259:7/uevent"', text)
        self.assertIn(self.module.EXPECTED_RESIDENT_SHA256, text)
        self.assertNotIn("argv[1]", text)

    def test_manifest_is_h0_only_and_pins_exact_runtime_geometry(self):
        manifest = self.manifest
        self.assertEqual(manifest["schema"], self.module.SCHEMA)
        self.assertEqual(manifest["verdict"], self.module.VERDICT)
        self.assertEqual(manifest["tier"], "H0")
        self.assertFalse(manifest["live_authority"])
        self.assertEqual(manifest["target"], self.module.TARGET)
        runtime = manifest["runtime_binding"]
        self.assertEqual(runtime["target_path"], "/dev/block/sda23")
        self.assertEqual(runtime["rdev"], "259:7")
        self.assertEqual(runtime["partname"], "boot")
        self.assertEqual(runtime["partition_number"], 23)
        self.assertEqual(runtime["size_bytes"], 67_108_864)
        self.assertEqual(
            runtime["resident_sha256"], self.module.EXPECTED_RESIDENT_SHA256
        )

    def test_published_backend_and_manifest_are_exact_direct_files(self):
        backend_bytes = self.backend.read_bytes()
        self.assertEqual(len(backend_bytes), self.manifest["backend"]["size"])
        self.assertEqual(
            hashlib.sha256(backend_bytes).hexdigest(),
            self.manifest["backend"]["sha256"],
        )
        self.assertEqual(self.manifest["backend"]["path"], self.backend.name)
        backend_state = self.backend.lstat()
        manifest_state = (OUTPUT / "manifest.json").lstat()
        self.assertTrue(stat.S_ISREG(backend_state.st_mode))
        self.assertTrue(stat.S_ISREG(manifest_state.st_mode))
        self.assertEqual(backend_state.st_nlink, 1)
        self.assertEqual(manifest_state.st_nlink, 1)
        self.assertEqual(stat.S_IMODE(backend_state.st_mode), 0o500)
        self.assertEqual(stat.S_IMODE(manifest_state.st_mode), 0o400)

    def test_binary_is_static_aarch64_without_dynamic_or_rwe_surface(self):
        elf = self.manifest["backend"]
        self.assertTrue(elf["static"])
        self.assertFalse(elf["pt_interp"])
        self.assertEqual(elf["dt_needed"], [])
        self.assertEqual(elf["undefined_symbols"], [])
        self.assertFalse(elf["writable_executable_load"])
        self.assertIn("ARM aarch64", elf["file"])
        self.assertIn("statically linked", elf["file"])

    def test_qemu_rejects_every_argument_before_stage_or_write(self):
        completed = subprocess.run(
            [str(self.module.TOOLS["qemu"]), str(self.backend), "unexpected"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
        self.assertEqual(completed.returncode, 70)
        self.assertEqual(completed.stdout, self.module.EXPECTED_ARGUMENT_FAILURE)
        self.assertEqual(completed.stderr, b"")
        refusal = self.manifest["qemu_argument_refusal"]
        self.assertFalse(refusal["write_started"])
        self.assertEqual(refusal["stdout_sha256"], hashlib.sha256(completed.stdout).hexdigest())

    def test_safety_manifest_preserves_interrupted_write_hazard(self):
        safety = self.manifest["safety"]
        for key in (
            "fixed_input",
            "source_and_preimage_exact_before_write",
            "write_fd_identity_guarded",
            "write_fd_used_for_effect",
            "fsync_required",
            "fresh_odirect_readback_fd_independently_guarded",
            "signals_blocked_before_effect",
            "interrupted_write_recoverable_only_not_safe",
        ):
            self.assertTrue(safety[key], key)
        self.assertFalse(safety["caller_arguments"])
        self.assertFalse(safety["device_contact"])
        self.assertFalse(safety["activation"])
        self.assertEqual(safety["reboots"], 0)
        self.assertEqual(safety["other_partition_paths"], 0)

    def test_exact_resident_input_matches_private_known_good_boot(self):
        resident = ROOT / (
            "workspace/private/outputs/s20plus_g986n/"
            "magisk_boot_only_iyc2_v1/candidate/boot.img"
        )
        payload = resident.read_bytes()
        self.assertEqual(len(payload), self.module.EXPECTED_RESIDENT_SIZE)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            self.module.EXPECTED_RESIDENT_SHA256,
        )

    def test_wrong_target_hash_write_site_or_runtime_order_rejects(self):
        original = SOURCE.read_text(encoding="ascii")
        mutations = (
            original.replace('"/dev/block/sda23"', '"/dev/block/sda24"', 1),
            original.replace(self.module.EXPECTED_RESIDENT_SHA256, "0" * 64, 1),
            original.replace("amount = pwrite(target", "amount = write(target", 1),
            original.replace(
                "target = open(Q0_TARGET_PATH, O_WRONLY",
                "target = open(Q0_TARGET_PATH, O_RDONLY",
                1,
            ),
        )
        with tempfile.TemporaryDirectory(
            prefix="s20plus-q0-source-mutation-", dir=PRIVATE_TMP
        ) as temporary:
            for index, mutation in enumerate(mutations):
                path = Path(temporary) / f"source-{index}.c"
                path.write_text(mutation, encoding="ascii")
                with mock.patch.object(self.module, "SOURCE", path):
                    with self.assertRaises(self.module.BuildError):
                        self.module.source_contract()

    def test_forbidden_partition_path_and_process_action_reject(self):
        original = SOURCE.read_text(encoding="ascii")
        mutations = (
            original + '\nstatic const char *forbidden = "/dev/block/by-name/recovery";\n',
            original + "\nstatic void forbidden(void) { reboot(0); }\n",
            original + "\nstatic void forbidden(void) { system(\"dd\"); }\n",
            original + "\nstatic void forbidden(void) { unlink(\"x\"); }\n",
        )
        with tempfile.TemporaryDirectory(
            prefix="s20plus-q0-forbidden-mutation-", dir=PRIVATE_TMP
        ) as temporary:
            for index, mutation in enumerate(mutations):
                path = Path(temporary) / f"source-{index}.c"
                path.write_text(mutation, encoding="ascii")
                with mock.patch.object(self.module, "SOURCE", path):
                    with self.assertRaises(self.module.BuildError):
                        self.module.source_contract()

    def test_two_fresh_builds_are_byte_identical_and_no_clobber(self):
        with tempfile.TemporaryDirectory(
            prefix="s20plus-q0-repro-", dir=PRIVATE_TMP
        ) as temporary:
            root = Path(temporary)
            first = root / "first"
            second = root / "second"
            first_result = self.module.build(first)
            second_result = self.module.build(second)
            self.assertEqual(first_result["backend"], second_result["backend"])
            self.assertEqual(
                (first / self.module.Q0_BACKEND_FILENAME).read_bytes(),
                (second / self.module.Q0_BACKEND_FILENAME).read_bytes(),
            )
            self.assertEqual(
                (first / "manifest.json").read_bytes(),
                (second / "manifest.json").read_bytes(),
            )
            with self.assertRaisesRegex(self.module.BuildError, "already exists"):
                self.module.build(first)

    def test_builder_has_no_connected_or_live_execution_surface(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import adb",
            '"/usr/bin/adb"',
            "odin4",
            "--connected",
            "--prepare",
            "--execute",
            "--approval",
            "subprocess.Popen",
        ):
            self.assertNotIn(forbidden, text)
        self.assertFalse(self.manifest["live_authority"])
        self.assertFalse(self.manifest["safety"]["device_contact"])


if __name__ == "__main__":
    unittest.main()
