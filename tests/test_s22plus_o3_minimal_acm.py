import importlib.util
import os
import pty
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
O0_SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_o0_stock_usb_control.py"
O3_INIT = ROOT / "workspace/public/src/native-init/s22plus_init_o3_minimal_acm.c"
O3_DAEMON = ROOT / "workspace/public/src/android/s22plus_o3_tty_control.c"
O3_BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_s22plus_o3_minimal_acm.py"
O2_HEADER_DIR = ROOT / "workspace/public/src/native-init"
O3_PLAN_DIR = ROOT / "workspace/private/outputs/s22plus_native_init/o3_minimal_acm_plan_v0_2"


def load_o0_module():
    spec = importlib.util.spec_from_file_location("s22plus_o0_for_o3_test", O0_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusO3MinimalAcmTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o0 = load_o0_module()

    @unittest.skipUnless(shutil.which("cc"), "host C compiler unavailable")
    def test_control_daemon_status_and_128_frame_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            daemon = temp / "s22plus_o3_tty_control"
            status = temp / "status"
            status.write_text(
                "marker=S22_NATIVE_INIT_O3_MINIMAL_ACM\n"
                "result=ready\n"
                "plan_count=59\n"
                "gate_mask=0xff\n"
                "gadget_function=acm.usb0\n"
                "udc=a600000.dwc3\n",
                encoding="ascii",
            )
            compiled = subprocess.run(
                [
                    "cc",
                    "-std=gnu11",
                    "-Os",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    str(O3_DAEMON),
                    "-o",
                    str(daemon),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)

            master, slave = pty.openpty()
            process = subprocess.Popen(
                [
                    str(daemon),
                    "--device",
                    os.ttyname(slave),
                    "--status-file",
                    str(status),
                    "--max-requests",
                    "128",
                    "--idle-timeout-ms",
                    "10000",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                time.sleep(0.05)
                self._exchange(master, 0, b"O3 STATUS", contains=b"plan_count=59")
                for index in range(128):
                    seq = index + 1
                    payload = self.o0.deterministic_payload(seq, 256)
                    self._exchange(master, seq, payload, equals=payload)
                self._exchange(master, 129, b"O3 STATUS", contains=b"protocol_result=pass")
                final_status = status.read_text(encoding="ascii")
                self.assertIn("protocol_handled=128\n", final_status)
                self.assertIn("protocol_invalid=0\n", final_status)
                self.assertIn("protocol_crc_errors=0\n", final_status)
                self.assertIn("protocol_seq_errors=0\n", final_status)
            finally:
                os.close(master)
                os.close(slave)
                process.send_signal(signal.SIGKILL)
                process.wait(timeout=5)

    def _exchange(self, fd, seq, payload, *, equals=None, contains=None):
        request = self.o0.encode_frame(self.o0.REQUEST, seq, payload)
        self.o0.write_all(fd, request, 2.0)
        response = self.o0.read_frame(fd, 2.0)
        _, response_seq, response_payload = self.o0.decode_frame(response, self.o0.RESPONSE)
        self.assertEqual(response_seq, seq)
        if equals is not None:
            self.assertEqual(response_payload, equals)
        if contains is not None:
            self.assertIn(contains, response_payload)

    def test_direct_pid1_source_contract(self):
        init_text = O3_INIT.read_text(encoding="ascii")
        daemon_text = O3_DAEMON.read_text(encoding="ascii")
        for required in [
            "S22PLUS_O2_MODULE_PLAN_COUNT",
            "s22plus_o2_execute_module_plan",
            "s22plus_o2_scan_proc_modules",
            "S22PLUS_O2_BIND_GATE_COUNT",
            '"/config/usb_gadget/g1/functions/acm.usb0"',
            '"/sys/devices/platform/soc/a600000.ssusb/mode"',
            '"peripheral"',
            '"a600000.dwc3"',
            '"/dev/ttyGS0"',
            "execve(O3_DAEMON_PATH",
        ]:
            self.assertIn(required, init_text)
        for forbidden in [
            "ss_acm",
            "functionfs",
            "ffs.adb",
            "mtp.",
            "max77705",
            "sysrq",
            "SYS_reboot",
            '"/sys/module/eud/parameters/enable"',
            '"/system/bin/init"',
        ]:
            self.assertNotIn(forbidden.lower(), init_text.lower())
        self.assertIn('#define O3_STATUS_QUERY "O3 STATUS"', daemon_text)
        self.assertIn('"protocol_result=%s\\nprotocol_handled=%u\\n', daemon_text)
        self.assertNotIn("system(", init_text)
        self.assertNotIn("system(", daemon_text)

    def test_builder_is_host_only_and_fail_closed(self):
        text = O3_BUILDER.read_text(encoding="ascii")
        for required in [
            "verify_fyg8_pins",
            "verify_o3_minimal_acm_plan_identity",
            "all_plan_modules_present",
            '"live_flash_authorized": False',
            'members != ["boot.img.lz4"]',
            "no-change repack differs",
            "patched boot kernel changed",
        ]:
            self.assertIn(required, text)
        for forbidden in ["adb reboot", "odin4 -a", "fastboot flash", "dd of=/dev/block"]:
            self.assertNotIn(forbidden, text)

    @unittest.skipUnless(shutil.which("aarch64-linux-gnu-gcc"), "arm64 compiler unavailable")
    @unittest.skipUnless(O3_PLAN_DIR.is_dir(), "pinned O3 plan is unavailable")
    def test_static_aarch64_binaries_have_no_interpreter(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            init_binary = temp / "init"
            daemon_binary = temp / "control"
            common = [
                "aarch64-linux-gnu-gcc",
                "-static",
                "-Os",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-fno-stack-protector",
                "-Wl,--build-id=none",
                "-Wl,-z,noexecstack",
            ]
            commands = [
                common
                + [
                    "-I",
                    str(O2_HEADER_DIR),
                    "-I",
                    str(O3_PLAN_DIR),
                    str(O3_INIT),
                    "-o",
                    str(init_binary),
                ],
                common + [str(O3_DAEMON), "-o", str(daemon_binary)],
            ]
            for command in commands:
                built = subprocess.run(command, text=True, capture_output=True, check=False)
                self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            for binary in [init_binary, daemon_binary]:
                described = subprocess.run(
                    ["file", str(binary)], text=True, capture_output=True, check=False
                )
                self.assertEqual(described.returncode, 0, described.stderr)
                self.assertIn("ARM aarch64", described.stdout)
                self.assertIn("statically linked", described.stdout)
                program_headers = subprocess.run(
                    ["readelf", "-l", str(binary)], text=True, capture_output=True, check=False
                )
                self.assertEqual(program_headers.returncode, 0, program_headers.stderr)
                self.assertNotIn("INTERP", program_headers.stdout)


if __name__ == "__main__":
    unittest.main()
