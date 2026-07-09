import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workspace/public/src/native-init/s22plus_init_o3r1_native_retained_sysrq.c"
BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_s22plus_o3r1_native_retained_sysrq.py"
MANIFEST = ROOT / "workspace/private/outputs/s22plus_native_init/o3r1_native_retained_sysrq_v0_1/manifest.json"


class S22PlusO3R1NativeRetainedSysrqTest(unittest.TestCase):
    def test_source_is_minimal_and_fail_closed_to_pid1_panic(self):
        text = SOURCE.read_text(encoding="ascii")
        for required in [
            "S22_NATIVE_INIT_O3R1_RETAINED_SYSRQ",
            "entry-pre-proc",
            "proc-mount",
            "sysrq-open",
            "before-sysrq-c",
            "sysrq-returned",
            "pid1-exit-group-panic",
            'o3r1_open("/proc/sysrq-trigger"',
            "o3r1_exit_group(exit_code)",
        ]:
            self.assertIn(required, text)
        for forbidden in [
            "/dev/pmsg0",
            "/proc/sys/kernel/sysrq",
            "/sys/",
            "/config/",
            "/lib/modules",
            "finit_module",
            "usb_gadget",
            "a600000",
            "NR_REBOOT",
            "NR_CLONE",
        ]:
            self.assertNotIn(forbidden.lower(), text.lower())
        phases = ["entry-pre-proc", "proc-mount", "sysrq-open", "before-sysrq-c", "sysrq-returned"]
        offsets = [text.index(phase) for phase in phases]
        self.assertEqual(offsets, sorted(offsets))

    @unittest.skipUnless(shutil.which("aarch64-linux-gnu-gcc"), "arm64 compiler unavailable")
    def test_arm64_binary_is_static_freestanding_and_small(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "init"
            built = subprocess.run(
                [
                    "aarch64-linux-gnu-gcc",
                    "-std=gnu11",
                    "-nostdlib",
                    "-static",
                    "-ffreestanding",
                    "-fno-builtin",
                    "-fno-tree-loop-distribute-patterns",
                    "-fno-stack-protector",
                    "-fno-asynchronous-unwind-tables",
                    "-fno-unwind-tables",
                    "-Os",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wl,--build-id=none",
                    "-Wl,-e,_start",
                    "-Wl,-z,noexecstack",
                    str(SOURCE),
                    "-o",
                    str(binary),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            file_info = subprocess.run(["file", str(binary)], text=True, capture_output=True, check=False)
            readelf = subprocess.run(
                ["aarch64-linux-gnu-readelf", "-h", "-l", str(binary)],
                text=True,
                capture_output=True,
                check=False,
            )
            undefined = subprocess.run(
                ["aarch64-linux-gnu-nm", "-u", str(binary)],
                text=True,
                capture_output=True,
                check=False,
            )
            size = binary.stat().st_size
        self.assertIn("ARM aarch64", file_info.stdout)
        self.assertIn("statically linked", file_info.stdout)
        self.assertNotIn("INTERP", readelf.stdout)
        self.assertEqual(undefined.stdout.strip(), "")
        self.assertLess(size, 65536)

    def test_builder_is_host_only_and_pins_crash_contract(self):
        text = BUILDER.read_text(encoding="ascii")
        for required in [
            '"intentional_kernel_crash": "sysrq-trigger-c"',
            '"failure_fallback": "global PID1 exit_group panic"',
            '"live_flash_authorized": False',
            '"kernel_changed": False',
            '"reboot_syscall": False',
            'members != ["boot.img.lz4"]',
        ]:
            self.assertIn(required, text)
        for forbidden in ["adb ", "odin4 --reboot", "heimdall flash"]:
            self.assertNotIn(forbidden, text)

    @unittest.skipUnless(MANIFEST.is_file(), "O3R1 manifest unavailable")
    def test_real_manifest_is_inert_boot_only_artifact(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "s22plus_o3r1_native_retained_sysrq_build_v1")
        self.assertEqual(data["tar_members"], ["boot.img.lz4"])
        self.assertEqual(data["ramdisk"]["added_entries"], [])
        safety = data["safety"]
        self.assertTrue(safety["boot_only"])
        self.assertFalse(safety["live_flash_authorized"])
        self.assertEqual(safety["procfs_write_allowlist"], ["/proc/sysrq-trigger=c"])
        for key in [
            "kernel_changed",
            "kernel_sysrq_sysctl_write",
            "pmsg_write",
            "module_insertion",
            "sysfs_write",
            "configfs_write",
            "usb_setup",
            "reboot_syscall",
            "block_device_write",
            "persistent_partition_mount",
        ]:
            self.assertFalse(safety[key], key)


if __name__ == "__main__":
    unittest.main()
