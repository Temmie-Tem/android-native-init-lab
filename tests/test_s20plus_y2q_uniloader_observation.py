import hashlib
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"))
import uniloader_android_observation as observer


BOOT_ID = b"12345678-1234-1234-1234-123456789abc"
BOOT_SHA256 = hashlib.sha256(BOOT_ID).hexdigest()
MARKER = "7" * 64
MARKER_SHA256 = observer.marker_digest(MARKER)
HEALTH = {
    "serial_sha256": "1" * 64, "topology_sha256": "2" * 64, "boot_id_sha256": BOOT_SHA256,
}
PREFLIGHT = {**HEALTH, "boot_id_sha256": "3" * 64}


def fixture_read(root, property_file):
    boot_id = root / "boot_id"
    boot_id.write_bytes(BOOT_ID + b"\n")
    script = (observer.READ_SCRIPT.replace(observer.MARKER_PATH, str(property_file))
              .replace("/system/bin/cat /proc/sys/kernel/random/boot_id", f"/bin/cat {boot_id}")
              .replace("/system/bin/head", "/usr/bin/head"))
    done = subprocess.run(["/bin/sh", "-c", script], capture_output=True, timeout=3)
    return done.returncode, done.stdout, done.stderr


def classify(result):
    return observer.classify_marker(*result, expected_marker_sha256=MARKER_SHA256,
                                    expected_boot_sha256=BOOT_SHA256)


class LoaderMarkerObservationTests(unittest.TestCase):
    def test_fixed_shell_v2_command(self):
        argv = observer.marker_argv("S20TEST")
        self.assertEqual(argv[:7], [observer.ADB, "-s", "S20TEST", "shell", "-T", "su", "-c"])
        self.assertEqual(shlex.split(argv[7]), [observer.READ_SCRIPT])

    def test_real_shell_preserves_nul_and_limits_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "property"
            path.write_bytes(MARKER.encode() + b"\0")
            result = fixture_read(root, path)
            self.assertEqual(classify(result), "MATCH")
            self.assertEqual(result[1].split(b"\n", 1)[1], MARKER.encode() + b"\0")
            path.write_bytes(MARKER.encode() + b"\0extra")
            result = fixture_read(root, path)
            self.assertEqual(len(result[1]), observer.STDOUT_MAXIMUM)
            self.assertEqual(classify(result), "UNAVAILABLE")

    def test_absent_is_distinct_from_missing_directory_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "property"
            self.assertEqual(classify(fixture_read(root, path)), "ABSENT")
            self.assertEqual(classify(fixture_read(root, root / "missing" / "property")),
                             "UNAVAILABLE")
            path.symlink_to(root / "absent")
            self.assertEqual(classify(fixture_read(root, path)), "UNAVAILABLE")

    def test_wrong_marker_and_early_exit_remain_unproved(self):
        header = b"boot_id=" + BOOT_ID + b"\n"
        self.assertEqual(classify((0, header + b"1" * 64 + b"\0", b"")), "DIFFERENT")
        self.assertEqual(classify((0, header + MARKER.encode(), b"")), "UNAVAILABLE")
        self.assertEqual(classify((0, header + MARKER.encode() + b"\0", b"warning")),
                         "UNAVAILABLE")
        self.assertEqual(classify((44, b"", b"")), "UNAVAILABLE")

    def test_capture_must_name_the_health_brackets_boot(self):
        result = (0, b"boot_id=" + BOOT_ID + b"\n" + MARKER.encode() + b"\0", b"")
        options = {"expected_marker_sha256": MARKER_SHA256, "preflight": PREFLIGHT,
                   "prior_boots": ()}
        self.assertEqual(observer.observe_marker(HEALTH, HEALTH, result, **options), "MATCH")
        changed = {**HEALTH, "boot_id_sha256": "4" * 64}
        self.assertEqual(observer.observe_marker(HEALTH, changed, result, **options),
                         "HEALTH_BINDING_CHANGED")
        self.assertEqual(observer.observe_marker(changed, changed, result, **options),
                         "BOOT_CHANGED")

    def test_original_return_must_be_fresh_and_from_prepared_target(self):
        result = (44, b"boot_id=" + BOOT_ID + b"\n", b"")
        options = {"expected_marker_sha256": MARKER_SHA256, "preflight": PREFLIGHT}
        self.assertEqual(observer.observe_marker(HEALTH, HEALTH, result, prior_boots=(),
                                                 **options), "ABSENT")
        self.assertEqual(observer.observe_marker(HEALTH, HEALTH, result,
                                                 prior_boots=(BOOT_SHA256,), **options),
                         "HEALTH_BINDING_CHANGED")
        foreign = {**HEALTH, "topology_sha256": "f" * 64}
        self.assertEqual(observer.observe_marker(foreign, foreign, result, prior_boots=(),
                                                 **options), "HEALTH_BINDING_CHANGED")


if __name__ == "__main__":
    unittest.main()
