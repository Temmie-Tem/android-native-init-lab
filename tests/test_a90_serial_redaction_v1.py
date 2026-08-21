"""Host-only privacy corpus for the A90 owner serial boundary."""

from __future__ import annotations

import contextlib
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
from a90_serial_redaction_v1 import SerialRedactor, marker_for_hash  # noqa: E402
import a90_boot_only_f1_adapter_v1 as adapter  # noqa: E402
from _loader import load_revalidation  # noqa: E402


NATIVE = load_revalidation("native_init_flash")


class SerialRedactionTest(unittest.TestCase):
    RAW = "A90-BOUND-PRIVACY-7f4e9b2c"

    @classmethod
    def setUpClass(cls) -> None:
        cls.digest = hashlib.sha256(cls.RAW.encode()).hexdigest()
        cls.marker = marker_for_hash(cls.digest)

    def test_registered_and_hash_only_text_never_returns_raw(self):
        redactor = SerialRedactor(hashes=(self.digest,))
        self.assertNotIn(self.RAW, redactor.text(f"serial={self.RAW}"))
        self.assertIn(self.marker, redactor.text(f"serial={self.RAW}"))
        redactor.register_secret(self.RAW)
        self.assertNotIn(self.RAW, redactor.text(f"argv -s {self.RAW}"))

    def test_adb_inventory_redacts_every_endpoint_first_column(self):
        foreign = "FOREIGN-PRIVACY-5a8b"
        raw = (
            "List of devices attached\n"
            f"{self.RAW}\trecovery usb:1-2 product:a90\n"
            f"{foreign}\tdevice usb:1-3 product:other\n"
        )
        redactor = SerialRedactor(hashes=(self.digest,))
        redactor.register_adb_inventory_tokens(raw.encode())
        safe = redactor.bytes(raw.encode()).decode()
        self.assertNotIn(self.RAW, safe)
        self.assertNotIn(foreign, safe)
        self.assertIn(self.marker, safe)
        self.assertIn(
            marker_for_hash(hashlib.sha256(foreign.encode()).hexdigest()), safe
        )

    def test_owner_host_runner_persists_only_redacted_recovery_push_failure_and_timeout(self):
        with tempfile.TemporaryDirectory() as temporary:
            redactor = SerialRedactor(hashes=(self.digest,))
            runner = adapter.HostRunner(Path(temporary) / "logs", redactor=redactor)
            inventory_code = (
                "import sys; "
                "sys.stdout.write('List of devices attached\\n"
                + self.RAW
                + "\\trecovery usb:1-2 product:a90 model:"
                + self.RAW
                + " transport_id:"
                + self.RAW
                + "\\nFOREIGN-PRIVACY-5a8b\\tunauthorized usb:1-3 product:other\\n'); "
                "sys.stderr.write('inventory echo "
                + self.RAW
                + "\\n')"
            )
            result = runner.run(
                "adb-inventory", (sys.executable, "-c", inventory_code), 5
            )
            self.assertIn(self.RAW.encode(), result.stdout)
            persisted = b"".join(path.read_bytes() for path in runner.log_directory.iterdir())
            self.assertNotIn(self.RAW.encode(), persisted)
            self.assertIn(b"A90-ADB-INVENTORY-STDOUT-SHA256:", persisted)
            self.assertIn(b"A90-ADB-INVENTORY-STDERR-SHA256:", persisted)

            malformed_code = (
                "import sys; sys.stdout.write('unknown line "
                + self.RAW
                + "\\n')"
            )
            runner.run("adb-inventory", (sys.executable, "-c", malformed_code), 5)
            persisted = b"".join(path.read_bytes() for path in runner.log_directory.iterdir())
            self.assertNotIn(self.RAW.encode(), persisted)
            self.assertIn(b"A90-ADB-INVENTORY-STDOUT-SHA256:", persisted)

            nonzero_code = (
                "import sys; sys.stdout.write('List of devices attached\\n"
                + self.RAW
                + "\\toffline usb:1-2 product:a90\\n'); "
                "sys.stderr.write('adb error "
                + self.RAW
                + "\\n'); sys.exit(3)"
            )
            runner.run("adb-inventory", (sys.executable, "-c", nonzero_code), 5)
            persisted = b"".join(path.read_bytes() for path in runner.log_directory.iterdir())
            self.assertNotIn(self.RAW.encode(), persisted)
            self.assertIn(b"A90-ADB-INVENTORY-STDERR-SHA256:", persisted)

            inventory_timeout_code = (
                "import sys,time; sys.stdout.write('partial "
                + self.RAW
                + "\\n'); sys.stdout.flush(); time.sleep(2)"
            )
            runner.run(
                "adb-inventory",
                (sys.executable, "-c", inventory_timeout_code),
                1,
            )
            persisted = b"".join(path.read_bytes() for path in runner.log_directory.iterdir())
            self.assertNotIn(self.RAW.encode(), persisted)

            failure_code = (
                "import sys; sys.stderr.write('push failed "
                + self.RAW
                + "\\n'); sys.exit(7)"
            )
            failed = runner.run(
                "flash-rollback", (sys.executable, "-c", failure_code), 5
            )
            self.assertEqual(failed.returncode, 7)
            persisted = b"".join(path.read_bytes() for path in runner.log_directory.iterdir())
            self.assertNotIn(self.RAW.encode(), persisted)

            timeout_code = (
                "import sys,time; sys.stderr.write('timeout "
                + self.RAW
                + "\\n'); sys.stderr.flush(); time.sleep(2)"
            )
            timed = runner.run(
                "flash-rollback", (sys.executable, "-c", timeout_code), 1
            )
            self.assertEqual(timed.returncode, 124)
            persisted = b"".join(path.read_bytes() for path in runner.log_directory.iterdir())
            self.assertNotIn(self.RAW.encode(), persisted)

    def test_owner_native_log_argv_recovery_present_and_new_arrival_are_redacted(self):
        previous_state = NATIVE.OWNER_EFFECT_STATE
        previous_redactor = NATIVE.OWNER_SERIAL_REDACTOR
        NATIVE.OWNER_EFFECT_STATE = NATIVE.OwnerEffectState()
        NATIVE.OWNER_SERIAL_REDACTOR = SerialRedactor(hashes=(self.digest,))
        try:
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                NATIVE.log(f"owner serial={self.RAW}")
                with mock.patch.object(
                    NATIVE.subprocess,
                    "run",
                    return_value=NATIVE.subprocess.CompletedProcess([], 0, b"", b""),
                ):
                    NATIVE.run_command(
                        [NATIVE.OWNER_ADB, "-s", self.RAW, "shell", "true"],
                        check=False,
                    )
                with mock.patch.object(
                    NATIVE,
                    "adb_devices",
                    return_value=[(self.RAW, "recovery")],
                ), mock.patch.object(NATIVE.time, "sleep"):
                    NATIVE.bind_present_recovery_or_native_baseline(
                        NATIVE.OWNER_ADB,
                        expected_serial_sha256=self.digest,
                    )
                with mock.patch.object(
                    NATIVE,
                    "adb_devices",
                    return_value=[("FOREIGN", "device"), (self.RAW, "recovery")],
                ), mock.patch.object(NATIVE.time, "sleep"):
                    NATIVE.wait_for_new_recovery_adb(
                        NATIVE.OWNER_ADB,
                        [("FOREIGN", "device")],
                        1,
                        expected_serial_sha256=self.digest,
                    )
            rendered = output.getvalue()
            self.assertNotIn(self.RAW, rendered)
            self.assertIn(self.marker, rendered)
        finally:
            NATIVE.OWNER_EFFECT_STATE = previous_state
            NATIVE.OWNER_SERIAL_REDACTOR = previous_redactor


if __name__ == "__main__":
    unittest.main()
