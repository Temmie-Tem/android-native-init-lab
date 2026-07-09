import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m3_observable_live_gate.py")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m3_observable_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM3RootFallbackTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_root_shell_falls_back_to_debug_ramdisk_su_and_suppresses_core(self):
        calls = []

        def fake_run(argv, *, timeout=None):
            calls.append([str(part) for part in argv])
            command = str(argv[-1])
            self.assertIn("/proc/sys/kernel/core_pattern", command)
            if command.startswith("su -c "):
                return subprocess.CompletedProcess(argv, 127, "", "/system/bin/sh: su: inaccessible or not found\n")
            if command.startswith("/debug_ramdisk/su -c "):
                return subprocess.CompletedProcess(argv, 0, "uid=0(root)\n", "")
            raise AssertionError(f"unexpected command: {command}")

        original_run = self.module.run
        self.module.run = fake_run
        try:
            result = self.module.adb_root_shell("id", serial="SERIAL")
        finally:
            self.module.run = original_run

        self.assertEqual(result.returncode, 0)
        self.assertIn("uid=0(root)", result.stdout)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][:4], ["adb", "-s", "SERIAL", "shell"])
        self.assertTrue(calls[0][-1].startswith("su -c "))
        self.assertTrue(calls[1][-1].startswith("/debug_ramdisk/su -c "))

    def test_root_id_probe_reports_debug_ramdisk_success(self):
        def fake_run(argv, *, timeout=None):
            command = str(argv[-1])
            if command.startswith("su -c "):
                return subprocess.CompletedProcess(argv, 127, "", "missing\n")
            if command.startswith("/debug_ramdisk/su -c "):
                return subprocess.CompletedProcess(argv, 0, "uid=0(root) gid=0(root)\n", "")
            raise AssertionError(f"unexpected command: {command}")

        original_run = self.module.run
        self.module.run = fake_run
        try:
            text = self.module.root_id_probe_text("SERIAL")
        finally:
            self.module.run = original_run

        self.assertIn("su_root_rc=127", text)
        self.assertIn("debug_ramdisk_su_root_rc=0", text)
        self.assertIn("root_probe=debug_ramdisk_su", text)
        self.assertIn("su_id=uid=0(root) gid=0(root)", text)


if __name__ == "__main__":
    unittest.main()
